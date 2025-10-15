# app/routers/object_router.py
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException
import cv2
import numpy as np
from app.models.object_detect import DetectClosestResponse, Detection
from app.services.object_detect.object_detect_service import detect_closest_objects_from_bytes

router = APIRouter()


@router.post("/detect_closest")
async def detect_closest_objects(file: UploadFile = File(...), k: int = 3) -> DetectClosestResponse:
    try:
        image_bytes = await file.read()
        return detect_closest_objects_from_bytes(image_bytes, k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

