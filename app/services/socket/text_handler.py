import json

from app.services.socket import robot_websocket_info_service


async def handle_text_message(data: str, serial: str) -> None:
    """Handle text messages from the robot"""
    try:
        message_data = json.loads(data)
        await process_robot_message(message_data, serial)
    except json.JSONDecodeError:
        print(f"Invalid JSON received from robot {serial}")
    except Exception as e:
        print(f"Error processing text message from robot {serial}: {e}")


async def process_robot_message(message_data: dict, serial: str):
    """Process robot messages regardless of original format"""
    try:
        message_type = message_data.get('type')
        
        if message_type == 'get_system_info' and 'data' in message_data:
            response_message = {
                'type': 'system_info_response',
                'data': message_data['data']
            }
            robot_websocket_info_service.handle_robot_response(response_message)
        else:
            robot_websocket_info_service.handle_robot_response(message_data)
    
    except Exception as e:
        print(f"Error in process_robot_message for robot {serial}: {e}")