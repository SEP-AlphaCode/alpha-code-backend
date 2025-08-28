from fastapi import APIRouter, UploadFile
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
