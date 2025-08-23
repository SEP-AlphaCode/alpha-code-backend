from fastapi import APIRouter, UploadFile
from app.services.nlp.nlp_service import process_text, process_audio
from app.models.nlp import NLPRequest

router = APIRouter()

@router.post('/generate-dance-plan')
async def generate_dance_plan(file: UploadFile):
    # Await the async service function; previously this returned a coroutine causing JSON serialization errors
    return await process_audio(file)