from app.models.stt import ASRData, STTResponse
from app.services.nlp.nlp_service import process_text
from app.services.object_detect.object_detect_service import detect_closest_objects_from_bytes
from app.services.osmo.osmo_service import recognize_action_cards_from_image, parse_action_card_list
from app.services.stt.stt_service import transcribe_bytes


async def process_speech(asr: ASRData):
    try:
        text: STTResponse = await transcribe_bytes(asr)
        resp = await process_text(text.text)
        return resp
    except Exception as e:
        raise e


async def detect_object(img: bytes):
    try:
        rs = detect_closest_objects_from_bytes(img)
        return rs
    except Exception as e:
        raise e


async def parse_osmo(img: bytes):
    import tempfile, os
    
    # Create temporary file for the image
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp:
        temp.write(img)
        temp_path = temp.name
    
    try:
        # Use your existing logic functions
        action_card_list = await recognize_action_cards_from_image(temp_path)
        actions = await parse_action_card_list(action_card_list)
        return {
            "action_cards": action_card_list.action_cards,
            "actions": actions
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        os.remove(temp_path)
