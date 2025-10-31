"""
Robot Info Router
API endpoint để lấy thông tin robot qua WebSocket
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional
import logging

from app.services.socket.robot_websocket_service import get_robot_info_via_websocket, check_block_coding_status

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/info/{serial}")
async def get_robot_info(
    serial: str,
    timeout: Optional[int] = Query(default=10, description="Timeout in seconds for robot response")
):
    """
    Lấy 4 thông tin cơ bản của robot qua WebSocket:
    - battery_level: Mức pin (%)  
    - is_charging: Trạng thái sạc (true/false)
    - firmware_version: Phiên bản firmware
    - ctrl_version: Phiên bản control
    - serial_number: Serial number
    
    Robot phải đã kết nối WebSocket trước khi gọi API này.
    """
    try:
        logger.info(f"API call: get_robot_info for serial {serial}, timeout {timeout}s")
        
        # Validate input
        if not serial or len(serial.strip()) < 3:
            raise HTTPException(
                status_code=400, 
                detail="Serial number must be at least 3 characters long"
            )
        
        if timeout < 1 or timeout > 30:
            raise HTTPException(
                status_code=400,
                detail="Timeout must be between 1 and 30 seconds"
            )
        
        # Get robot info via WebSocket
        logger.info(f"Calling get_robot_info_via_websocket for {serial}")
        result = await get_robot_info_via_websocket(serial.strip(), timeout)
        logger.info(f"get_robot_info_via_websocket result for {serial}: {result}")
        logger.info(f"WebSocket result for {serial}: success={result.get('success')}, message={result.get('message')}")

        # ✅ Robot offline → HTTP 200, status=error
        if not result.get("success"):
            logger.warning(f"Failed to get robot info for {serial}: {result.get('message')}")
            return JSONResponse(
                content={
                    "status": "error",
                    "message": f"Robot {serial} not connected via WebSocket",
                    "data": {
                        "serial_number": serial,
                        "firmware_version": None,
                        "ctrl_version": None,
                        "battery_level": None,
                        "is_charging": False
                    }
                },
                status_code=200
            )

        # ✅ Robot online
        data = result.get('data')
        battery_level = data.get("battery_level")
        is_charging = data.get("is_charging", False)

        response_data = {
            "serial_number": data.get('serial_number'),
            "firmware_version": data.get('firmware_version'),
            "ctrl_version": data.get('ctrl_version'),
            "battery_level": battery_level,
            "is_charging": is_charging,
        }
        
        logger.info(f"Returning robot info for {serial}: battery={battery_level}%, charging={is_charging}, serial={data.get('serial_number')}")

        return JSONResponse(
            content={
                "status": "success",
                "message": "Robot info retrieved successfully",
                "data": response_data
            },
            status_code=200
        )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Internal server error getting robot info for {serial}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/coding-block/{serial}")
async def get_coding_block_status(serial: str, timeout: int = 10):
    try:
        if timeout < 1 or timeout > 30:
            raise HTTPException(
                status_code=400,
                detail="Timeout must be between 1 and 30 seconds"
            )
        
        result = await check_block_coding_status(serial)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )