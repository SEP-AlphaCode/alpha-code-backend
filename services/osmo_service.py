from models.osmo import OsmoCardSequence, AlphaMiniAction, AlphaMiniActionList, ActionCardList, ActionCard, OsmoCard
from typing import List
from fastapi.responses import JSONResponse

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

def parse_action_card_list(action_card_list: ActionCardList) -> AlphaMiniActionList:
    actions: List[AlphaMiniAction] = []
    for ac in action_card_list.action_cards:
        color = ac.action.color
        direction = ac.direction.direction if ac.direction and hasattr(ac.direction, "direction") else "forward"
        # Always default step to 1 if missing
        step = ac.step.value if ac.step and ac.step.value is not None else 1

        # Combine action and direction
        if color == "blue":
            action_name = f"move_{direction}"
        elif color == "red":
            action_name = f"jump_{direction}"
        elif color == "orange":
            action_name = f"raise_hand_{direction}"
        else:
            continue  # skip other colors

        actions.append(AlphaMiniAction(action=action_name, value=step))
    return AlphaMiniActionList(actions=actions)


# ------------------ Recognizer ------------------

import cv2, numpy as np, math
from models.osmo import ActionCard, OsmoCard, ActionCardList
from typing import Optional

def detect_arrow_direction(gray_img):
    gray = cv2.resize(gray_img, (100, 100))
    _, thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    cnts, _ = cv2.findContours(thr, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    c = max(cnts, key=cv2.contourArea)
    (x, y), (MA, ma), angle = cv2.minAreaRect(c)
    if angle < 0:
        angle += 360

    if 315 <= angle or angle < 45:
        return "right"
    elif 45 <= angle < 135:
        return "backward"
    elif 135 <= angle < 225:
        return "left"
    elif 225 <= angle < 315:
        return "forward"
    return None

def recognize_action_cards_from_image_fixed(image_path: str,
                                            tesseract_cmd: Optional[str] = None,
                                            iou_merge_threshold: float = 0.25,
                                            row_height_bin: int = 50):
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(image_path)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # color ranges
    color_ranges = {
        'blue':  ([90, 60, 60],  [130, 255, 255]),
        'yellow':([18, 120,120], [40, 255, 255]),
        'orange':([5, 100,100],  [18, 255, 255]),
        'red1':  ([0, 100,100],  [8,  255, 255]),
        'red2':  ([160,100,100], [179,255, 255]),
        'gray':  ([0, 0, 50], [179, 50, 200]),
    }

    # detect boxes
    raw_boxes = []
    for cname, (low, high) in color_ranges.items():
        lower = np.array(low, dtype=np.uint8)
        upper = np.array(high, dtype=np.uint8)
        mask = cv2.inRange(hsv, lower, upper)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cnts:
            x,y,w,h = cv2.boundingRect(c)
            if w*h < 300:
                continue
            raw_boxes.append({"x":x,"y":y,"w":w,"h":h, "color_detect": cname})

    # merge IoU
    def iou(a,b):
        x1 = max(a['x'], b['x']); y1 = max(a['y'], b['y'])
        x2 = min(a['x']+a['w'], b['x']+b['w']); y2 = min(a['y']+a['h'], b['y']+b['h'])
        if x2<=x1 or y2<=y1: return 0.0
        inter = (x2-x1)*(y2-y1)
        area = a['w']*a['h'] + b['w']*b['h'] - inter
        return inter/area

    boxes = []
    used = [False]*len(raw_boxes)
    for i,a in enumerate(raw_boxes):
        if used[i]: continue
        ux,uy,ux2,uy2 = a['x'], a['y'], a['x']+a['w'], a['y']+a['h']
        color_detect = a["color_detect"]
        used[i]=True
        for j,b in enumerate(raw_boxes[i+1:], start=i+1):
            if used[j]: continue
            if iou(a,b) > iou_merge_threshold:
                used[j]=True
                ux = min(ux, b['x']); uy = min(uy, b['y'])
                ux2 = max(ux2, b['x']+b['w']); uy2 = max(uy2, b['y']+b['h'])
        boxes.append({"x":ux,"y":uy,"w":ux2-ux,"h":uy2-uy,"color_detect":color_detect})

    boxes.sort(key=lambda z: (int(z["y"]//row_height_bin), z["x"]))

    action_cards = []
    for a in boxes:
        if a["color_detect"] not in ("blue", "red1", "red2", "orange"):
            continue
        action_color = "red" if a["color_detect"] in ("red1", "red2") else a["color_detect"]

        # direction box
        direction_box = next((b for b in boxes if b["color_detect"] == "gray"
                              and b["x"] > a["x"]
                              and abs(b["y"] - a["y"]) < a["h"]), None)

        direction_text = None
        if direction_box:
            roi_dir = img[direction_box["y"]:direction_box["y"]+direction_box["h"],
                          direction_box["x"]:direction_box["x"]+direction_box["w"]]
            gray_dir = cv2.cvtColor(roi_dir, cv2.COLOR_BGR2GRAY)
            direction_text = detect_arrow_direction(gray_dir) or "forward"

        # step box
        step_value = None
        if direction_box:
            yellow_box = next((b for b in boxes if b["color_detect"] == "yellow"
                               and b["x"] > direction_box["x"]
                               and abs(b["y"] - direction_box["y"]) < a["h"]), None)
            if yellow_box:
                try:
                    import pytesseract
                    if tesseract_cmd:
                        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
                    roi_img = img[yellow_box["y"]:yellow_box["y"]+yellow_box["h"],
                                  yellow_box["x"]:yellow_box["x"]+yellow_box["w"]]
                    gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
                    _,thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
                    txt = pytesseract.image_to_string(thr, config='--psm 8 -c tessedit_char_whitelist=0123456789').strip()
                    if txt.isdigit():
                        step_value = int(txt)
                except:
                    pass

        if step_value is None:
            step_value = 1  # mặc định

        action_cards.append(ActionCard(
            action=OsmoCard(color=action_color, value=None),
            direction=OsmoCard(color="gray", direction=direction_text, value=None) if direction_box else None,
            step=OsmoCard(color="yellow", value=step_value)
        ))

    return ActionCardList(action_cards=action_cards)