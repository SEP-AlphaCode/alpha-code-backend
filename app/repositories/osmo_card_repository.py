from sqlalchemy import select, and_, func
from app.entities.activity_service.database import AsyncSessionLocal
from app.entities.activity_service.osmo_card import OsmoCard
from typing import List, Optional
from aiocache import cached, RedisCache
from config.config import settings
from aiocache.serializers import JsonSerializer

@cached(ttl=60 * 10 * 3,
        cache=RedisCache,
        endpoint=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        key_builder=lambda f:  f"osmo_cards_list",
        serializer=JsonSerializer(),
)
@cached(ttl=60 * 10 * 3, cache=RedisCache, key_builder=lambda f:  f"osmo_cards_list")
async def get_all_osmo_cards() -> List[OsmoCard]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(OsmoCard).where(OsmoCard.status == 1))
        return result.scalars().all()

@cached(ttl=60 * 10 * 3,
        cache=RedisCache,
        endpoint=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        key_builder=lambda f, color: f"osmo_card:{color}",
        serializer=JsonSerializer(),
)
async def get_osmo_card_by_color(color: str) -> Optional[OsmoCard]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(OsmoCard).where(
                and_(
                    func.lower(OsmoCard.color) == color.lower(),
                    OsmoCard.status == 1
                )
            )
        )
        osmo_card = result.scalar_one_or_none()

        # Nếu có FK, load relationship thủ công
        if osmo_card:
            if osmo_card.action_id:
                await session.refresh(osmo_card, attribute_names=["action"])
            if osmo_card.dance_id:
                await session.refresh(osmo_card, attribute_names=["dance"])
            if osmo_card.expression_id:
                await session.refresh(osmo_card, attribute_names=["expression"])
            if osmo_card.skill_id:
                await session.refresh(osmo_card, attribute_names=["skill"])
            if osmo_card.extended_action_id:
                await session.refresh(osmo_card, attribute_names=["extended_action"])

        return osmo_card

