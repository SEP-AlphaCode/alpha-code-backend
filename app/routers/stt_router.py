from fastapi import APIRouter, HTTPException

from app.routers.websocket_router import send_command, Command
from app.services.nlp.nlp_service import process_text
from app.services.stt.stt_service import transcribe_bytes
from app.models.stt import ASRData
from app.services.audio.audio_service import text_to_wav_and_upload

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
        # 1. Transcribe raw audio bytes to text
        resp = await transcribe_bytes(data)  # returns object with 'text' attribute

        # 2. Process the transcribed text to get JSON classification
        # Example output: {"type": "<greeting|study|dance|...>", "data": {"text": "..."}}
        json_raw = await process_text(resp.text)

        # 3. Combine original text with TTS result
        json_combined = {
            "type": json_raw['type'],
            "data": {
                "text": json_raw['data']['text'],
            }
        }

        # 4. Send command to client or robot
        await send_command(Command(type=json_combined['type'], data=json_combined['data']))

        # 5. Return combined JSON as API response
        return json_combined

    except Exception as e:
        # If any error occurs, raise HTTP 500
        raise HTTPException(status_code=500, detail=str(e))