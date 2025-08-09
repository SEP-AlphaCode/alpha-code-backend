from fastapi import APIRouter, UploadFile, HTTPException

from services.audio_parse_service import generate_sequence

router = APIRouter()

@router.post('/parse')
async def parse_audio_file(file: UploadFile):
    if not (file.filename.lower().endswith(".wav")):
        raise HTTPException(status_code=400, detail="Only .wav files are supported.")

    service = await generate_sequence(file)
    return service