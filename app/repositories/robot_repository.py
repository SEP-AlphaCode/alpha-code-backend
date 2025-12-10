from sqlalchemy.future import select
from app.entities.robot_service.robot import Robot
from app.entities.robot_service.database_robot import AsyncSessionLocal
from typing import Optional
import logging

logger = logging.getLogger(__name__)


async def get_robot_by_serial(serial_number: str) -> Optional[Robot]:
    """
    Get Robot entity by serial number

    Args:
        serial_number: Robot serial number

    Returns:
        Robot entity if found and active, None otherwise
    """
    async with AsyncSessionLocal() as db:
        try:
            query = select(Robot).where(
                Robot.serial_number == serial_number,
                Robot.status == 1
            )
            result = await db.execute(query)
            robot = result.scalar_one_or_none()

            if robot:
                logger.info(f"Found robot {robot.id} with serial {serial_number}, account_id: {robot.account_id}")
            else:
                logger.warning(f"No active robot found with serial {serial_number}")

            return robot

        except Exception as e:
            logger.error(f"Error getting robot by serial {serial_number}: {e}")
            return None

