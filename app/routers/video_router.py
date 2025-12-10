from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import Optional
import uuid
from app.services.video.video_service import generate_video_from_image
from app.services.video.video_capture_service import upload_image_to_s3
from app.repositories.robot_repository import get_robot_by_serial
from app.repositories.video_capture_repository import create_video_capture

router = APIRouter()

@router.post("/generate")
async def generate_video_from_image_api(
    file: UploadFile = File(..., description="Image file (JPG, PNG, etc.)"),
    description: Optional[str] = Form(
        default="",
        description="Mô tả bổ sung cho video (tùy chọn). Ví dụ: 'với ánh sáng mặt trời chiếu xuống' hoặc 'trong không khí yên bình'"
    ),
    use_default_template: bool = Form(
        default=True,
        description="Sử dụng mẫu prompt mặc định (khuyến nghị). Nếu false, chỉ dùng description thuần túy."
    )
):
    """
    Generate animated video from a static image using AI

    **Cách sử dụng:**
    - Upload một bức ảnh (JPG, PNG, etc.)
    - Có thể thêm mô tả bổ sung (tùy chọn) để AI tạo video theo hướng mong muốn
    - Nếu không có description, AI sẽ tự động tạo chuyển động tự nhiên cho ảnh

    **Ví dụ description:**
    - "với gió thổi nhẹ và lá cây rung động"
    - "trong ánh hoàng hôn ấm áp"
    - "với người đang từ từ mỉm cười"
    - "" (để trống để AI tự động tạo chuyển động tự nhiên)

    **Response:**
    - video_url: URL của video đã generate (từ Replicate)
    - prompt: Prompt đầy đủ đã sử dụng
    - original_filename: Tên file ảnh gốc
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Chỉ chấp nhận file ảnh (JPG, PNG, etc.)"
        )

    try:
        result = await generate_video_from_image(
            file=file,
            description=description,
            use_default_template=use_default_template,
        )

        return {
            "message": "Video đã được tạo thành công",
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi tạo video: {str(e)}"
        )

@router.get("/health")
async def health_check():
    """
    Check if video generation service is configured properly
    """
    import os

    if not os.getenv("REPLICATE_API_TOKEN"):
        return {
            "status": "unhealthy",
            "message": "Missing REPLICATE_API_TOKEN environment variable"
        }

    return {
        "status": "healthy",
        "message": "Video generation service is configured properly"
    }


@router.post("/capture/test")
async def test_video_capture(
    file: UploadFile = File(..., description="Image file to upload and create video capture record"),
    serial_number: str = Form(..., description="Robot serial number"),
    description: Optional[str] = Form(
        default=None,
        description="Description for video generation (optional)"
    )
):
    """
    Test endpoint for video capture flow (parse-video command simulation)

    **Flow:**
    1. Validate robot exists by serial number
    2. Upload image to S3
    3. Create video_capture record in database

    **Parameters:**
    - file: Image file (JPG, PNG, etc.)
    - serial_number: Robot serial number (must exist and be active)
    - description: Optional description for video generation

    **Response:**
    - success: Boolean
    - message: Status message
    - data: Contains video_capture_id, image_url, account_id
    """
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail="Only image files are accepted (JPG, PNG, etc.)"
            )

        # Step 1: Get robot by serial number
        robot = await get_robot_by_serial(serial_number)

        if not robot:
            raise HTTPException(
                status_code=404,
                detail=f"Robot with serial number '{serial_number}' not found or inactive"
            )

        account_id = robot.account_id

        # Step 2: Upload image to S3
        image_bytes = await file.read()
        image_url = await upload_image_to_s3(image_bytes)

        if not image_url:
            raise HTTPException(
                status_code=500,
                detail="Failed to upload image to S3"
            )

        # Step 3: Create video_capture record
        final_description = description or "Hãy biến bức ảnh này thành video sinh động"
        video_capture = await create_video_capture(
            image_url=image_url,
            account_id=account_id,
            description=final_description
        )

        if not video_capture:
            raise HTTPException(
                status_code=500,
                detail="Failed to create video_capture record in database"
            )

        return {
            "success": True,
            "message": "Video capture created successfully",
            "data": {
                "video_capture_id": str(video_capture.id),
                "image_url": image_url,
                "account_id": str(account_id),
                "description": final_description,
                "is_created": video_capture.is_created,
                "status": video_capture.status,
                "created_date": video_capture.created_date.isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error in video capture: {str(e)}"
        )


@router.post("/capture/by-account")
async def test_video_capture_by_account(
    file: UploadFile = File(..., description="Image file to upload and create video capture record"),
    account_id: str = Form(..., description="Account ID (UUID)"),
    description: Optional[str] = Form(
        default=None,
        description="Description for video generation (optional)"
    )
):
    """
    Test endpoint for video capture flow with direct account_id (no robot needed)

    **Flow:**
    1. Upload image to S3
    2. Create video_capture record in database with provided account_id

    **Parameters:**
    - file: Image file (JPG, PNG, etc.)
    - account_id: Account UUID
    - description: Optional description for video generation

    **Response:**
    - success: Boolean
    - message: Status message
    - data: Contains video_capture_id, image_url, account_id
    """
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail="Only image files are accepted (JPG, PNG, etc.)"
            )

        # Parse account_id as UUID
        try:
            parsed_account_id = uuid.UUID(account_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid account_id format. Must be a valid UUID."
            )

        # Step 1: Upload image to S3
        image_bytes = await file.read()
        image_url = await upload_image_to_s3(image_bytes)

        if not image_url:
            raise HTTPException(
                status_code=500,
                detail="Failed to upload image to S3"
            )

        # Step 2: Create video_capture record
        final_description = description or "Hãy biến bức ảnh này thành video sinh động"
        video_capture = await create_video_capture(
            image_url=image_url,
            account_id=parsed_account_id,
            description=final_description
        )

        if not video_capture:
            raise HTTPException(
                status_code=500,
                detail="Failed to create video_capture record in database"
            )

        return {
            "success": True,
            "message": "Video capture created successfully",
            "data": {
                "video_capture_id": str(video_capture.id),
                "image_url": image_url,
                "account_id": str(parsed_account_id),
                "description": final_description,
                "is_created": video_capture.is_created,
                "status": video_capture.status,
                "created_date": video_capture.created_date.isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error in video capture: {str(e)}"
        )


