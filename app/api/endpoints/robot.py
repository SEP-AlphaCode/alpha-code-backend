from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
import asyncio

from app.models.schemas import RobotStatus, RobotCommand, RobotAction
from app.services.websocket_manager import ConnectionManager
from app.services.choreography import ChoreographyService
from app.services.alpha_mini_robot import robot_service

router = APIRouter()
manager = ConnectionManager()
choreography_service = ChoreographyService()

@router.post("/search-robots")
async def search_robots(timeout: int = 10):
    """Tìm kiếm tất cả robot Alpha Mini có sẵn"""

    try:
        devices = await robot_service.search_all_robots(timeout)

        robots = []
        for device in devices:
            robots.append({
                "name": device.name,
                "ip": device.ip,
                "port": device.port,
                "id": f"{device.name}_{device.ip}"
            })

        return {
            "success": True,
            "robots_found": len(robots),
            "robots": robots
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching robots: {str(e)}")

@router.post("/search-robot/{serial_suffix}")
async def search_robot_by_serial(serial_suffix: str, timeout: int = 10):
    """Tìm kiếm robot Alpha Mini bằng serial number suffix"""

    try:
        device = await robot_service.search_robot_by_serial(serial_suffix, timeout)

        if device:
            return {
                "success": True,
                "robot": {
                    "name": device.name,
                    "ip": device.ip,
                    "port": device.port,
                    "id": f"{device.name}_{device.ip}"
                }
            }
        else:
            return {
                "success": False,
                "message": f"No robot found with serial suffix: {serial_suffix}"
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching robot: {str(e)}")

@router.post("/connect")
async def connect_robot(robot_name: str, robot_ip: str, robot_port: int = 20001):
    """Kết nối với robot Alpha Mini"""

    try:
        # Create WiFiDevice object
        from app.services.alpha_mini_robot import WiFiDevice
        device = WiFiDevice(robot_name, robot_ip, robot_port)

        connected = await robot_service.connect_robot(device)

        if connected:
            return {
                "success": True,
                "message": f"Successfully connected to robot {robot_name}",
                "robot_id": f"{robot_name}_{robot_ip}"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to connect to robot")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error connecting to robot: {str(e)}")

@router.post("/disconnect")
async def disconnect_robot():
    """Ngắt kết nối với robot Alpha Mini"""

    try:
        disconnected = await robot_service.disconnect_robot()

        if disconnected:
            return {
                "success": True,
                "message": "Robot disconnected successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to disconnect robot")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error disconnecting robot: {str(e)}")

@router.get("/status")
async def get_all_robots_status():
    """Lấy trạng thái của tất cả robot đang kết nối"""

    try:
        robot_status = robot_service.get_all_robot_status()

        # Combine with WebSocket connections
        websocket_robots = manager.get_connected_robots()

        return {
            "physical_robots": robot_status,
            "websocket_connections": len(websocket_robots),
            "total_connected": len(robot_status) + len(websocket_robots)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting robot status: {str(e)}")

@router.post("/execute-choreography-physical")
async def execute_choreography_on_physical_robot(choreography_id: str):
    """Thực hiện vũ đạo trên robot Alpha Mini thực tế"""

    try:
        if not robot_service.is_connected:
            raise HTTPException(status_code=400, detail="No physical robot connected")

        # Load choreography data
        choreography = await choreography_service.load_choreography(choreography_id)

        # Execute on physical robot
        success = await robot_service.execute_choreography(choreography)

        if success:
            return {
                "success": True,
                "message": f"Choreography executed on physical robot",
                "choreography_id": choreography_id,
                "duration": choreography.total_duration,
                "robot": robot_service.current_device.name if robot_service.current_device else "Unknown"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to execute choreography on robot")

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Choreography not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing choreography: {str(e)}")

@router.post("/command-physical")
async def send_command_to_physical_robot(command: RobotCommand):
    """Gửi lệnh điều khiển đến robot Alpha Mini thực tế"""

    try:
        if not robot_service.is_connected:
            raise HTTPException(status_code=400, detail="No physical robot connected")

        # Execute single action on physical robot
        await robot_service.execute_robot_action(
            command.action,
            command.parameters,
            command.duration or 3.0
        )

        return {
            "success": True,
            "message": f"Command '{command.action.value}' sent to physical robot",
            "robot": robot_service.current_device.name if robot_service.current_device else "Unknown"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending command to physical robot: {str(e)}")

# Keep existing endpoints for WebSocket robots
@router.get("/status/{robot_id}")
async def get_robot_status(robot_id: str):
    """Lấy trạng thái của một robot cụ thể (WebSocket hoặc physical)"""

    # Check physical robot first
    physical_status = robot_service.get_robot_status(robot_id)
    if physical_status.get("status") != "not_connected":
        return {
            "robot_id": robot_id,
            "type": "physical",
            "status": physical_status
        }

    # Check WebSocket robots
    if robot_id in manager.get_connected_robots():
        websocket_status = manager.get_robot_status(robot_id)
        return {
            "robot_id": robot_id,
            "type": "websocket",
            "status": websocket_status
        }

    raise HTTPException(status_code=404, detail="Robot not found")

@router.post("/execute-choreography/{robot_id}")
async def execute_choreography(robot_id: str, choreography_id: str):
    """Thực hiện vũ đạo trên robot (WebSocket)"""

    if robot_id not in manager.get_connected_robots():
        raise HTTPException(status_code=404, detail="Robot not connected via WebSocket")

    try:
        # Load choreography data
        choreography = await choreography_service.load_choreography(choreography_id)

        # Prepare choreography data for WebSocket robot
        choreography_data = {
            "choreography_id": choreography.id,
            "total_duration": choreography.total_duration,
            "bpm": choreography.bpm,
            "segments": []
        }

        for segment in choreography.segments:
            choreography_data["segments"].append({
                "start_time": segment.start_time,
                "end_time": segment.end_time,
                "action": segment.action.value,
                "parameters": segment.parameters,
                "ubx_file": segment.ubx_file,
                "intensity": segment.intensity
            })

        # Send to WebSocket robot
        await manager.send_choreography_command(robot_id, choreography_data)

        return {
            "success": True,
            "message": f"Choreography sent to WebSocket robot {robot_id}",
            "choreography_id": choreography_id,
            "duration": choreography.total_duration,
            "type": "websocket"
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Choreography not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing choreography: {str(e)}")
