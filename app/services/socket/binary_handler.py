import json

from pydantic.main import BaseModel
from starlette.websockets import WebSocket

from app.models.proto.robot_command_pb2 import RobotRequest
from app.models.stt import ASRData
from app.services.nlp.nlp_service import process_text
from app.services.socket.command_handler import process_speech, handle_command
from app.services.stt.stt_service import transcribe_bytes


async def handle_binary_message(websocket: WebSocket, data: bytes, serial: str) -> None:
    try:
        request = RobotRequest()
        request.ParseFromString(data)
        
        # Use the handle_command function to process the request
        result = await handle_command(request)
        
        # Send the result back as JSON
        if isinstance(result, BaseModel):
            await websocket.send_text(result.json())
        else:
            # For regular dicts or other objects
            await websocket.send_text(json.dumps(result))
    
    except UnicodeDecodeError as ue:
        print('Decode error', ue)
        await websocket.send_text(json.dumps({"error": f"Decode error: {str(ue)}"}))
    except Exception as e:
        print('General error', e)
        await websocket.send_text(json.dumps({"error": f"General error: {str(e)}"}))