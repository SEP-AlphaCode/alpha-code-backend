from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Set
import json

from app.services.socket.robot_websocket_service import robot_websocket_info_service
from app.services.socket.connection_manager import connection_manager

router = APIRouter()

# Pydantic model cho command
class Command(BaseModel):
    type: str
    data: dict

# Dùng connection manager
manager = connection_manager

# --- WebSocket robot connect ---
@router.websocket("/ws/{serial}")
async def websocket_endpoint(websocket: WebSocket, serial: str):
    if not serial:
        await websocket.close(code=1008)
        return

    success = await manager.connect(websocket, serial)
    if not success:
        return

    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
            elif message["type"] == "websocket.receive":
                if "text" in message:
                    try:
                        data = json.loads(message["text"])
                        # Xử lý response từ robot
                        robot_websocket_info_service.handle_robot_response(data)
                    except json.JSONDecodeError:
                        pass
                elif "bytes" in message:
                    await manager.handle_binary(websocket, message["bytes"], serial)
    except WebSocketDisconnect:
        await manager.disconnect(serial)
    except Exception:
        await manager.disconnect(serial)

# --- Send command to a robot ---
@router.post("/command/{serial}")
async def send_command(serial: str, command: Command):
    ok = await manager.send_to_robot(serial, command.model_dump_json())
    return JSONResponse({
        "status": "sent" if ok else "failed",
        "to": serial,
        "command": command.model_dump(),
        "active_clients": manager.active
    })

# --- List serials by client_id ---
@router.get("/ws/list-by-client/{client_id}")
async def list_by_client(client_id: str):
    result: Set[str] = set()
    for serial, info in manager.clients.items():
        if info.client_id == client_id:
            result.add(serial)
    return {"serials": result}

# --- Disconnect all robots by client_id ---
@router.get("/ws/disconnect-by-client/{client_id}")
async def disconnect_by_client(client_id: str):
    result: Set[str] = set()
    for serial, info in manager.clients.items():
        if info.client_id == client_id:
            result.add(serial)
    for serial in result:
        await manager.disconnect(serial)
    return {"serials": result}

# --- Disconnect single robot ---
@router.get("/ws/disconnect/{serial}")
async def close_connection(serial: str):
    try:
        if serial in manager.clients:
            await manager.clients[serial].close(reason="Disconnected by choice")
            await manager.disconnect(serial)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(500, str(e))

# --- WebRTC signaling between robot <-> web ---
robot_connections: Dict[str, WebSocket] = {}
web_connections: Dict[str, WebSocket] = {}

from fastapi import WebSocket, WebSocketDisconnect
import logging

logging.basicConfig(level=logging.INFO)

@router.websocket("/ws/signaling/{serial}/{client_type}")
async def signaling(ws: WebSocket, serial: str, client_type: str):
    """
    client_type: "robot" hoặc "web"
    """
    await ws.accept()
    logging.info(f"New WebSocket connection: serial={serial}, type={client_type}")

    if client_type == "robot":
        robot_connections[serial] = ws
    else:
        web_connections[serial] = ws

    try:
        while True:
            data = await ws.receive_json()
            logging.info(f"Received data from {client_type} {serial}: {data}")

            # Relay data tới đối tượng còn lại
            if client_type == "robot" and serial in web_connections:
                await web_connections[serial].send_json(data)
                logging.info(f"Relayed data to web {serial}")
            elif client_type == "web" and serial in robot_connections:
                await robot_connections[serial].send_json(data)
                logging.info(f"Relayed data to robot {serial}")

    except WebSocketDisconnect:
        logging.info(f"WebSocket disconnected: serial={serial}, type={client_type}")
        if client_type == "robot":
            robot_connections.pop(serial, None)
        else:
            web_connections.pop(serial, None)

