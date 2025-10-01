from fastapi import APIRouter, HTTPException

from app.services.nlp.nlp_service import process_text
from app.models.stt import ASRData

from app.services.stt.transcription_service import transcribe_bytes_vip

router = APIRouter()

@router.post('')
async def transcribe_audio(data: ASRData):
    try:
        return await transcribe_bytes_vip(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)

@router.post('/with-action')
async def transcribe_audio(data: ASRData):
    """
    Receive audio bytes, transcribe to text, classify action,
    generate TTS, and send command with combined JSON.
    """
    try:
        resp = await transcribe_bytes_vip(data)
        print(resp)
        json_result = await process_text(resp.text)
        return json_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)
