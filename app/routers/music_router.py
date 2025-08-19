from fastapi import APIRouter
from pydantic import BaseModel
from app.services.music.planner import build_activity_json

router = APIRouter()

class MusicRequest(BaseModel):
    music_name: str
    music_url: str
    duration: float  # seconds

@router.post('/generate-dance-plan')
async def generate_dance_plan(req: MusicRequest):
    return build_activity_json(req.music_name, req.music_url, req.duration)
