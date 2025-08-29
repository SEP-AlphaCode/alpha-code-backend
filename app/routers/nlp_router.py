from fastapi import APIRouter, UploadFile, Response, HTTPException

from app.services.audio.audio_service import text_to_mp3_bytes
from app.services.nlp.nlp_service import process_text, process_audio
from app.models.nlp import NLPRequest

router = APIRouter()

@router.post('/process-audio')
async def process_audio_endpoint(file: UploadFile):
    # Await the async service function; previously this returned a coroutine causing JSON serialization errors
    return await process_audio(file)

@router.post('/process-text')
async def process_text_endpoint(request: NLPRequest):
    return await process_text(request.text)
@router.post("/tts")
async def do_tts(input_text: NLPRequest):
    try:
        json_result = await process_text(input_text.text)

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
