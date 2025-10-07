from app.models.stt import ASRData, STTResponse
from app.services.nlp.nlp_service import process_text
from app.services.stt.stt_service import transcribe_bytes


async def process_speech(asr: ASRData):
    try:
        text: STTResponse = await transcribe_bytes(asr)
        resp = await process_text(text.text)
        return resp
    except Exception as e:
        raise e
