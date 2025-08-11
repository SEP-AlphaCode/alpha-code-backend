import logging

from fastapi import APIRouter, UploadFile, HTTPException

from services.audio_parse_service import generate_actions, load_data

router = APIRouter()
logger = logging.getLogger('uvicorn.error')

@router.post('/parse')
async def parse_audio_file(file: UploadFile, change_threshold: float = 0.1):
    await load_data()
    if not (file.filename.lower().endswith(".wav")):
        raise HTTPException(status_code=400, detail="Only .wav files are supported.")
    try:
        service = await generate_actions(file=file, change_threshold=change_threshold)
        return service
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=e)