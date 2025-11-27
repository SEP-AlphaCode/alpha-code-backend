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
    prompt = """
    You are analyzing an image that contains one or more horizontal rows of Osmo action cards.

    Each row typically includes:
    - One **action card** on the left with a color indicating the type of action.
    - Optionally, one **yellow step card** on the right indicating the number of steps.

    Your task:
    Detect all rows and return a **pure JSON array** (no text or markdown).
    Each item represents one detected row in top-to-bottom order.

    JSON format for each item:
    {
      "color": "blue" | "red" | "orange" | "gray" | "pink" | "purple" | "green",
      "direction": "forward" | "backward" | "left" | "right" | null,
      "value": integer
    }

    Rules:
    1. The "color" field corresponds to the color of the action card (not yellow).
    2. If a yellow card is present in the same row, extract the number on it and use that as "value".
    3. If there is **no yellow card**, default `"value": 1`.
    5. Return **JSON only**, without explanations or code fences.

    Example valid output:
    [
      {"color": "red", "direction": "backward", "value": 3},
      {"color": "blue", "direction": "forward", "value": 2},
      {"color": "green", "direction": "left", "value": 5}
    ]
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
                actions_inside = await card_to_action(cards[j])
                loop_body.extend(actions_inside)

            # result.append({
            #     "type": "loop",
            #     "times": times,
            #     "actions": loop_body
            # })
            for _ in range(times):
                result.extend(loop_body)
            break 

        # ---- ACTION THƯỜNG ----
        actions = await card_to_action(card)
        result.extend(actions)
        i += 1

    return {
        "type": "osmo_card",
        "data": {'actions': result}
    }

async def card_to_action(card: ActionCard) -> List[dict]:
    """Convert 1 ActionCard sang list các dict action (mỗi step = 1 item)."""
    db_card = await get_osmo_card_by_color(card.action.color)
    step_count = card.step.value if card.step else 1

    # Map màu sang RGB
    color_map = {
        "blue": [0, 0, 255],
        "red": [255, 0, 0],
        "orange": [255, 165, 0],
        "yellow": [255, 255, 0],
        "gray": [128, 128, 128],
    }
    rgb_color = color_map.get(card.action.color, [255, 255, 255])  # fallback: white

    # Default values
    action_type = "unknown"
    action_code = "unknown"

    if db_card:
        if db_card.action is not None:
            action_type = "action"
            action_code = db_card.action.code
        elif db_card.dance is not None:
            action_type = "action"
            action_code = db_card.dance.code
        elif db_card.expression is not None:
            action_type = "expression"
            action_code = db_card.expression.code
        elif db_card.skill is not None:
            action_type = "skill_helper"
            action_code = db_card.skill.code
        elif db_card.extended_action is not None:
            action_type = "extended_action"
            action_code = db_card.extended_action.code

    print(f"Card {card.action.color} -> {action_type}:{action_code} x{step_count}")
    # Lặp lại theo số step
    return [
        {
            "type": action_type,
            "code": action_code,
            "color": {
                'a': 0,
                'r': rgb_color[0],
                'g': rgb_color[1],
                'b': rgb_color[2]
            }
        }
        for _ in range(step_count)
    ]

    return result


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


