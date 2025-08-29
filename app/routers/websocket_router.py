from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict

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
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    try:
        serial = websocket.query_params.get("serial")
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
    ok = await manager.send_to_robot(serial, command.json())
    return JSONResponse({
        "status": "sent" if ok else "failed",
        "to": serial,
        "command": command.dict(),
        "active_clients": manager.active
    })
