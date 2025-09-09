# app/db/repos/expression_repo.py
from sqlalchemy.future import select
from typing import List, Optional
from app.entities.database import AsyncSessionLocal
from app.entities.expression import Expression

async def get_all_expressions() -> List[Expression]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Expression))
        return result.scalars().all()

async def get_expression_by_code(code: str) -> Optional[Expression]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Expression).where(Expression.code == code))
        return result.scalar_one_or_none()
