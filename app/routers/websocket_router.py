from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Set, Optional
import json
import logging

from app.services.socket.robot_websocket_service import robot_websocket_info_service
from app.services.socket.connection_manager import connection_manager

router = APIRouter()
logging.basicConfig(level=logging.INFO)

# Pydantic model cho command
class Command(BaseModel):
    type: str
    lang: Optional[str]
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
