from sqlalchemy.future import select
from app.entities.robot_model import RobotModel
from app.entities.database_robot import AsyncSessionLocal
from typing import List, Optional

async def get_robot_prompt_by_id(robot_model_id: str) -> Optional[str]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(RobotModel.robot_prompt).where(RobotModel.id == robot_model_id)
        )
        row = result.first()
        return row[0] if row else None