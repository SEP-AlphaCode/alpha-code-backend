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
        if hasattr(result, 'json') and callable(getattr(result, 'json')):
            # It's a BaseModel or similar with .json() method
            json_response = result.json()
        elif hasattr(result, 'dict') and callable(getattr(result, 'dict')):
            # It's a BaseModel or similar with .dict() method
            json_response = json.dumps(result.dict())
        else:
            # It's a regular dict, list, or other JSON-serializable type
            json_response = json.dumps(result, default=str)  # default=str handles non-serializable types
        await websocket.send_text(json_response)
    
    except UnicodeDecodeError as ue:
        print('Decode error', ue)
        await websocket.send_text(json.dumps({"error": f"Decode error: {str(ue)}"}))
    except Exception as e:
        print('Other error', e)
        await websocket.send_text(json.dumps({"error": f"Other error: {str(e)}"}))