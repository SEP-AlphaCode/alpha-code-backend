# routers/marker_router.py
from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil, os
from app.services.marker.marker_service import MarkerService
from app.models.marker import MarkerResponse

router = APIRouter()
service = MarkerService()

@router.post("/detect", response_model=MarkerResponse)
async def detect_marker(file: UploadFile = File(...)):
    try:
        # Lưu file tạm
        temp_path = f"temp_{file.filename}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        result = service.detect_marker(temp_path)

        # Xóa file sau khi xử lý
        os.remove(temp_path)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
