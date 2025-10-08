import json

from starlette.websockets import WebSocket

from app.models.proto.robot_command_pb2 import RobotRequest
from app.services.socket.handlers.controller import handle_command


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