# app/db/repos/action_repo.py
from sqlalchemy.future import select
from typing import List, Optional
from app.entities.database import AsyncSessionLocal
from app.entities.action import Action

async def get_all_actions() -> List[Action]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Action))
        return result.scalars().all()

async def get_action_by_code(code: str) -> Optional[Action]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Action).where(Action.code == code))
        return result.scalar_one_or_none()
