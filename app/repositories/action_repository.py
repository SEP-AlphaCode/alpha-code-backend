# app/db/repos/action_repo.py
from sqlalchemy.future import select
from typing import List, Optional
from app.entities.database import AsyncSessionLocal
from app.entities.action import Action
from aiocache import cached, Cache, RedisCache

@cached(ttl=60 * 10, cache=RedisCache, key_builder=lambda f:  f"actions_list")
async def get_all_actions() -> List[Action]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Action))
        return result.scalars().all()
    
@cached(ttl=60 * 10, cache=RedisCache, key_builder=lambda f, code: f"action:{code}")
async def get_action_by_code(code: str) -> Optional[Action]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Action).where(Action.code == code))
        return result.scalar_one_or_none()

@cached(ttl=60 * 10, cache=RedisCache, key_builder=lambda f, robot_model_id: f"action:{robot_model_id}")
async def load_action_durations(robot_model_id: str) -> dict[str, int]:
    """Load action durations (ms) từ bảng action."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Action.code, Action.duration)
                                       .where(Action.robot_model_id == robot_model_id))
        return {code: int(duration or 0) for code, duration in result.all()}