# services/quota_manager.py

import asyncio
from datetime import datetime
from sqlalchemy import select, update
from redis.asyncio import Redis

from app.entities.payment_service.account_quota import AccountQuota
from app.entities.payment_service.database_payment import AsyncSession as PaymentSession

# Initialize Redis globally (you can also inject via dependency)
redis_client = Redis(host="localhost", port=6379, decode_responses=True)


# --- Core helper functions ---

async def consume_quota(acc_id: str, amount: int = 1) -> int:
    """Atomically decrease account quota in Redis and return the new value."""
    key = f"quota:{acc_id}"
    pipe = redis_client.pipeline()
    pipe.decrby(key, amount)
    pipe.get(key)
    _, new_quota = await pipe.execute()
    return int(new_quota)


async def get_account_quota(acc_id: str):
    """Return the account's current quota, either from Redis or DB."""
    key = f"quota:{acc_id}"
    quota = await redis_client.get(key)

    if quota is None:
        # Fallback to DB if not cached
        async with PaymentSession() as session:
            result = await session.execute(
                select(AccountQuota).where(AccountQuota.account_id == acc_id)
            )
            record = result.scalar_one_or_none()
            if not record:
                return None, "Quota"

            await redis_client.set(key, record.quota)
            return {
                "account_id": str(record.account_id),
                "quota": record.quota,
                "last_updated": record.last_updated.isoformat() if record.last_updated else None,
            }, "Quota"

    # Redis hit
    return {
        "account_id": acc_id,
        "quota": int(quota),
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
