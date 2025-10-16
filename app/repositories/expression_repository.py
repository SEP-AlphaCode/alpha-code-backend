# app/db/repos/expression_repo.py
from sqlalchemy.future import select
from typing import List, Optional
from app.entities.database import AsyncSessionLocal
from app.entities.expression import Expression
from aiocache import cached, Cache, RedisCache

@cached(ttl=60 * 10, cache=RedisCache, key_builder=lambda f:  f"expressions_list")
async def get_all_expressions() -> List[Expression]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Expression))
        return result.scalars().all()

@cached(ttl=60 * 10, cache=RedisCache, key_builder=lambda f, code: f"expression:{code}")
async def get_expression_by_code(code: str) -> Optional[Expression]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Expression).where(Expression.code == code))
        return result.scalar_one_or_none()

@cached(ttl=60 * 10, cache=RedisCache, key_builder=lambda f, robot_model_id: f"expression:{robot_model_id}")
async def load_expression_durations(robot_model_id: str) -> dict[str, int]:
    """Load expression durations (ms) từ bảng expression (nếu có)."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Expression.code)
                                       .where(Expression.robot_model_id == robot_model_id))
        # Nếu expression không có duration -> có thể đặt mặc định 3000ms
        return {code: 3000 for code, in result.all()}