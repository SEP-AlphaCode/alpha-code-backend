from fastapi import APIRouter, HTTPException

from app.routers.websocket_router import send_command, Command
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
        json_result = await process_text(resp.text)
        await send_command(Command(type=json_result['type'], data=json_result['data']))
        raise json_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)