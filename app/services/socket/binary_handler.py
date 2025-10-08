import json

from starlette.websockets import WebSocket

from app.models.proto.robot_command_pb2 import RobotRequest
from app.models.stt import ASRData
from app.services.nlp.nlp_service import process_text
from app.services.socket.command_handler import process_speech
from app.services.stt.stt_service import transcribe_bytes


async def handle_binary_message(websocket: WebSocket, data: bytes, serial: str) -> None:
    try:
        request = RobotRequest()
        request.ParseFromString(data)
        asr = ASRData(arr=list(request.asr))
        rs = await process_speech(asr)
        #print(rs)
        await websocket.send_text(json.dumps(rs))
        # print('Done!')
        return
    except UnicodeDecodeError as ue:
        print('Decode error', ue)
    except Exception as e:
        print('General error', e)