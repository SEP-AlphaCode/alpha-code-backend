from sqlalchemy.future import select
from typing import List, Optional
from app.entities.database import AsyncSessionLocal
from app.entities.skill import Skill
from aiocache import cached

async def get_all_skills() -> List[Skill]:
    """Lấy toàn bộ skills"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Skill))
        return result.scalars().all()

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


@cached(ttl=60 * 10, key_builder=lambda f, robot_model_id: f"skill:{robot_model_id}")
async def get_skills_by_robot_model_repo(robot_model_id: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Skill).where(Skill.robot_model_id == robot_model_id)
        )
        return result.scalars().all()
