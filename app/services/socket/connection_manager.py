"""
WebSocket Connection Manager
Quản lý kết nối WebSocket với các robot
"""

from fastapi import WebSocket
from typing import Dict
import logging


class ConnectionManager:
    """Quản lý kết nối WebSocket với robot"""
    
    def __init__(self):
        # Store clients as {serial: websocket}
        self.clients: Dict[str, WebSocket] = {}
        self.logger = logging.getLogger(__name__)

    async def connect(self, websocket: WebSocket, serial: str):
        """Kết nối WebSocket với robot"""
        await websocket.accept()
        self.clients[serial] = websocket
        self.logger.info(f"Robot {serial} connected. Total: {len(self.clients)}")

    def disconnect(self, serial: str):
        """Ngắt kết nối robot"""
        if serial in self.clients:
            del self.clients[serial]
            self.logger.info(f"Robot {serial} disconnected. Total: {len(self.clients)}")

    async def send_to_robot(self, serial: str, message: str) -> bool:
        """Gửi message tới robot"""
        ws = self.clients.get(serial)
        if ws:
            try:
                await ws.send_text(message)
                return True
            except Exception as e:
                self.logger.error(f"Send error to {serial}: {e}")
                self.disconnect(serial)
        return False

    @property
    def active(self) -> int:
        """Số lượng robot đang kết nối"""
        return len(self.clients)
    
    def is_connected(self, serial: str) -> bool:
        """Kiểm tra robot có đang kết nối không"""
        return serial in self.clients


# Tạo instance global
connection_manager = ConnectionManager()
