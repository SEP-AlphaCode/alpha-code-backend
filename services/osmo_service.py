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
            step = 0
            if i + 1 < len(card_sequence.cards):
                next_card = card_sequence.cards[i + 1]
                ncolor = getattr(next_card, "color", None)
                nvalue = getattr(next_card, "value", None)
                if ncolor == "yellow" and nvalue is not None:
                    step = int(nvalue)
                    i += 1  # consume yellow card

            if ccolor == "blue":
                actions.append(AlphaMiniAction(action="move_forward", value=step))
            elif ccolor == "red":
                actions.append(AlphaMiniAction(action="jump_forward", value=step))
            elif ccolor == "orange":
                actions.append(AlphaMiniAction(action="raise_hand", value=step))
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
        step = ac.step.value if ac.step and ac.step.value is not None else 0

        if color == "blue":
            actions.append(AlphaMiniAction(action="move_forward", value=step))
        elif color == "red":
            actions.append(AlphaMiniAction(action="jump_forward", value=step))
        elif color == "orange":
            actions.append(AlphaMiniAction(action="raise_hand", value=step))
        # 'gray' bị bỏ qua hoàn toàn
    return AlphaMiniActionList(actions=actions)

# ------------------ Recognizer ------------------

import cv2, numpy as np, math
from models.osmo import ActionCard, OsmoCard, ActionCardList
from typing import Optional

def recognize_action_cards_from_image_fixed(image_path: str,
                                            tesseract_cmd: Optional[str] = None,
                                            iou_merge_threshold: float = 0.25,
                                            row_height_bin: int = 50):
    """
    Trả về ActionCardList với action=OsmoCard(color=..., value=None) và
    step=OsmoCard(color='yellow', value=<int or None>)
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(image_path)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # color ranges (OpenCV H:0..179)
    color_ranges = {
        'blue':  ([90, 60, 60],  [130, 255, 255]),
        'yellow':([18, 120,120], [40, 255, 255]),
        'orange':([5, 100,100],  [18, 255, 255]),
        'red1':  ([0, 100,100],  [8,  255, 255]),
        'red2':  ([160,100,100], [179,255, 255]),
    }

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
            raw_boxes.append({"x":x,"y":y,"w":w,"h":h})

    def iou(a,b):
        x1 = max(a['x'], b['x']); y1 = max(a['y'], b['y'])
        x2 = min(a['x']+a['w'], b['x']+b['w']); y2 = min(a['y']+a['h'], b['y']+b['h'])
        if x2<=x1 or y2<=y1: return 0.0
        inter = (x2-x1)*(y2-y1)
        area = a['w']*a['h'] + b['w']*b['h'] - inter
        return inter/area

    # merge overlapping boxes
    boxes = []
    used = [False]*len(raw_boxes)
    for i,a in enumerate(raw_boxes):
        if used[i]: continue
        ux,uy,ux2,uy2 = a['x'], a['y'], a['x']+a['w'], a['y']+a['h']
        used[i]=True
        for j,b in enumerate(raw_boxes[i+1:], start=i+1):
            if used[j]: continue
            if iou(a,b) > iou_merge_threshold:
                used[j]=True
                ux = min(ux, b['x']); uy = min(uy, b['y'])
                ux2 = max(ux2, b['x']+b['w']); uy2 = max(uy2, b['y']+b['h'])
        boxes.append({"x":ux,"y":uy,"w":ux2-ux,"h":uy2-uy})

    # circular mean hue
    def circular_mean_hue(roi_h):
        arr = roi_h.flatten().astype(np.float64)
        ang = arr * (2*np.pi/180.0)
        mean_cos = np.mean(np.cos(ang)); mean_sin = np.mean(np.sin(ang))
        mean_ang = math.atan2(mean_sin, mean_cos)
        if mean_ang < 0: mean_ang += 2*np.pi
        mean_h = mean_ang * (180.0/(2*np.pi))
        if mean_h >= 180: mean_h -= 180
        return mean_h

    def classify_from_hsv(mean_h, mean_s, mean_v):
        if mean_s < 40 or mean_v < 40:
            return "gray"
        h = mean_h
        if h <= 10 or h >= 170: return "red"
        if 10 < h <= 18: return "orange"
        if 18 < h <= 40: return "yellow"
        if 90 <= h <= 130: return "blue"
        # fallback nearest
        centers = {"red":0, "orange":14, "yellow":30, "blue":110}
        nearest = min(centers.items(), key=lambda kv: min(abs(h - kv[1]), 180-abs(h-kv[1])))
        return nearest[0]

    final = []
    for b in boxes:
        x,y,w,h = b['x'], b['y'], b['w'], b['h']
        x0,y0 = max(0,x), max(0,y)
        x1,y1 = min(img.shape[1], x+w), min(img.shape[0], y+h)
        roi_h = hsv[y0:y1, x0:x1, 0]
        roi_s = hsv[y0:y1, x0:x1, 1]
        roi_v = hsv[y0:y1, x0:x1, 2]
        mean_h = float(circular_mean_hue(roi_h))
        mean_s = float(np.mean(roi_s)); mean_v = float(np.mean(roi_v))
        color = classify_from_hsv(mean_h, mean_s, mean_v)
        final.append({"x":x,"y":y,"w":w,"h":h,"cx":x+w/2.0,"cy":y+h/2.0,"color":color})

    # reading order sort: row (by y/bin) then x
    final.sort(key=lambda z: (int(z["y"]//row_height_bin), z["x"]))

    # pairing: each non-yellow -> nearest yellow to the right in same row
    used_steps = set()
    action_cards = []
    if tesseract_cmd:
        try:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        except Exception:
            pass

    for i,a in enumerate(final):
        if a["color"] == "yellow":
            continue
        # find candidate yellow
        candidate = None
        for j,b in enumerate(final):
            if j in used_steps: continue
            if b["color"] != "yellow": continue
            if b["x"] <= a["x"]: continue
            if abs(b["cy"] - a["cy"]) > max(a["h"], b["h"]) * 0.6: continue
            if candidate is None or (b["x"] - a["x"] < candidate["x"] - a["x"]):
                candidate = b.copy()
                candidate["j"] = j
        step_value = None
        if candidate is not None:
            used_steps.add(candidate["j"])
            # OCR (optional)
            try:
                import pytesseract
                x0,y0 = int(candidate["x"]), int(candidate["y"])
                x1,y1 = int(candidate["x"]+candidate["w"]), int(candidate["y"]+candidate["h"])
                roi_img = img[y0:y1, x0:x1]
                gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
                _,thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
                txt = pytesseract.image_to_string(thr, config='--psm 8 -c tessedit_char_whitelist=0123456789').strip()
                if txt.isdigit():
                    step_value = int(txt)
            except Exception:
                step_value = None

        # build ActionCard
        action_cards.append(
            ActionCard(
                action=OsmoCard(color=a["color"], value=None),
                step=OsmoCard(color="yellow", value=step_value)
            )
        )

    return ActionCardList(action_cards=action_cards)

