# services/quota_manager.py

import asyncio
from datetime import datetime
from config.config import settings
from sqlalchemy import select, update
from redis.asyncio import Redis

from app.entities.payment_service.account_quota import AccountQuota
from app.entities.payment_service.database_payment import AsyncSessionLocal as PaymentSession

# Initialize Redis globally (you can also inject via dependency)
redis_client = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True, password=settings.REDIS_PASSWORD)

from redis.exceptions import ConnectionError, TimeoutError

async def safe_redis_get(key: str, fallback_fn):
    try:
        value = await redis_client.get(key)
        if value is not None:
            return int(value)
    except (ConnectionError, TimeoutError):
        print(f"⚠️ Redis unavailable, falling back for key: {key}")
    return await fallback_fn()


# --- Core helper functions ---

async def consume_quota(acc_id: str, amount: int = 1) -> int:
    key = f"quota:{acc_id}"
    try:
        pipe = redis_client.pipeline()
        pipe.decrby(key, amount)
        pipe.get(key)
        _, new_quota = await pipe.execute()
        return int(new_quota)
    except (ConnectionError, TimeoutError):
        print(f"⚠️ Redis unavailable while consuming quota for {acc_id}")
        # fallback: update DB directly
        async with PaymentSession() as session:
            result = await session.execute(
                select(AccountQuota).where(AccountQuota.account_id == acc_id)
            )
            record = result.scalar_one_or_none()
            if not record:
                return 0
            new_value = max(record.quota - amount, 0)
            await session.execute(
                update(AccountQuota)
                .where(AccountQuota.account_id == acc_id)
                .values(quota=new_value)
            )
            await session.commit()
            return new_value



async def get_account_quota(acc_id: str):
    key = f"quota:{acc_id}"

    async def fallback_from_db():
        async with PaymentSession() as session:
            result = await session.execute(
                select(AccountQuota).where(AccountQuota.account_id == acc_id)
            )
            record = result.scalar_one_or_none()
            if not record:
                return 0
            return record.quota

    quota = await safe_redis_get(key, fallback_from_db)
    return {
        "account_id": acc_id,
        "quota": quota,
    }, "Quota"



async def preload_daily_quotas():
    """Load all quotas from DB into Redis (typically at 00:00)."""
    async with PaymentSession() as session:
        result = await session.execute(select(AccountQuota.account_id, AccountQuota.quota))
        rows = result.all()
        if not rows:
            return

        pipe = redis_client.pipeline()
        for acc_id, quota in rows:
            pipe.set(f"quota:{acc_id}", quota)
        await pipe.execute()
    print(f"[{datetime.utcnow().isoformat()}] Quotas preloaded into Redis.")


async def sync_redis_to_db():
    """Sync all live Redis quotas back to DB (optional hourly job)."""
    keys = await redis_client.keys("quota:*")
    if not keys:
        return

    async with PaymentSession() as session:
        for key in keys:
            acc_id = key.split(":")[1]
            quota_val = await redis_client.get(key)
            if quota_val is not None:
                await session.execute(
                    update(AccountQuota)
                    .where(AccountQuota.account_id == acc_id)
                    .values(quota=int(quota_val), last_updated=datetime.utcnow())
                )
        await session.commit()

    print(f"[{datetime.utcnow().isoformat()}] Redis quotas synced to DB.")
