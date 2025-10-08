from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Set
import json
import logging

from app.services.socket.robot_websocket_service import robot_websocket_info_service
from app.services.socket.connection_manager import connection_manager

router = APIRouter()
logging.basicConfig(level=logging.INFO)

# Pydantic model cho command
class Command(BaseModel):
    type: str
    data: dict

# --- Send command to a robot ---
@router.post("/command/{serial}")
async def send_command(serial: str, command: Command):
    """
    Gửi command tới robot qua WebSocket ConnectionManager
    """
    ok = await connection_manager.send_to_client(
        serial,
        command.model_dump_json(),
        client_type="robot"  # mặc định gửi tới robot
    )
    return JSONResponse({
        "status": "sent" if ok else "failed",
        "to": serial,
        "command": command.model_dump(),
        "active_clients": connection_manager.active
    })

# --- List serials by client_id ---
@router.get("/ws/list-by-client/{client_id}")
async def list_by_client(client_id: str):
    result: Set[str] = set()
    for serial, info in connection_manager.clients.items():
        if info.client_id == client_id:
            result.add(serial)
    return {"serials": result}

# --- Disconnect all robots by client_id ---
@router.get("/ws/disconnect-by-client/{client_id}")
async def disconnect_by_client(client_id: str):
    result: Set[str] = set()
    for serial, info in connection_manager.clients.items():
        if info.client_id == client_id:
            result.add(serial)
    for serial in result:
        await connection_manager.disconnect(serial)
    return {"serials": result}

# --- Disconnect single robot ---
@router.get("/ws/disconnect/{serial}")
async def close_connection(serial: str):
    try:
        if serial in connection_manager.clients:
            await connection_manager.disconnect(serial)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(500, str(e))

# --- WebSocket signaling robot <-> web ---
@router.websocket("/ws/signaling/{serial}/{client_type}")
async def signaling(ws: WebSocket, serial: str, client_type: str):
    """
    WebSocket signaling giữa robot và web client
    client_type: "robot" hoặc "web"
    """
    success = await connection_manager.connect(ws, serial, client_type)
    if not success:
        await ws.close(code=1008, reason="Connection rejected")
        return

    logging.info(f"New WebSocket connection: serial={serial}, type={client_type}")

    try:
        while True:
            data = await ws.receive_json()
            logging.info(f"Received data from {client_type} {serial}: {data}")

            # Relay dữ liệu đến bên còn lại
            target_type = "web" if client_type == "robot" else "robot"
            if connection_manager.is_connected(serial, target_type):
                await connection_manager.send_to_client(serial, json.dumps(data), target_type)

    except WebSocketDisconnect:
        logging.info(f"WebSocket disconnected: serial={serial}, type={client_type}")
        await connection_manager.disconnect(serial, client_type)
    except Exception as e:
        logging.error(f"Unexpected error for {client_type} {serial}: {e}")
        await connection_manager.disconnect(serial, client_type)
