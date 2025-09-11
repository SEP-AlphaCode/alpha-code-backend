"""
Socket services module
Chứa các service liên quan đến socket và communication với robot
"""

from .robot_websocket_service import get_robot_info_via_websocket, robot_websocket_info_service
from .websocket_patch import apply_websocket_patch

__all__ = [
    'get_robot_info_via_websocket',
    'robot_websocket_info_service',
    'apply_websocket_patch'
]