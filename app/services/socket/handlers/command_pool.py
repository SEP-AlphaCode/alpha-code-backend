from app.models.stt import ASRData, STTResponse
from app.repositories.activity_repository import get_activity_from_qr
from app.services.nlp.nlp_service import process_text as service_process_text, process_obj_detect
from app.services.object_detect.object_detect_service import detect_closest_objects_from_bytes
from app.services.osmo.osmo_service import recognize_action_cards_from_image, parse_action_card_list
from app.services.qr_code.qr_code_service import detect_qr_code
from app.services.socket import connection_manager
from app.services.stt.stt_service import transcribe_bytes


async def process_speech(asr: ASRData):  # process-speech
    try:
        text: STTResponse = await transcribe_bytes(asr)
        resp = await service_process_text(text.text)
        return resp
    except Exception as e:
        raise e

async def process_text(txt: str): #process-text
    try:
        resp = await service_process_text(txt)
        return resp
    except Exception as e:
        raise e

async def detect_object(img: bytes, lang: str):  # detect-object
    try:
        obj = detect_closest_objects_from_bytes(img)
        if len(obj.closest_objects) == 0:
            return {}
        label = obj.closest_objects[0].label
        rs = await process_obj_detect(label, lang)
        return rs
    except Exception as e:
        raise e


async def parse_osmo(img: bytes):  # parse-osmo
    import tempfile, os
    
    # Create temporary file for the image
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp:
        temp.write(img)
        temp_path = temp.name
    
    try:
        # Use your existing logic functions
        action_card_list = await recognize_action_cards_from_image(temp_path)
        actions = await parse_action_card_list(action_card_list)
        return actions
    except Exception as e:
        raise e
    finally:
        os.remove(temp_path)


async def notify_shutdown(serial: str):  # notify-shutdown
    manager = connection_manager
    try:
        if serial in manager.clients:
            await manager.disconnect_with_reason(serial, "Shut down")
        return {'serial': serial}
    except Exception as e:
        raise e


async def parse_qr(img: bytes):  # parse-qr
    try:
        code = detect_qr_code(img)
        activities = await get_activity_from_qr(code)
        return activities
    except Exception as e:
        raise e
