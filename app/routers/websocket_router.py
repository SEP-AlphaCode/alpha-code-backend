from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict

from app.services.robot_sdk_control.dance_service import run_dances_for_serial

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
        return JSONResponse(result)
    except Exception as e:
        # return exception details to caller to aid debugging (do not keep this in production)
        return JSONResponse({"error": str(e)})
