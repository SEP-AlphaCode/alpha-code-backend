from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import Optional
from app.services.video.video_service import generate_video_from_image

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

