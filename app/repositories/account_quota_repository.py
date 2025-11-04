from aiocache import RedisCache
from sqlalchemy import select
from app.entities.account_quota import AccountQuota
from app.entities.databases.database_payment import AsyncSessionLocal
from aiocache import cached, RedisCache
from config.config import settings
from aiocache.serializers import JsonSerializer

@cached(ttl=60 * 10 * 6,
        cache=RedisCache,
        endpoint=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        key_builder=lambda f:  f"serial_acc_quota",
        serializer=JsonSerializer(),
)
async def get_account_quota(acc_id: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AccountQuota).where(AccountQuota.account_id == acc_id))
        return result.scalar_one_or_none()
    
@cached(ttl=60 * 10 * 6,
        cache=RedisCache,
        endpoint=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        key_builder=lambda f:  f"serial_to_acc",
        serializer=JsonSerializer(),
)
async def get_account_from_serial(serial: str):
