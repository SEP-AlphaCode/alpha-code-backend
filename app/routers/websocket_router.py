from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Set
import json

from starlette.status import HTTP_200_OK

from app.services.socket.robot_websocket_service import robot_websocket_info_service
from app.services.socket.connection_manager import connection_manager

router = APIRouter()

class Command(BaseModel):
    type: str
    data: dict

# Sử dụng connection manager từ service
manager = connection_manager
@router.get("/ws/disconnect/{serial}")
async def close_connection(serial: str):
    try:
        if serial in manager.clients:
            await manager.clients[serial].close(reason="Disconnected by choice")
            manager.disconnect(serial)
        return "Ok"
    except Exception as e:
        raise HTTPException(500, e)
# Robot connects here with serial number
@router.websocket("/ws/{serial}")
async def websocket_endpoint(websocket: WebSocket, serial: str):
    try:
        if not serial:
            await websocket.close(code=1008)  # Policy Violation
            return

        await manager.connect(websocket, serial)

        while True:
            data = await websocket.receive_text()
            
            # Xử lý message từ robot
            try:
                message_data = json.loads(data)
                # Kiểm tra nếu là response cho system info request
                robot_websocket_info_service.handle_robot_response(message_data)
            except json.JSONDecodeError:
                pass
            except Exception as e:
                pass

    except WebSocketDisconnect:
        manager.disconnect(serial)

    except Exception as e:
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

# @router.post("/ubt/dances/{serial}/{code}")
# async def trigger_robot_dances(serial: str, code: str):
#     """Connect to robot by serial tail, run predefined dances, and return results.
#
#     The router is included under the /websocket prefix in main.py, so the full path is POST /websocket/ubt/dances/{serial}/{code}
#     """
#     try:
#         result = await run_dances_for_serial(serial, code)
#         # If the service returned an error, map it to an appropriate HTTP status
#         err = result.get("error") if isinstance(result, dict) else None
#         if err:
#             # device not found/connect failed -> 404
#             if isinstance(err, str) and err.startswith("device_not_found_or_connect_failed"):
#                 return JSONResponse(result, status_code=404)
#             # other expected errors -> 400
#             return JSONResponse(result, status_code=400)
#
#         # success path
#         return JSONResponse(result, status_code=200)
#
#     except Exception as e:
#         # unexpected server error
#         return JSONResponse({"error": str(e)}, status_code=500)

@router.get("/ws/list-by-client/{client}")
async def list_by_client(client_id: str):
    result: Set[str] = set()
    for s in connection_manager.clients.items():
        if s[1].client_id == client_id:
            result.add(s[0])
    return {
        'serials': result
    }

@router.get("/ws/disconnect-by-client/{client}")
async def disconnect_by_client(client_id: str):
    result: Set[str] = set()
    for s in connection_manager.clients.items():
        if s[1].client_id == client_id:
            result.add(s[0])
    for i in result:
        await connection_manager.disconnect(i)
    return {
        'serials': result
    }

@router.get('/ws/info')
async def get_all_clients():
    return connection_manager.clients