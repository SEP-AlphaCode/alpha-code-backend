import traceback

from fastapi import APIRouter, HTTPException

from app.services.semantic.semantic import TaskClassifier

router = APIRouter()

@router.get("/match")
async def test(t: str, k: int = 3):
    try:
        return TaskClassifier().classify_task(t, k)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))