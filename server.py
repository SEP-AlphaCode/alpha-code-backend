from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List

app = FastAPI()

clients: List[WebSocket] = []

class Command(BaseModel):
    type: str
    data: dict

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            print(f"Client said: {data}")
    except WebSocketDisconnect:
        clients.remove(websocket)

@app.post("/command")
async def send_command(command: Command):
    message = command.json()  # chuyển model thành json string

    disconnected_clients = []
    for ws in clients:
        try:
            await ws.send_text(message)
        except Exception as e:
            print(f"Failed to send to client: {e}")
            disconnected_clients.append(ws)
    for ws in disconnected_clients:
        clients.remove(ws)

    return JSONResponse({"status": "sent", "command": command.dict()})
