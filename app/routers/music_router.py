from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.audio.audio_service import convert_audio_to_wav_and_upload
from app.services.music.planner import build_activity_json
from fastapi import APIRouter, UploadFile, File, HTTPException, Body, Query

router = APIRouter()


class MusicRequest(BaseModel):
    music_name: str
    music_url: str
    duration: float  # seconds


@router.post('/generate-dance-plan')
async def generate_dance_plan(req: MusicRequest):
    return build_activity_json(req.music_name, req.music_url, req.duration)


@router.post('/upload-music-and-generate-plan')
async def upload_music_and_generate_plan(
        file: UploadFile = File(...),
        start_time: Optional[float] = Query(None, description="Start time in seconds (optional)", ge=0),
        end_time: Optional[float] = Query(None, description="End time in seconds (optional)", ge=0)):
    # Chỉ cho phép mp3 và mp4
    if not (file.filename.lower().endswith(".mp3") or file.filename.lower().endswith(".mp4")):
        raise HTTPException(status_code=400, detail="Only .mp3 or .mp4 files are supported.")

    # Validate time parameters
    if start_time is not None and end_time is not None and start_time >= end_time:
        raise HTTPException(status_code=400, detail="start_time must be less than end_time")

    try:
        result = await convert_audio_to_wav_and_upload(file, start_time=start_time, end_time=end_time)

        # Add trimming info to response if parameters were provided

        response_data = build_activity_json(result["file_name"], result["url"], result["duration"])

        # lấy phần data ra
        new_res_data = response_data['data'].copy()

        # map start_time / end_time vào music_info nếu có
        if start_time is not None or end_time is not None:
            new_res_data['music_info']['start_time'] = start_time
            new_res_data['music_info']['end_time'] = end_time


        return new_res_data
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion or upload failed: {str(e)}")
