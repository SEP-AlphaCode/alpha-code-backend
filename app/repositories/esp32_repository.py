from typing import Optional
from aiocache import cached, RedisCache
from sqlalchemy.future import select

from app.entities.model_to_json import esp32_to_dict
from app.entities.robot_service.esp32 import ESP32
from config.config import settings
from aiocache.serializers import JsonSerializer
from app.entities.robot_service.database_robot import AsyncSessionLocal

@cached(ttl=60 * 10 * 3,
        cache=RedisCache,
        endpoint=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        key_builder=lambda f, account_id:  f"esp32:{account_id}",
        serializer=JsonSerializer(),
)
async def get_esp(account_id: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ESP32).where(
            ESP32.account_id == account_id,
            ESP32.status == 1
        ))
        return esp32_to_dict(result.scalar_one_or_none())