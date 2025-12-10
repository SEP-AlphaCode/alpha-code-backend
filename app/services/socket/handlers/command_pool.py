from app.models.stt import ASRData
from app.repositories.activity_repository import get_activity_from_qr
from app.repositories.robot_repository import get_robot_by_serial
from app.repositories.video_capture_repository import create_video_capture
from app.services.nlp.nlp_service import process_text as service_process_text, process_obj_detect
from app.services.object_detect.object_detect_service import detect_closest_objects_from_bytes
from app.services.osmo.osmo_service import recognize_action_cards_from_image, parse_action_card_list
from app.services.qr_code.qr_code_service import detect_qr_code
from app.services.socket import connection_manager, robot_websocket_info_service
from app.services.stt.stt_service import transcribe_bytes_driver
from app.services.video.video_capture_service import upload_image_to_s3
import logging

logger = logging.getLogger(__name__)


async def process_speech(asr: ASRData, robot_model_id: str, serial: str):  # process-speech
    try:
        text = await transcribe_bytes_driver(asr)
        print(text)
        resp = await service_process_text(input_text=text, robot_model_id=robot_model_id, serial=serial)
        return resp
    except Exception as e:
        raise e

async def process_text(txt: str,  robot_model_id: str, serial: str): #process-text
    try:
        resp = await service_process_text(input_text=txt, robot_model_id=robot_model_id, serial=serial)
        return resp
    except Exception as e:
        raise e

async def detect_object(img: bytes, lang: str):  # detect-object
    try:
        obj = detect_closest_objects_from_bytes(img)
        if len(obj.closest_objects) == 0:
            if lang == 'en':
                content = "I couldn't see anything"
            else:
                content = "Tôi không thấy gì cả"
            return {
                'type': 'talk',
                'lang': lang,
                'data': {
                    'text': content
                }
            }
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
        if code is None:
            return {
                'type': 'talk',
                'lang': 'vi',
                'data': {
                    'text': "Tôi không thấy QR code. Vui lòng thử lại"
                }
            }
        activities = await get_activity_from_qr(code)
        return activities
    except Exception as e:
        raise e

async def handle_coding_block_status(b: bool):
    s = robot_websocket_info_service
    for request_id, pending in list(s.pending_requests.items()):
        s.pending_requests[request_id]['response'] = b
        s.pending_requests[request_id]['event'].set()


async def parse_video(img: bytes, serial: str, lang: str = 'vi'):  # parse-video
    """
    Parse video command: upload image to S3 and create video_capture record

    Args:
        img: Image bytes
        serial: Robot serial number
        lang: Language for response messages

    Returns:
        Response dict with status and message
    """
    try:
        logger.info(f"Processing parse-video command for serial: {serial}")

        # Step 1: Get robot entity by serial
        logger.info(f"Fetching robot for serial: {serial}")
        robot = await get_robot_by_serial(serial)

        if not robot:
            logger.error(f"No robot found for serial: {serial}")
            error_msg = "Robot not found or inactive" if lang == 'en' else "Không tìm thấy robot hoặc robot không hoạt động"
            return {
                'type': 'talk',
                'lang': lang,
                'data': {
                    'text': error_msg
                }
            }

        # Extract account_id from robot entity
        account_id = robot.account_id
        logger.info(f"Found robot with account_id: {account_id}")

        # Step 2: Upload image to S3
        logger.info("Uploading image to S3...")
        image_url = await upload_image_to_s3(img)

        if not image_url:
            logger.error("Failed to upload image to S3")
            error_msg = "Failed to upload image" if lang == 'en' else "Không thể tải ảnh lên"
            return {
                'type': 'talk',
                'lang': lang,
                'data': {
                    'text': error_msg
                }
            }

        logger.info(f"Image uploaded successfully: {image_url}")

        # Step 3: Create video_capture record
        logger.info("Creating video_capture record in database...")
        description = "Hãy biến bức ảnh này thành video sinh động" if lang == 'vi' else "Transform this image into a vivid video"
        video_capture = await create_video_capture(
            image_url=image_url,
            account_id=account_id,
            description=description
        )

        if not video_capture:
            logger.error("Failed to create video_capture record")
            error_msg = "Failed to save video capture data" if lang == 'en' else "Không thể lưu dữ liệu video"
            return {
                'type': 'talk',
                'lang': lang,
                'data': {
                    'text': error_msg
                }
            }

        logger.info(f"Video capture record created successfully: {video_capture.id}")

        # Success response
        success_msg = "Image received successfully! Video will be generated soon." if lang == 'en' else "Đã nhận ảnh thành công! Video sẽ được tạo sớm."
        return {
            'type': 'talk',
            'lang': lang,
            'data': {
                'text': success_msg,
                'video_capture_id': str(video_capture.id),
                'image_url': image_url
            }
        }

    except Exception as e:
        logger.error(f"Error in parse_video: {e}", exc_info=True)
        error_msg = f"Error: {str(e)}" if lang == 'en' else f"Lỗi: {str(e)}"
        return {
            'type': 'talk',
            'lang': lang,
            'data': {
                'text': error_msg
            }
        }
