from sqlalchemy.future import select
from app.entities.robot_model import RobotModel
from app.entities.database_robot import AsyncSessionLocal
from typing import List, Optional
from aiocache import cached, Cache, RedisCache


@cached(ttl=60 * 10, cache=RedisCache, key_builder=lambda f, robot_model_id: f"robot_model:{robot_model_id}")
# @cached(
#     ttl=60,
#     cache=RedisCache,
#     endpoint="localhost",
#     port=6379,
#     key_builder=lambda f, robot_model_id: f"robot_prompt:{robot_model_id}",
#     serializer=JsonSerializer(),
# )
async def get_robot_prompt_by_id(robot_model_id: str) -> Optional[str]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(RobotModel.robot_prompt).where(RobotModel.id == robot_model_id)
        )
        row = result.first()
        return row[0] if row else None