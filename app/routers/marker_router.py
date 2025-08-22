# routers/marker_router.py
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import shutil, os, base64, cv2

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

# -------- Embed marker --------
@router.post("/embed")
async def embed_marker(
    file: UploadFile = File(...),
    page_id: int = Form(...),
    size: int = Form(20),
    pos_x: Optional[str] = Form(None),
    pos_y: Optional[str] = Form(None)
):
    try:
        temp_path = f"temp_{file.filename}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        pos = None
        if pos_x and pos_y:  # chỉ khi cả hai khác rỗng
            pos = (int(pos_x), int(pos_y))

        out_path = service.embed_marker(temp_path, page_id, size=size, pos=pos)

        with open(out_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        data_url = f"data:image/png;base64,{b64}"

        os.remove(temp_path)

        return {
            "page_id": page_id,
            "size": size,
            "pos": pos,
            "result_image": data_url
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    
@router.post("/embed-hidden")
async def embed_marker(
    file: UploadFile = File(...),
    page_id: int = Form(...),
    size: int = Form(20),
):
    try:
        # lưu file tạm
        temp_path = f"temp_{file.filename}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        out_path = service.embed_marker(temp_path, page_id, size=size)

        # convert ảnh đã nhúng sang base64 (data URL)
        with open(out_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        data_url = f"data:image/png;base64,{b64}"

        # xóa file tạm
        os.remove(temp_path)

        return {
            "page_id": page_id,
            "size": size,
            "result_image": data_url
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))