from fastapi import APIRouter, HTTPException

from app.models.nlp import NLPRequest
from app.routers.websocket_router import send_command, Command
from app.services.audio.audio_service import text_to_mp3_bytes, text_to_wav_bytes
from app.services.nlp.nlp_service import process_text
from app.services.stt.stt_service import transcribe_bytes
from app.models.stt import ASRData, STTResponse
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
    try:
        resp = await transcribe_bytes(data)
        json_result = await process_text(resp.text)
        return json_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)

@router.post("/with-action-mp3")
async def transcribe_audio_with_file(data: ASRData):
    try:
        # 1) Transcribe + NLP
        resp = await transcribe_bytes(data)
        json_result = await process_text(resp.text)

        # 2) TTS in memory
        tts_meta = await text_to_mp3_bytes(json_result["data"]["text"])
        wav_bytes = tts_meta["bytes"]

        # 3) Headers (all fields except url)
        headers = {
            "X-Type": str(json_result.get("type", "")),
            "X-Text": str(json_result["data"].get("text", "")),
            "X-File-Name": str(tts_meta.get("file_name", "")),
            "X-Duration": str(tts_meta.get("duration", "")),
            "X-Voice": str(tts_meta.get("voice", "")),
            "X-Text-Length": str(tts_meta.get("text_length", "")),
            "Content-Disposition": f'attachment; filename="{tts_meta["file_name"]}"',
        }

        # 4) Return WAV directly in body
        return Response(
            content=wav_bytes,
            media_type="audio/wav",
            headers=headers,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/with-action-wav")
async def transcribe_audio_with_file(data: ASRData):
    try:
        # 1) Transcribe + NLP
        resp = await transcribe_bytes(data)
        json_result = await process_text(resp.text)

        # 2) TTS in memory
        tts_meta = await text_to_wav_bytes(json_result["data"]["text"])
        wav_bytes = tts_meta["bytes"]

        # 3) Headers (all fields except url)
        headers = {
            "X-Type": str(json_result.get("type", "")),
            "X-Text": str(json_result["data"].get("text", "")),
            "X-File-Name": str(tts_meta.get("file_name", "")),
            "X-Duration": str(tts_meta.get("duration", "")),
            "X-Voice": str(tts_meta.get("voice", "")),
            "X-Text-Length": str(tts_meta.get("text_length", "")),
            "Content-Disposition": f'attachment; filename="{tts_meta["file_name"]}"',
        }

        # 4) Return WAV directly in body
        return Response(
            content=wav_bytes,
            media_type="audio/wav",
            headers=headers,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

