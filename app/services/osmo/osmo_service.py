from app.models.osmo import OsmoCardSequence, AlphaMiniAction, AlphaMiniActionList, ActionCardList, ActionCard, OsmoCard
from typing import List
from fastapi.responses import JSONResponse
from app.repositories.osmo_card_repository import get_osmo_card_by_color
import google.generativeai as genai
import os
import json
from typing import Optional

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))


async def recognize_action_cards_from_image(
    image_path: str,
    model_name: str = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
) -> ActionCardList:
    model = genai.GenerativeModel(model_name)

    img_file = {
        "mime_type": "image/jpeg",
        "data": open(image_path, "rb").read()
    }
    print('recognizing')
    prompt = """
    Detect Osmo action cards from this photo.
    Return JSON array only. Each item has:
    - color: "blue","red","orange","yellow","gray"
    - direction: "forward","backward","left","right" or null
    - value: integer (>=1)
    """

    from starlette.concurrency import run_in_threadpool
    response = await run_in_threadpool(model.generate_content, [prompt, img_file])

    raw_text = response.text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        raw_text = raw_text.replace("json", "").strip()

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        raise ValueError(f"Gemini output not valid JSON: {raw_text}")

    action_cards = []
    for c in parsed:
        action_cards.append(ActionCard(
            action=OsmoCard(color=c.get("color")),
            direction=OsmoCard(color="gray", direction=c.get("direction")) if c.get("direction") else None,
            step=OsmoCard(color="yellow", value=c.get("value", 1))
        ))
    print('Done')
    return ActionCardList(action_cards=action_cards)

def parse_osmo_cards(card_sequence: OsmoCardSequence) -> AlphaMiniActionList:
    actions: List[AlphaMiniAction] = []
    i = 0
    while i < len(card_sequence.cards):
        card = card_sequence.cards[i]
        ccolor = getattr(card, "color", None)
        cvalue = getattr(card, "value", None)

        if ccolor in ("blue", "red", "orange"):
            # Default values
            direction = "forward"
            step = 1

            # Check next card for direction (gray)
            if i + 1 < len(card_sequence.cards):
                next_card = card_sequence.cards[i + 1]
                ncolor = getattr(next_card, "color", None)
                ndirection = getattr(next_card, "direction", None)
                if ncolor == "gray" and ndirection:
                    direction = ndirection
                    i += 1  # consume direction card

            # Check next card for step (yellow)
            if i + 1 < len(card_sequence.cards):
                next_card = card_sequence.cards[i + 1]
                ncolor = getattr(next_card, "color", None)
                nvalue = getattr(next_card, "value", None)
                if ncolor == "yellow" and nvalue is not None:
                    step = int(nvalue)
                    i += 1  # consume step card

            if ccolor == "blue":
                action_name = f"move_{direction}"
            elif ccolor == "red":
                action_name = f"jump_{direction}"
            elif ccolor == "orange":
                action_name = f"raise_hand_{direction}"
            else:
                action_name = "unknown"

            actions.append(AlphaMiniAction(action=action_name, value=step))
        i += 1
    return AlphaMiniActionList(actions=actions)


def export_actions_to_json(actions: AlphaMiniActionList, file_path: str):
    import json
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump([action.dict() for action in actions.actions], f, ensure_ascii=False, indent=2)


def export_actions_to_json_response(actions: AlphaMiniActionList):
    return JSONResponse(content=[action.dict() for action in actions.actions])


# ------------------ New Parser for ActionCardList ------------------

async def parse_action_card_list(action_card_list):
    """Chuyển ActionCardList thành list action dictionary, hỗ trợ loop."""
    result = []
    cards = action_card_list.action_cards
    i = 0
    while i < len(cards):
        card = cards[i]

        # ---- LOOP ----
        if card.action.color == "gray" and card.direction is None:
            times = card.step.value if card.step else 1
            loop_body = []

            # Lấy toàn bộ các thẻ sau loop
            for j in range(i + 1, len(cards)):
                loop_body.append(await card_to_action(cards[j]))

            result.append({
                "action": "loop",
                "times": times,
                "actions": loop_body
            })
            break  # dừng vì đã xử lý xong

        # ---- ACTION THƯỜNG ----
        result.append(await card_to_action(card))
        i += 1

    return result

async def card_to_action(card: ActionCard) -> dict:
    """Chuyển 1 ActionCard sang dict hành động, lookup DB thay vì hardcode."""
    db_card = await get_osmo_card_by_color(card.action.color)

    if not db_card:
        action_name = "unknown"
    else:
        # Ưu tiên action.name nếu có, rồi đến dance.name, expression.name
        if db_card.action:
            action_name = db_card.action.name
        elif db_card.dance:
            action_name = db_card.dance.name
        elif db_card.expression:
            action_name = db_card.expression.name
        else:
            action_name = db_card.name  # fallback

    # # Thêm hướng nếu có
    # if card.direction and card.direction.direction:
    #     action_name += "_" + card.direction.direction

    return {
        "action": action_name,
        "value": card.step.value if card.step else 1
    }


# ------------------ Recognizer ------------------

import cv2, numpy as np, math
from app.models.osmo import ActionCard, OsmoCard, ActionCardList
from typing import Optional

def detect_arrow_direction(gray_img):
    import cv2, numpy as np

    g = cv2.resize(gray_img, (120, 120))
    # Nền trắng, mũi tên đậm -> nhị phân ngược
    _, thr = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    cnts, _ = cv2.findContours(thr, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None

    # Lấy khối lớn nhất (mũi tên)
    c = max(cnts, key=cv2.contourArea)
    mask = np.zeros_like(thr)
    cv2.drawContours(mask, [c], -1, 255, -1)

    M = cv2.moments(mask, binaryImage=True)
    if M["m00"] == 0:
        return None

    h, w = mask.shape
    cx = M["m10"] / M["m00"]
    cy = M["m01"] / M["m00"]

    dx = cx - w / 2.0
    dy = cy - h / 2.0

    # Ưu tiên trục có độ lệch lớn hơn
    if abs(dx) >= abs(dy):
        return "right" if dx > 0 else "left"
    else:
        return "forward" if dy < 0 else "backward"


# async def recognize_action_cards_from_image(
#     image_path: str,
#     tesseract_cmd: Optional[str] = None,
#     iou_merge_threshold: float = 0.25,
#     row_height_bin: int = 70,   # nới một chút cho điện thoại chụp
# ):
#     import cv2, numpy as np
#     from app.models.osmo import ActionCard, OsmoCard, ActionCardList
# 
#     img = cv2.imread(image_path)
#     if img is None:
#         raise FileNotFoundError(image_path)
#     hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
# 
#     # HSV ranges
#     color_ranges = {
#         "blue":   ([90, 60, 60],  [130, 255, 255]),
#         "yellow": ([18, 120,120], [40, 255, 255]),
#         "orange": ([5, 100,100],  [18, 255, 255]),
#         "red1":   ([0, 100,100],  [8,  255, 255]),
#         "red2":   ([160,100,100], [179,255,255]),
#         "gray":   ([0, 0, 50],    [179, 50, 200]),
#         # "purple": ([135, 60, 60], [160, 255, 255]),  # nếu có thẻ break màu tím
#     }
# 
#     # --- detect rough boxes
#     raw_boxes = []
#     for cname, (low, high) in color_ranges.items():
#         mask = cv2.inRange(hsv, np.array(low, np.uint8), np.array(high, np.uint8))
#         kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
#         mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
#         cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
#         for c in cnts:
#             x, y, w, h = cv2.boundingRect(c)
#             if w * h < 300:
#                 continue
#             raw_boxes.append(dict(x=x, y=y, w=w, h=h, color_detect=cname))
# 
#     # --- merge IoU (như cũ)
#     def iou(a, b):
#         x1 = max(a["x"], b["x"]); y1 = max(a["y"], b["y"])
#         x2 = min(a["x"] + a["w"], b["x"] + b["w"])
#         y2 = min(a["y"] + a["h"], b["y"] + b["h"])
#         if x2 <= x1 or y2 <= y1:
#             return 0.0
#         inter = (x2 - x1) * (y2 - y1)
#         area = a["w"] * a["h"] + b["w"] * b["h"] - inter
#         return inter / area
# 
#     boxes = []
#     used = [False] * len(raw_boxes)
#     for i, a in enumerate(raw_boxes):
#         if used[i]:
#             continue
#         ux, uy, ux2, uy2 = a["x"], a["y"], a["x"] + a["w"], a["y"] + a["h"]
#         color_detect = a["color_detect"]
#         used[i] = True
#         for j, b in enumerate(raw_boxes[i + 1:], start=i + 1):
#             if used[j]:
#                 continue
#             if iou(a, b) > iou_merge_threshold:
#                 used[j] = True
#                 ux, uy = min(ux, b["x"]), min(uy, b["y"])
#                 ux2, uy2 = max(ux2, b["x"] + b["w"]), max(uy2, b["y"] + b["h"])
#         boxes.append(dict(x=ux, y=uy, w=ux2 - ux, h=uy2 - uy, color_detect=color_detect))
# 
#     # --- sort & assign row id
#     def row_id(b):
#         return int(round((b["y"] + b["h"] * 0.5) / row_height_bin))
# 
#     boxes = sorted(boxes, key=lambda z: (row_id(z), z["x"]))
#     
#     # Tạo index để "đánh dấu đã dùng"
#     for idx, b in enumerate(boxes):
#         b["idx"] = idx
#         b["row"] = row_id(b)
# 
#     used_dir = set()
#     used_yellow = set()
# 
#     def pick_nearest(boxes, cond, ref_x):
#         """Chọn box thỏa cond có x gần ref_x nhất (và cùng hàng)"""
#         candidates = [b for b in boxes if cond(b)]
#         if not candidates:
#             return None
#         return min(candidates, key=lambda k: abs((k["x"] + k["w"] / 2) - ref_x))
# 
#     action_cards = []
# 
#     # --- 2.1 Ghép các ACTION (blue/red/orange) với direction + yellow cùng hàng, gần nhất
#     for a in boxes:
#         # if a["color_detect"] not in ("blue", "red1", "red2", "orange"):
#         #     continue
#         
#         if a["color_detect"] in ("blue", "red1", "red2", "orange"):
# 
#             action_color = "red" if a["color_detect"] in ("red1", "red2") else a["color_detect"]
#             row = a["row"]
#     
#             # direction (gray) cùng hàng, x > action.x, chưa dùng, gần nhất
#             direction_box = pick_nearest(
#                 boxes,
#                 cond=lambda b: (
#                     b["row"] == row and
#                     b["color_detect"] == "gray" and
#                     b["x"] > a["x"] and
#                     b["idx"] not in used_dir
#                 ),
#                 ref_x=a["x"],
#             )
#     
#             direction_text = None
#             anchor_x = a["x"]
#             if direction_box is not None:
#                 roi = img[
#                     direction_box["y"]:direction_box["y"] + direction_box["h"],
#                     direction_box["x"]:direction_box["x"] + direction_box["w"]
#                 ]
#                 direction_text = detect_arrow_direction(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)) or "forward"
#                 used_dir.add(direction_box["idx"])
#                 anchor_x = direction_box["x"]
#     
#             # yellow (step) cùng hàng, x > anchor_x, chưa dùng, gần nhất
#             yellow_box = pick_nearest(
#                 boxes,
#                 cond=lambda b: (
#                     b["row"] == row and
#                     b["color_detect"] == "yellow" and
#                     b["x"] > anchor_x and
#                     b["idx"] not in used_yellow
#                 ),
#                 ref_x=anchor_x,
#             )
#     
#             step_value = 1
#             if yellow_box is not None:
#                 try:
#                     import pytesseract
#                     if tesseract_cmd:
#                         pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
#                     roi_y = img[
#                         yellow_box["y"]:yellow_box["y"] + yellow_box["h"],
#                         yellow_box["x"]:yellow_box["x"] + yellow_box["w"]
#                     ]
#                     gray_y = cv2.cvtColor(roi_y, cv2.COLOR_BGR2GRAY)
#                     _, thr_y = cv2.threshold(gray_y, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
#                     txt = pytesseract.image_to_string(
#                         thr_y, config="--psm 8 -c tessedit_char_whitelist=0123456789"
#                     ).strip()
#                     if txt.isdigit():
#                         step_value = int(txt)
#                     used_yellow.add(yellow_box["idx"])
#                 except:
#                     pass
#     
#             action_cards.append(ActionCard(
#                 action=OsmoCard(color=action_color),
#                 direction=OsmoCard(color="gray", direction=direction_text) if direction_box is not None else None,
#                 step=OsmoCard(color="yellow", value=step_value)
#             ))
#             
#     # --- 2.2 Nhận thẻ LOOP (xám độc lập, không phải direction của action nào) + yellow cùng hàng
#             
#         if a["color_detect"] in ("gray", "green"):
#             if a["idx"] in used_dir:
#                 continue
#     
#             # tìm yellow cùng hàng, x > g.x, gần nhất
#             yb = pick_nearest(
#                 boxes,
#                 cond=lambda b: (
#                     b["row"] == a["row"] and
#                     b["color_detect"] == "yellow" and
#                     b["x"] > a["x"] and
#                     b["idx"] not in used_yellow
#                 ),
#                 ref_x=a["x"],
#             )
#     
#             if yb is None:
#                 continue
#     
#             step_value = 1
#             try:
#                 import pytesseract
#                 if tesseract_cmd:
#                     pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
#                 roi_y = img[yb["y"]:yb["y"] + yb["h"], yb["x"]:yb["x"] + yb["w"]]
#                 gray_y = cv2.cvtColor(roi_y, cv2.COLOR_BGR2GRAY)
#                 _, thr_y = cv2.threshold(gray_y, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
#                 txt = pytesseract.image_to_string(
#                     thr_y, config="--psm 8 -c tessedit_char_whitelist=0123456789"
#                 ).strip()
#                 if txt.isdigit():
#                     step_value = int(txt)
#                 used_yellow.add(yb["idx"])
#             except:
#                 pass
#     
#             action_cards.append(ActionCard(
#                 action=OsmoCard(color="gray"),   # loop
#                 direction=None,
#                 step=OsmoCard(color="yellow", value=step_value)
#             ))
#             
#     return ActionCardList(action_cards=action_cards)
