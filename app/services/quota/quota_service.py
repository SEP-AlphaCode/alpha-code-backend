# services/quota_manager.py

import asyncio
from datetime import datetime

from app.entities.payment_service.token_rule import TokenRule
from config.config import settings
from sqlalchemy import select, update
from redis.asyncio import Redis

from app.entities.payment_service.account_quota import AccountQuota
from app.entities.payment_service.database_payment import AsyncSessionLocal as PaymentSession

# Initialize Redis globally (you can also inject via dependency)
redis_client = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True,
                     password=settings.REDIS_PASSWORD)

from redis.exceptions import ConnectionError


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
        print(f'⚠Reduce quota for {acc_id} by {amount}. New amount = {new_quota}')
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
            
            # Add the updated value to Redis for future use
            try:
                await redis_client.set(key, new_value)
                print(f"✅ Updated Redis cache for {acc_id} with new quota: {new_value}")
            except (ConnectionError, TimeoutError):
                print(f"⚠️ Redis still unavailable, skipping cache update for {acc_id}")
            
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
    """Load all trial quotas from token_rule into Redis (typically at 00:00)."""
    async with PaymentSession() as session:
        print('Load daily trial quota')
        # Get the active token_rule (status = 1) and use its cost as the trial amount
        result = await session.execute(
            select(TokenRule.cost).where(TokenRule.status == 1)
        )
        row = result.first()
        
        if not row:
            print("No active token rule found")
            return
        
        trial_amount = row[0]
        
        # Get all account IDs
        accounts_result = await session.execute(select(AccountQuota.account_id))
        accounts = accounts_result.all()
        
        if not accounts:
            return
        
        # Set trial amount for all accounts
        pipe = redis_client.pipeline()
        for (acc_id,) in accounts:
            pipe.set(f"quota:{acc_id}", trial_amount)
        await pipe.execute()
    
    print(f"[{datetime.utcnow().isoformat()}] Trial quotas preloaded into Redis")


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
