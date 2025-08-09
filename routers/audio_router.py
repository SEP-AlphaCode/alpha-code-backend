from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import os
from services.audio_service import convert_audio_to_wav

router = APIRouter()

def remove_file(path: str):
    if os.path.exists(path):
        os.remove(path)

@router.post("/convert/to-wav")
async def convert_to_wav_api(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    if not (file.filename.lower().endswith(".mp3") or file.filename.lower().endswith(".mp4")):
        raise HTTPException(status_code=400, detail="Only .mp3 or .mp4 files are supported.")

    try:
        temp_out_path, download_name = await convert_audio_to_wav(file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")

    background_tasks.add_task(remove_file, temp_out_path)

    return FileResponse(
        path=temp_out_path,
        filename=download_name,
        media_type="audio/wav",
    )

