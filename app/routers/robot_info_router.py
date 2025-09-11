"""
Robot Info Router
API endpoint để lấy thông tin robot qua WebSocket
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional

from app.services.socket.robot_websocket_service import get_robot_info_via_websocket

router = APIRouter()


@router.post("/info/{serial}")
async def get_robot_info(
    serial: str,
    timeout: Optional[int] = Query(default=10, description="Timeout in seconds for robot response")
):
    """
    Lấy 4 thông tin cơ bản của robot qua WebSocket:
    - battery_level: Mức pin (%)  
    - firmware_version: Phiên bản firmware
    - ctrl_version: Phiên bản control
    - serial_number: Serial number
    
    Robot phải đã kết nối WebSocket trước khi gọi API này.
    
    Args:
        serial: Serial number của robot đã kết nối WebSocket
        timeout: Timeout chờ response từ robot (default: 10 seconds)
    """
    try:
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
        result = await get_robot_info_via_websocket(serial.strip(), timeout)
        
        return JSONResponse(
            content={
                "status": "success" if result['success'] else "error",
                "message": result['message'],
                "data": result['data']
            },
            status_code=200 if result['success'] else 400
        )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
