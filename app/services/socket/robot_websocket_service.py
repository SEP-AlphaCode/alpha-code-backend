"""
Robot WebSocket Info Service
Service để gửi command qua WebSocket yêu cầu robot trả về thông tin hệ thống
"""

import asyncio
import json
import logging
from typing import Dict, Optional, Any
from datetime import datetime

from .connection_manager import connection_manager


class RobotWebSocketInfoService:
    """Service để gửi lệnh lấy thông tin robot qua WebSocket"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.pending_requests = {}  # Lưu các request đang chờ response
    
    async def send_info_request(self, serial: str, timeout: int = 10) -> Dict[str, Any]:
        """
        Gửi yêu cầu lấy thông tin robot qua WebSocket
        
        Args:
            serial: Serial number của robot
            timeout: Timeout chờ response (seconds)
            
        Returns:
            Dict chứa thông tin robot hoặc error
        """
        try:
            # Kiểm tra robot có kết nối không
            if serial not in connection_manager.clients:
                return {
                    'success': False,
                    'data': {
                        'battery_level': None,
                        'firmware_version': None,
                        'ctrl_version': None,
                        'serial_number': None
                    },
                    'message': f'Robot {serial} not connected via WebSocket'
                }
            
            # Tạo command để yêu cầu thông tin hệ thống
            request_id = f"info_req_{datetime.now().timestamp()}"
            command = {
                "type": "get_system_info",
                "request_id": request_id,
                "data": {
                    "info_types": ["battery", "firmware", "ctrl_version", "serial"]
                }
            }
            
            # Tạo event để chờ response
            response_event = asyncio.Event()
            self.pending_requests[request_id] = {
                'event': response_event,
                'response': None,
                'timestamp': datetime.now()
            }
            
            # Gửi command tới robot
            command_json = json.dumps(command)
            success = await connection_manager.send_to_robot(serial, command_json)
            
            if not success:
                del self.pending_requests[request_id]
                return {
                    'success': False,
                    'data': {
                        'battery_level': None,
                        'firmware_version': None,
                        'ctrl_version': None,
                        'serial_number': None
                    },
                    'message': f'Failed to send command to robot {serial}'
                }
            
            # Chờ response từ robot
            try:
                await asyncio.wait_for(response_event.wait(), timeout=timeout)
                
                # Lấy response
                if request_id in self.pending_requests:
                    response_data = self.pending_requests[request_id]['response']
                    del self.pending_requests[request_id]
                    
                    if response_data:
                        return self.parse_robot_response(response_data)
                    else:
                        return {
                            'success': False,
                            'data': {
                                'battery_level': None,
                                'firmware_version': None,
                                'ctrl_version': None,
                                'serial_number': None
                            },
                            'message': 'No response received from robot'
                        }
                else:
                    return {
                        'success': False,
                        'data': {
                            'battery_level': None,
                            'firmware_version': None,
                            'ctrl_version': None,
                            'serial_number': None
                        },
                        'message': 'Request not found in pending requests'
                    }
                    
            except asyncio.TimeoutError:
                # Cleanup pending request
                if request_id in self.pending_requests:
                    del self.pending_requests[request_id]
                
                return {
                    'success': False,
                    'data': {
                        'battery_level': None,
                        'firmware_version': None,
                        'ctrl_version': None,
                        'serial_number': None
                    },
                    'message': f'Timeout waiting for response from robot {serial}'
                }
                
        except Exception as e:
            self.logger.error(f"Error sending info request to robot {serial}: {e}")
            return {
                'success': False,
                'data': {
                    'battery_level': None,
                    'firmware_version': None,
                    'ctrl_version': None,
                    'serial_number': None
                },
                'message': f'Service error: {str(e)}'
            }
    
    def parse_robot_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse response từ robot và trích xuất 4 thông tin cần thiết
        
        Args:
            response_data: Raw response từ robot
            
        Returns:
            Dict chứa 4 thông tin đã parse
        """
        try:
            # Giả sử robot trả về format:
            # {
            #   "type": "system_info_response",
            #   "data": {
            #     "battery_level": 85,
            #     "firmware_version": "v2.1.0", 
            #     "ctrl_version": "v1.5.2",
            #     "serial_number": "AM123456789"
            #   }
            # }
            
            data = response_data.get('data', {})
            
            return {
                'success': True,
                'data': {
                    'battery_level': data.get('battery_level'),
                    'firmware_version': data.get('firmware_version'),
                    'ctrl_version': data.get('ctrl_version'),
                    'serial_number': data.get('serial_number')
                },
                'message': 'Robot info retrieved successfully via WebSocket'
            }
            
        except Exception as e:
            self.logger.error(f"Error parsing robot response: {e}")
            return {
                'success': False,
                'data': {
                    'battery_level': None,
                    'firmware_version': None,
                    'ctrl_version': None,
                    'serial_number': None
                },
                'message': f'Error parsing robot response: {str(e)}'
            }
    
    def handle_robot_response(self, message_data: Dict[str, Any]):
        """
        Xử lý response từ robot (được gọi từ WebSocket handler)
        
        Args:
            message_data: Message data từ robot
        """
        try:
            message_type = message_data.get('type')
            request_id = message_data.get('request_id')
            
            if message_type == 'system_info_response' and request_id:
                if request_id in self.pending_requests:
                    # Lưu response và trigger event
                    self.pending_requests[request_id]['response'] = message_data
                    self.pending_requests[request_id]['event'].set()
                    
        except Exception as e:
            self.logger.error(f"Error handling robot response: {e}")
    
    def cleanup_old_requests(self, max_age_seconds: int = 60):
        """Cleanup các request cũ để tránh memory leak"""
        try:
            current_time = datetime.now()
            old_requests = []
            
            for request_id, request_info in self.pending_requests.items():
                age = (current_time - request_info['timestamp']).total_seconds()
                if age > max_age_seconds:
                    old_requests.append(request_id)
            
            for request_id in old_requests:
                del self.pending_requests[request_id]
                
        except Exception as e:
            self.logger.error(f"Error cleaning up old requests: {e}")


# Tạo instance global
robot_websocket_info_service = RobotWebSocketInfoService()


# Function để gọi từ router
async def get_robot_info_via_websocket(serial: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Lấy thông tin robot qua WebSocket
    
    Args:
        serial: Serial number của robot
        timeout: Timeout chờ response (seconds)
        
    Returns:
        Dict chứa thông tin robot
    """
    # Cleanup old requests trước khi thực hiện request mới
    robot_websocket_info_service.cleanup_old_requests()
    
    # Gửi request và chờ response
    return await robot_websocket_info_service.send_info_request(serial, timeout)
