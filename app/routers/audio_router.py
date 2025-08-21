from fastapi import APIRouter, UploadFile, File, HTTPException, Body
import os
from app.services.audio.audio_service import convert_audio_to_wav_and_upload, text_to_wav_local

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


@router.post("/tts-local")
async def tts_local(text: str = Body(..., embed=True)):
    """Convert plain text to WAV (local file) and return path info."""
    try:
        result = await text_to_wav_local(text)
        return {
            "message": "Text synthesized successfully",
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS failed: {e}")
