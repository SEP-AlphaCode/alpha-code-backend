from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List
import json
import asyncio

class ConnectionManager:
    """Quản lý kết nối WebSocket cho giao tiếp real-time với robot Alpha Mini"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.robot_status: Dict[str, dict] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """Kết nối WebSocket client"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        print(f"✅ Robot {client_id} connected")

        # Initialize robot status
        self.robot_status[client_id] = {
            "connected": True,
            "last_ping": None,
            "current_action": None,
            "battery_level": None
        }

    def disconnect(self, client_id: str):
        """Ngắt kết nối WebSocket client"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.robot_status:
            del self.robot_status[client_id]
        print(f"❌ Robot {client_id} disconnected")

    async def send_personal_message(self, message: str, client_id: str):
        """Gửi tin nhắn tới một robot cụ thể"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(message)
            except WebSocketDisconnect:
                self.disconnect(client_id)

    async def send_json_message(self, data: dict, client_id: str):
        """Gửi JSON data tới robot"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(json.dumps(data))
            except WebSocketDisconnect:
                self.disconnect(client_id)

    async def broadcast(self, message: str):
        """Broadcast tin nhắn tới tất cả robot đang kết nối"""
        disconnected_clients = []

        for client_id, connection in self.active_connections.items():
            try:
                await connection.send_text(message)
            except WebSocketDisconnect:
                disconnected_clients.append(client_id)

        # Cleanup disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)

    async def broadcast_json(self, data: dict):
        """Broadcast JSON data tới tất cả robot"""
        await self.broadcast(json.dumps(data))

    def get_connected_robots(self) -> List[str]:
        """Lấy danh sách robot đang kết nối"""
        return list(self.active_connections.keys())

    def get_robot_status(self, client_id: str) -> dict:
        """Lấy status của robot"""
        return self.robot_status.get(client_id, {"connected": False})

    def update_robot_status(self, client_id: str, status_data: dict):
        """Cập nhật status của robot"""
        if client_id in self.robot_status:
            self.robot_status[client_id].update(status_data)

    async def send_choreography_command(self, client_id: str, choreography_data: dict):
        """Gửi lệnh thực hiện vũ đạo tới robot"""
        command = {
            "type": "execute_choreography",
            "data": choreography_data
        }
        await self.send_json_message(command, client_id)

    async def send_robot_command(self, client_id: str, action: str, parameters: dict):
        """Gửi lệnh điều khiển robot"""
        command = {
            "type": "robot_command",
            "action": action,
            "parameters": parameters
        }
        await self.send_json_message(command, client_id)

    async def ping_all_robots(self):
        """Ping tất cả robot để kiểm tra kết nối"""
        ping_message = {
            "type": "ping",
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.broadcast_json(ping_message)
