from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import List, Optional
import os
import uuid
import aiofiles
from pathlib import Path

from app.models.schemas import (
    MusicAnalysisRequest,
    MusicAnalysisResult,
    UploadResponse
)
from app.services.music_analysis import MusicAnalysisService
from app.core.config import settings

router = APIRouter()
music_service = MusicAnalysisService()

@router.post("/upload", response_model=UploadResponse)
async def upload_music_file(file: UploadFile = File(...)):
    """Upload file nhạc để phân tích"""

    # Kiểm tra định dạng file
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in settings.ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format. Allowed: {settings.ALLOWED_AUDIO_EXTENSIONS}"
        )

    # Kiểm tra kích thước file
    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {settings.MAX_FILE_SIZE} bytes"
        )

    try:
        # Tạo tên file unique
        file_id = str(uuid.uuid4())
        filename = f"{file_id}_{file.filename}"
        file_path = f"uploads/music/{filename}"

        # Lưu file
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)

        return UploadResponse(
            success=True,
            message="File uploaded successfully",
            file_id=file_id,
            filename=filename
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

@router.post("/analyze/{file_id}", response_model=MusicAnalysisResult)
async def analyze_music_file(file_id: str):
    """Phân tích file nhạc đã upload"""

    try:
        # Tìm file trong thư mục uploads
        upload_dir = "uploads/music"
        target_file = None

        for filename in os.listdir(upload_dir):
            if filename.startswith(file_id):
                target_file = filename
                break

        if not target_file:
            raise HTTPException(status_code=404, detail="File not found")

        file_path = f"{upload_dir}/{target_file}"

        # Phân tích file
        result = await music_service.analyze_audio_file(file_path, target_file)

        return result

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing file: {str(e)}")

@router.get("/analysis/{analysis_id}", response_model=MusicAnalysisResult)
async def get_analysis_result(analysis_id: str):
    """Lấy kết quả phân tích đã lưu"""

    try:
        result = await music_service.load_analysis_result(analysis_id)
        return result
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Analysis result not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading analysis: {str(e)}")

@router.get("/analysis", response_model=List[dict])
async def list_analysis_results():
    """Liệt kê tất cả kết quả phân tích"""

    try:
        results = await music_service.list_analysis_results()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing analysis results: {str(e)}")

@router.delete("/analysis/{analysis_id}")
async def delete_analysis_result(analysis_id: str):
    """Xóa kết quả phân tích"""

    try:
        analysis_file = f"data/analysis/{analysis_id}.json"

        if not os.path.exists(analysis_file):
            raise HTTPException(status_code=404, detail="Analysis result not found")

        os.remove(analysis_file)

        return {"success": True, "message": "Analysis result deleted successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting analysis: {str(e)}")

@router.post("/upload-batch")
async def upload_multiple_music_files(files: List[UploadFile] = File(...)):
    """Upload nhiều file nhạc cùng lúc"""

    results = []

    for file in files:
        try:
            # Kiểm tra định dạng
            file_extension = Path(file.filename).suffix.lower()
            if file_extension not in settings.ALLOWED_AUDIO_EXTENSIONS:
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": f"Unsupported format: {file_extension}"
                })
                continue

            # Upload file
            content = await file.read()
            if len(content) > settings.MAX_FILE_SIZE:
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": "File too large"
                })
                continue

            file_id = str(uuid.uuid4())
            filename = f"{file_id}_{file.filename}"
            file_path = f"uploads/music/{filename}"

            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)

            results.append({
                "filename": file.filename,
                "success": True,
                "file_id": file_id,
                "saved_as": filename
            })

        except Exception as e:
            results.append({
                "filename": file.filename,
                "success": False,
                "error": str(e)
            })

    return {"results": results}
