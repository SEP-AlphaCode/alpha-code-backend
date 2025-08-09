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

def recognize_action_cards_from_image(image_path: str) -> ActionCardList:
    import cv2
    import numpy as np
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Image not found or cannot be read: {image_path}")

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Range màu
    color_ranges = {
        'blue': {'lower': [90, 80, 60], 'upper': [130, 255, 255]},
        'yellow': {'lower': [20, 150, 150], 'upper': [40, 255, 255]},
        'orange': {'lower': [5, 100, 100], 'upper': [25, 255, 255]},
        'red1': {'lower': [0, 100, 100], 'upper': [10, 255, 255]},
        'red2': {'lower': [160, 100, 100], 'upper': [179, 255, 255]},
    }

    detected_cards = []

    # Detect màu action
    for color, rng in color_ranges.items():
        lower = np.array(rng['lower'], dtype=np.uint8)
        upper = np.array(rng['upper'], dtype=np.uint8)

        mask = cv2.inRange(hsv, lower, upper)

        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cnts:
            x, y, w, h = cv2.boundingRect(c)
            if w > 20 and h > 20:
                if color in ['red1', 'red2']:
                    color_name = 'red'
                else:
                    color_name = color

                if color_name != 'gray':
                    detected_cards.append({
                        "color": color_name,
                        "x": x,
                        "y": y,
                        "w": w,
                        "h": h
                    })

    # Sắp xếp từ trái qua phải
    detected_cards.sort(key=lambda c: c['x'])

    action_cards = []
    i = 0
    while i < len(detected_cards) - 1:
        action_card = detected_cards[i]
        step_card = detected_cards[i + 1]

        # Chỉ ghép nếu step là yellow
        if step_card['color'] == 'yellow':
            # OCR đọc số từ step
            roi = img[step_card['y']:step_card['y']+step_card['h'],
                      step_card['x']:step_card['x']+step_card['w']]
            step_text = pytesseract.image_to_string(roi, config='--psm 8 -c tessedit_char_whitelist=0123456789').strip()
            if not step_text.isdigit():
                step_value = 0
            else:
                step_value = int(step_text)

            step_value = int(step_text) if step_text.isdigit() else 0

            action_cards.append(ActionCard(
                action=OsmoCard(color=action_card['color'], value=None),  # action value = None
                step=OsmoCard(color="yellow", value=step_value)
            ))
            i += 2
        else:
            i += 1

    return ActionCardList(action_cards=action_cards)
