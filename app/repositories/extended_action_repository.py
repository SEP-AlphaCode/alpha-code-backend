from sqlalchemy.future import select
from typing import List, Optional
from app.entities.database import AsyncSessionLocal
from app.entities.extended_action import ExtendedAction
from aiocache import cached, Cache, RedisCache
from config.config import settings
from aiocache.serializers import JsonSerializer

@cached(ttl=60 * 10,
        cache=RedisCache,
        endpoint=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        key_builder=lambda f:  f"extended_actions_list",
        serializer=JsonSerializer(),
)
async def get_all_extended_actions() -> List[ExtendedAction]:
    """Lấy toàn bộ extended actions"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ExtendedAction))
        return result.scalars().all()

@cached(ttl=60 * 10,
        cache=RedisCache,
        endpoint=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        key_builder=lambda f, code: f"extended_action:{code}",
        serializer=JsonSerializer(),
)
async def get_extended_action_by_code(code: str) -> Optional[ExtendedAction]:
    """Lấy extended action theo code"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ExtendedAction).where(ExtendedAction.code == code))
        return result.scalar_one_or_none()

async def create_extended_action(data: ExtendedAction) -> ExtendedAction:
    """Thêm mới extended action"""
    async with AsyncSessionLocal() as session:
        session.add(data)
        await session.commit()
        await session.refresh(data)
        return data

async def delete_extended_action_by_id(id: str) -> bool:
    """Xóa extended action theo id"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ExtendedAction).where(ExtendedAction.id == id))
        extended_action = result.scalar_one_or_none()
        if extended_action:
            await session.delete(extended_action)
            await session.commit()
            return True
        return False
