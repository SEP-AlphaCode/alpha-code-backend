from aiocache import RedisCache
from sqlalchemy import select, func
from app.entities.account_quota import AccountQuota
from app.entities.databases.database_payment import AsyncSessionLocal as PaymentSession
from app.entities.databases.database_robot import AsyncSessionLocal as RobotSession
from aiocache import cached, RedisCache

from app.entities.robot import Robot
from app.entities.subscription import Subscription
from config.config import settings
from aiocache.serializers import JsonSerializer

@cached(ttl=60 * 10 * 6,
        cache=RedisCache,
        endpoint=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        key_builder=lambda f, *args, **kwargs: f"acc_quota:{args[0]}",
        serializer=JsonSerializer(),
)
async def get_account_quota(acc_id: str):
    async with PaymentSession() as session:
        #find in subscription first
        subscriptions = await session.execute(
            select(Subscription)
            .where(Subscription.account_id == acc_id,
                   Subscription.end_date > func.now()))
        sub = subscriptions.scalar_one_or_none()
        if sub is not None:
            return sub, 'Subscription'
        quotas = await session.execute(select(AccountQuota).where(AccountQuota.account_id == acc_id))
        return quotas.scalar_one_or_none(), 'Quota'
    
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