# app/db/repos/dance_repo.py
from sqlalchemy.future import select
from typing import List, Optional
from app.entities.database import AsyncSessionLocal
from app.entities.dance import Dance

async def get_all_dances() -> List[Dance]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Dance))
        return result.scalars().all()

async def get_dance_by_code(code: str) -> Optional[Dance]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Dance).where(Dance.code == code))
        return result.scalar_one_or_none()

async def load_dance_durations(robot_model_id: str) -> dict[str, float]:
    """Load dance durations (ms) từ bảng dance."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Dance.code, Dance.duration)
                                       .where(Dance.robot_model_id == robot_model_id))
        return {code: float(duration or 0) for code, duration in result.all()}