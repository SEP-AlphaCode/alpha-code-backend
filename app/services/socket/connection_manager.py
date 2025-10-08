"""
WebSocket Connection Manager
Quản lý kết nối WebSocket với các robot, hỗ trợ nhiều loại kết nối
"""
from fastapi import WebSocket
from typing import Dict, List
import logging


class WSMapEntry:
    websocket: WebSocket
    client_id: str

    def __init__(self, websocket: WebSocket, client_id: str):
        self.websocket = websocket
        self.client_id = client_id


class ConnectionManager:
    """Quản lý kết nối WebSocket với robot và signaling"""

    def __init__(self):
        # Store clients as {serial: {client_type: WSMapEntry}}
        self.clients: Dict[str, Dict[str, WSMapEntry]] = {}
        self.logger = logging.getLogger(__name__)

    async def connect(self, websocket: WebSocket, serial: str, client_type: str = "robot") -> bool:
        """
        Kết nối WebSocket với robot hoặc signaling
        Trả về True nếu kết nối thành công, False nếu từ chối
        """
        await websocket.accept()
        if serial not in self.clients:
            self.clients[serial] = {}
        # Nếu cùng client_type đã tồn tại, disconnect cũ
        if client_type in self.clients[serial]:
            try:
                old_ws = self.clients[serial][client_type].websocket
                if old_ws.client_state.name != "DISCONNECTED":
                    await old_ws.close(reason=f"New {client_type} connection established")
            except Exception as e:
                self.logger.warning(f"Error closing old {client_type} websocket for {serial}: {e}")

        self.clients[serial][client_type] = WSMapEntry(websocket, websocket.headers.get("client_id"))
        self.logger.info(f"{client_type} connected for serial {serial}. Total client types: {list(self.clients[serial].keys())}")
        return True

    async def disconnect(self, serial: str, client_type: str = None):
        """
        Ngắt kết nối robot hoặc signaling
        Nếu client_type=None sẽ ngắt tất cả kết nối của serial
        """
        if serial not in self.clients:
            self.logger.warning(f"Attempted to disconnect {serial} but it was not connected")
            return

        types_to_disconnect = [client_type] if client_type else list(self.clients[serial].keys())
        for ctype in types_to_disconnect:
            ws_entry = self.clients[serial].get(ctype)
            if ws_entry:
                try:
                    if ws_entry.websocket.client_state.name != "DISCONNECTED":
                        await ws_entry.websocket.close()
                except Exception as e:
                    self.logger.warning(f"Error disconnecting {ctype} websocket for {serial}: {e}")
                del self.clients[serial][ctype]

        # Nếu không còn loại nào, remove serial
        if not self.clients[serial]:
            del self.clients[serial]

    async def send_to_robot(self, serial: str, message: str, client_type: str = "robot") -> bool:
        """Gửi message tới robot hoặc signaling theo client_type"""
        if serial not in self.clients or client_type not in self.clients[serial]:
            self.logger.warning(f"Cannot send message: {serial} [{client_type}] not connected")
            return False

        ws_entry = self.clients[serial][client_type]
        try:
            if ws_entry.websocket.client_state.name == "CONNECTED":
                await ws_entry.websocket.send_text(message)
                return True
            else:
                self.logger.warning(f"Cannot send message: {serial} [{client_type}] websocket not connected")
        except Exception as e:
            self.logger.error(f"Send error to {serial} [{client_type}]: {e}")
            await self.disconnect(serial, client_type)
        return False

    @property
    def active(self) -> int:
        """Số lượng serial đang có ít nhất 1 kết nối"""
        return len(self.clients)

    def is_connected(self, serial: str, client_type: str = None) -> bool:
        """Kiểm tra robot có đang kết nối không"""
        if serial not in self.clients:
            return False
        if client_type:
            return client_type in self.clients[serial]
        return True

    def get_connected_serials(self) -> List[str]:
        """Lấy danh sách các serial đang kết nối"""
        return list(self.clients.keys())

    def get_client_types(self, serial: str) -> List[str]:
        """Lấy danh sách các loại kết nối cho serial"""
        if serial in self.clients:
            return list(self.clients[serial].keys())
        return []


# Tạo instance global
connection_manager = ConnectionManager()
