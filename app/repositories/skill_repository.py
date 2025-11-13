from sqlalchemy.future import select
from typing import List, Optional
from app.entities.activity_service.database import AsyncSessionLocal
from app.entities.activity_service.skill import Skill
from aiocache import cached, RedisCache

from app.entities.model_to_json import skill_to_dict
from config.config import settings
from aiocache.serializers import JsonSerializer

@cached(ttl=60 * 10 * 3,
        cache=RedisCache,
        endpoint=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        key_builder=lambda f: f"skills_list",
        serializer=JsonSerializer(),
)
async def get_all_skills() -> List[Skill]:
    """Lấy toàn bộ skills"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Skill))
        return result.scalars().all()

@cached(ttl=60 * 10 * 3,
        cache=RedisCache,
        endpoint=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        key_builder=lambda f, code: f"skill:{code}",
        serializer=JsonSerializer(),
)
async def get_skill_by_code(code: str) -> Optional[Skill]:
    """Lấy skill theo code"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Skill).where(Skill.code == code))
        return result.scalar_one_or_none()

async def create_skill(data: Skill) -> Skill:
    """Thêm mới skill"""
    async with AsyncSessionLocal() as session:
        session.add(data)
        await session.commit()
        await session.refresh(data)
        return data

async def delete_skill_by_id(id: str) -> bool:
    """Xóa skill theo id"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Skill).where(Skill.id == id))
        skill = result.scalar_one_or_none()
        if skill:
            await session.delete(skill)
            await session.commit()
            return True
        return False

@cached(ttl=60 * 10 * 3,
        cache=RedisCache,
        endpoint=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        key_builder=lambda f, robot_model_id: f"skill:{robot_model_id}",
        serializer=JsonSerializer(),
)
async def get_skills_by_robot_model_repo(robot_model_id: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Skill).where(Skill.robot_model_id == robot_model_id)
        )
        return [skill_to_dict(skill) for skill in result.scalars().all()]
