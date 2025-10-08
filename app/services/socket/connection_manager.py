"""
WebSocket Connection Manager
Quản lý kết nối WebSocket với các robot
"""
from fastapi import WebSocket
from typing import Dict, List
import logging


class WSMapEntry:
    websocket: WebSocket
    client_id: str
    
    def __init__(self, websocket, client_id):
        self.client_id = client_id
        self.websocket = websocket


class ConnectionManager:
    """Quản lý kết nối WebSocket với robot"""
    
    def __init__(self):
        # Store clients as {serial: websocket}
        self.clients: Dict[str, WSMapEntry] = {}
        self.logger = logging.getLogger(__name__)
    
    async def connect(self, websocket: WebSocket, serial: str) -> bool:
        """
        Kết nối WebSocket với robot
        Trả về True nếu kết nối thành công, False nếu từ chối
        """
        # if websocket.headers.get('client_id') is None:
        #     await websocket.close(code=1008, reason="Socket has no client id")
        #     return False
        
        # Kiểm tra nếu serial đã tồn tại
        # if serial in self.clients:
        #     try:
        #         # Nếu không có lỗi, kết nối vẫn active
        #         print(f"Từ chối kết nối từ robot {serial}, đã có kết nối active")
        #
        #         # Thông báo cho client lý do từ chối
        #         try:
        #             await websocket.close(code=1008, reason="Robot with this serial is already connected")
        #         except Exception as e:
        #             self.logger.error(f"Lỗi khi từ chối kết nối: {e}")
        #         return False
        #
        #     except Exception as e:
        #         # Nếu có lỗi, kết nối cũ đã bị ngắt nhưng chưa được dọn dẹp
        #         self.logger.info(f"Cleaning up stale connection for {serial}: {e}")
        #         await self.disconnect(serial)
        # Nếu serial chưa tồn tại hoặc kết nối cũ đã bị ngắt, cho phép kết nối mới
        await websocket.accept()
        self.clients[serial] = WSMapEntry(websocket, websocket.headers.get('client_id'))
        print(f"Robot {serial} connected. Total: {len(self.clients)}")
        return True
    
    async def disconnect(self, serial: str):
        print(serial, 'disconnecting')
        """Ngắt kết nối robot"""
        if serial in self.clients:
            ws = self.clients[serial].websocket
            try:
                if not ws.client_state.name == "DISCONNECTED":
                    await ws.close()
            except RuntimeError as e:
                self.logger.warning(f"WebSocket for {serial} already closed: {e}")
            except Exception as e:
                self.logger.error(f"Unexpected error closing WebSocket for {serial}: {e}")
            del self.clients[serial]
        else:
            self.logger.warning(f"Attempted to disconnect robot {serial} but it was not connected")
        
    async def disconnect_with_reason(self, serial: str, reason: str):
        print(serial, 'disconnecting')
        """Ngắt kết nối robot"""
        if serial in self.clients:
            ws: WebSocket = self.clients[serial].websocket
            try:
                if not ws.client_state.name == "DISCONNECTED":
                    await ws.close(reason=reason)
            except RuntimeError as e:
                self.logger.warning(f"WebSocket for {serial} already closed: {e}")
            except Exception as e:
                self.logger.error(f"Unexpected error closing WebSocket for {serial}: {e}")
            del self.clients[serial]
        else:
            self.logger.warning(f"Attempted to disconnect robot {serial} but it was not connected")
    
    async def send_to_robot(self, serial: str, message: str) -> bool:
        """Gửi message tới robot"""
        client = self.clients.get(serial)
        if client and hasattr(client, 'websocket'):
            ws = client.websocket
            if ws:
                try:
                    if ws.client_state.name == "CONNECTED":
                        await ws.send_text(message)
                        return True
                    else:
                        self.logger.warning(f"Cannot send message to {serial}: websocket not connected")
                except RuntimeError as e:
                    self.logger.error(f"Send error to {serial}: {e}")
                    await self.disconnect(serial)
                except Exception as e:
                    self.logger.error(f"Unexpected send error to {serial}: {e}")
                    await self.disconnect(serial)
            else:
                self.logger.warning(f"Cannot send message to {serial}: websocket not available")
        else:
            self.logger.warning(f"Cannot send message to {serial}: robot not connected")
        return False
    
    @property
    def active(self) -> int:
        """Số lượng robot đang kết nối"""
        return len(self.clients)
    
    def is_connected(self, serial: str) -> bool:
        """Kiểm tra robot có đang kết nối không"""
        return serial in self.clients
    
    def get_connected_serials(self) -> List[str]:
        """Lấy danh sách các serial đang kết nối"""
        return list(self.clients.keys())


# Tạo instance global
connection_manager = ConnectionManager()
