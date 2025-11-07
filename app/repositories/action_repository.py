# app/db/repos/action_repo.py
from sqlalchemy.future import select
from typing import List, Optional
from app.entities.activity_service.database import AsyncSessionLocal
from app.entities.activity_service.action import Action
from aiocache import cached, RedisCache
from config.config import settings
from aiocache.serializers import JsonSerializer

@cached(ttl=60 * 10 * 3,
        cache=RedisCache,
        endpoint=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        key_builder=lambda f:  f"actions_list",
        serializer=JsonSerializer(),
)
async def get_all_actions() -> List[Action]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Action))
        return result.scalars().all()
    
@cached(ttl=60 * 10 * 3,
        cache=RedisCache,
        endpoint=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        key_builder=lambda f, code: f"action:{code}",
        serializer=JsonSerializer(),
)
async def get_action_by_code(code: str) -> Optional[Action]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Action).where(Action.code == code))
        return result.scalar_one_or_none()

@cached(ttl=60 * 10 * 3,
        cache=RedisCache,
        endpoint=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        key_builder=lambda f, robot_model_id: f"action:{robot_model_id}",
        serializer=JsonSerializer(),
)
async def load_action_durations(robot_model_id: str) -> dict[str, int]:
    """Load action durations (ms) từ bảng action."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Action.code, Action.duration)
                                       .where(Action.robot_model_id == robot_model_id))
        return {code: int(duration or 0) for code, duration in result.all()}