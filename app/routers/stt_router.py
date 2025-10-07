from fastapi import APIRouter, HTTPException
from app.services.nlp.nlp_service import process_text
from app.services.stt.stt_service import transcribe_bytes
from app.models.stt import ASRData
from fastapi.responses import Response
router = APIRouter()

@router.post('')
async def transcribe_audio(data: ASRData):
    try:
        return await transcribe_bytes(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)

@router.post('/with-action')
async def transcribe_audio(data: ASRData):
    """
    Receive audio bytes, transcribe to text, classify action,
    generate TTS, and send command with combined JSON.
    """
    try:
        resp = await transcribe_bytes(data)
        json_result = await process_text(resp.text)
        return json_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)
