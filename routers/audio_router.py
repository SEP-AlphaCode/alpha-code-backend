from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import os
from services.audio_service import convert_audio_to_wav_and_upload

router = APIRouter()

def remove_file(path: str):
    if os.path.exists(path):
        os.remove(path)

@router.post("/convert/to-wav")
async def convert_to_wav_api(file: UploadFile = File(...)):
    # Chỉ cho phép mp3 và mp4
    if not (file.filename.lower().endswith(".mp3") or file.filename.lower().endswith(".mp4")):
        raise HTTPException(status_code=400, detail="Only .mp3 or .mp4 files are supported.")

    try:
        result = await convert_audio_to_wav_and_upload(file)
        return {
            "message": "File converted and uploaded successfully",
            "file_name": result["file_name"],
            "url": result["url"],
            "duration": result["duration"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion or upload failed: {str(e)}")
