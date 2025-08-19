from fastapi import APIRouter
from app.services.nlp.nlp_service import process_text
from app.models.nlp import NLPRequest

router = APIRouter()

@router.post('/generate-dance-plan')
async def generate_dance_plan(req: NLPRequest):
    # Await the async service function; previously this returned a coroutine causing JSON serialization errors
    return await process_text(req)