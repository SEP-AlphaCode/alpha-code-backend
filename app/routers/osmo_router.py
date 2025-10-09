from fastapi import APIRouter, UploadFile, File
from typing import List
from app.models.osmo import ActionCardList
from app.services.osmo.osmo_service import (
    # recognize_osmo_cards_from_image,
    parse_action_card_list,
    recognize_action_cards_from_image,
)
from app.repositories.osmo_card_repository import get_all_osmo_cards
from app.models.osmo import OsmoCardRead

router = APIRouter()

@router.get("/osmo-cards", response_model=List[OsmoCardRead])
async def list_osmo_cards():
    return await get_all_osmo_cards()

@router.post("/parse_action_cards")
async def parse_action_cards(action_card_list: ActionCardList):
    actions = await parse_action_card_list(action_card_list)
    return actions.actions


@router.post("/recognize_action_cards_from_image")
async def recognize_action_cards_from_image_api(image: UploadFile = File(...)):
    import tempfile, shutil, os
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(image.filename)[-1]) as temp:
        shutil.copyfileobj(image.file, temp)
        temp_path = temp.name
    try:
        action_card_list = await recognize_action_cards_from_image(temp_path)
        actions = await parse_action_card_list(action_card_list)
        print(actions)
        return {
            # "action_cards": action_card_list.action_cards,
            # "actions":
            actions

        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        os.remove(temp_path)
