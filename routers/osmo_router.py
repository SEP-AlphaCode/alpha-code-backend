from fastapi import APIRouter, UploadFile, File

from models.osmo import ActionCardList
from services.osmo_service import (
    # recognize_osmo_cards_from_image,
    parse_action_card_list,
    recognize_action_cards_from_image,
)

router = APIRouter()

@router.post("/parse_action_cards")
async def parse_action_cards(action_card_list: ActionCardList):
    actions = parse_action_card_list(action_card_list)
    return {"actions": [a.dict() for a in actions.actions]}

@router.post("/recognize_action_cards_from_image")
async def recognize_action_cards_from_image_api(
    image: UploadFile = File(...)
):
    import tempfile, shutil, os
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(image.filename)[-1]) as temp:
        shutil.copyfileobj(image.file, temp)
        temp_path = temp.name
    try:
        action_card_list = recognize_action_cards_from_image(temp_path)
        actions = parse_action_card_list(action_card_list)
        return {
            "action_cards": [ac.dict() for ac in action_card_list.action_cards],
            "actions": [a.dict() for a in actions.actions]
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        os.remove(temp_path)
