from sqlalchemy import select, func

from app.entities.model_to_json import subscription_to_dict, robot_to_dict, account_quota_to_dict
from app.entities.payment_service.account_quota import AccountQuota
from app.entities.payment_service.database_payment import AsyncSessionLocal as PaymentSession
from app.entities.robot_service.database_robot import AsyncSessionLocal as RobotSession
from aiocache import cached, RedisCache

from app.entities.robot_service.robot import Robot
from app.entities.payment_service.subscription import Subscription
from config.config import settings
from aiocache.serializers import JsonSerializer

@cached(ttl=60 * 10 * 6,
        cache=RedisCache,
        endpoint=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        key_builder=lambda f, *args, **kwargs: f"serial_to_acc:{args[0]}",
        serializer=JsonSerializer(),
)
async def get_account_from_serial(serial: str):
    async with RobotSession() as session:
        result = await session.execute(select(Robot.account_id).where(Robot.serial_number == serial))
        return result.scalar_one_or_none()