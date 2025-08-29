from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict

class RobotWebSocketManager:
    """Manager for robot WebSocket connections.

    Responsibilities:
    - Accept and track WebSocket connections keyed by robot serial
    - Send/receive text messages to/from a robot
    - Handle disconnects and basic error logging
    """

    def __init__(self):
        self.clients: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, serial: str):
        await websocket.accept()
        self.clients[serial] = websocket
        print(f"Robot {serial} connected. Total: {len(self.clients)}")

    def disconnect(self, serial: str):
        if serial in self.clients:
            del self.clients[serial]
            print(f"Robot {serial} disconnected. Total: {len(self.clients)}")

    async def receive(self, serial: str):
        ws = self.clients.get(serial)
        if ws:
            try:
                return await ws.receive_text()
            except Exception as e:
                print(f"Receive error from {serial}: {e}")
                self.disconnect(serial)
        return None

    async def send(self, serial: str, message: str) -> bool:
        ws = self.clients.get(serial)
        if ws:
            try:
                await ws.send_text(message)
                return True
            except Exception as e:
                print(f"Send error to {serial}: {e}")
                self.disconnect(serial)
        return False

    @property
    def active(self) -> int:
        return len(self.clients)

# Export a single manager instance for application-wide use
manager = RobotWebSocketManager()
