from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict
import json

from app.services.robot_sdk_control.dance_service import run_dances_for_serial
from app.services.socket.robot_websocket_service import robot_websocket_info_service

router = APIRouter()

class Command(BaseModel):
    type: str
    data: dict

class ConnectionManager:
    def __init__(self):
        # Store clients as {serial: websocket}
        self.clients: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, serial: str):
        await websocket.accept()
        self.clients[serial] = websocket
        print(f"Robot {serial} connected. Total: {len(self.clients)}")

    def disconnect(self, serial: str):
        if serial in self.clients:
            del self.clients[serial]
            print(f"Robot {serial} disconnected. Total: {len(self.clients)}")

    async def send_to_robot(self, serial: str, message: str) -> bool:
        ws = self.clients.get(serial)
        if ws:
            try:
                await ws.send_text(message)
                return True
            except Exception as e:
                print(f"Send error to {serial}: {e}")
                self.disconnect(serial)
        return False

    @property
    def active(self) -> int:
        return len(self.clients)

manager = ConnectionManager()

# Robot connects here with serial number
@router.websocket("/ws/{serial}")
async def websocket_endpoint(websocket: WebSocket, serial: str):
    try:
        print("Incoming WS request:", websocket.url)
        print("Parsed serial:", serial)
        if not serial:
            await websocket.close(code=1008)  # Policy Violation
            return

        await manager.connect(websocket, serial)
        print(f"Robot {serial} connected")

        while True:
            data = await websocket.receive_text()
            print(f"{serial} -> {data}")
            
            # Xử lý message từ robot
            try:
                message_data = json.loads(data)
                # Kiểm tra nếu là response cho system info request
                robot_websocket_info_service.handle_robot_response(message_data)
            except json.JSONDecodeError:
                print(f"Invalid JSON from robot {serial}: {data}")
            except Exception as e:
                print(f"Error processing message from robot {serial}: {e}")

    except WebSocketDisconnect:
        print(f"Robot {serial} disconnected")
        manager.disconnect(serial)

    except Exception as e:
        print(f"WebSocket error for {serial}: {e}")
        manager.disconnect(serial)



# Send a command to a specific robot
@router.post("/command/{serial}")
async def send_command(serial: str, command: Command):
    # Use pydantic v2 model_dump_json / model_dump to avoid deprecation warnings
    ok = await manager.send_to_robot(serial, command.model_dump_json())
    return JSONResponse({
        "status": "sent" if ok else "failed",
        "to": serial,
        "command": command.model_dump(),
        "active_clients": manager.active
    })

@router.post("/ubt/dances/{serial}/{code}")
async def trigger_robot_dances(serial: str, code: str):
    """Connect to robot by serial tail, run predefined dances, and return results.

    The router is included under the /websocket prefix in main.py, so the full path is POST /websocket/ubt/dances/{serial}/{code}
    """
    try:
        result = await run_dances_for_serial(serial, code)
        # If the service returned an error, map it to an appropriate HTTP status
        err = result.get("error") if isinstance(result, dict) else None
        if err:
            # device not found/connect failed -> 404
            if isinstance(err, str) and err.startswith("device_not_found_or_connect_failed"):
                return JSONResponse(result, status_code=404)
            # other expected errors -> 400
            return JSONResponse(result, status_code=400)

        # success path
        return JSONResponse(result, status_code=200)

    except Exception as e:
        # unexpected server error
        return JSONResponse({"error": str(e)}, status_code=500)
