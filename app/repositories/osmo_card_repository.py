from sqlalchemy.future import select
from sqlalchemy import select as sync_select
from app.entities.database import AsyncSessionLocal
from app.entities.osmo_card import OsmoCard
from typing import List, Optional

async def get_all_osmo_cards() -> List[OsmoCard]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(OsmoCard).where(OsmoCard.status == 1))
        return result.scalars().all()

async def get_osmo_card_by_color(color: str) -> Optional[OsmoCard]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(OsmoCard).where(
            OsmoCard.color == color,
                        OsmoCard.status == 1)
                        )
        return result.scalar_one_or_none()
