from fastapi import APIRouter, HTTPException

from app.services.nlp.nlp_service import process_text
from app.services.stt.stt_service import transcribe_bytes
from app.models.stt import ASRData, STTResponse

router = APIRouter()

@router.post('')
async def transcribe_audio(data: ASRData):
    try:
        return await transcribe_bytes(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)

@router.post('/with-action')
async def transcribe_audio(data: ASRData):
    try:
        resp = await transcribe_bytes(data)
        return await process_text(resp.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)