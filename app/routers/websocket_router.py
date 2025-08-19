from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List

router = APIRouter()

class Command(BaseModel):
    type: str
    data: dict

class ConnectionManager:
    def __init__(self):
        self.clients: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.clients.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.clients:
            self.clients.remove(websocket)

    async def broadcast(self, message: str):
        disconnected: List[WebSocket] = []
        for ws in self.clients:
            try:
                await ws.send_text(message)
            except Exception as e:
                print(f"Broadcast error: {e}")
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws)
        return len(self.clients)

    @property
    def active(self) -> int:
        return len(self.clients)

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            print(f"Client said: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@router.post("/command")
async def send_command(command: Command):
    delivered_after = await manager.broadcast(command.json())
    return JSONResponse({
        "status": "sent",
        "command": command.dict(),
        "active_clients": delivered_after
    })
