# services/quota_manager.py

import asyncio
from datetime import datetime

from app.entities.payment_service.token_rule import TokenRule
from config.config import settings
from sqlalchemy import select, update
from redis.asyncio import Redis

from app.entities.payment_service.account_quota import AccountQuota
from app.entities.payment_service.database_payment import AsyncSessionLocal as PaymentSession
from aiocache import Cache
from aiocache.serializers import StringSerializer
from aiocache.backends.redis import RedisBackend
from datetime import datetime
from sqlalchemy import select, update

from aiocache import Cache
from aiocache.serializers import StringSerializer
from aiocache.backends.redis import RedisBackend
from datetime import datetime
from sqlalchemy import select, update

# Initialize aiocache Redis client
redis_client = Cache(
    Cache.REDIS,
    endpoint=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    serializer=StringSerializer(),
    namespace=""  # No namespace prefix
)


async def safe_redis_get(key: str, fallback_fn):
    """Safely get a value from Redis with fallback to DB."""
    try:
        value = await redis_client.get(key)
        if value is not None:
            return int(value)
    except Exception as e:
        print(f"⚠️ Redis unavailable, falling back for key: {key} - {e}")
    return await fallback_fn()


async def consume_quota(acc_id: str, amount: int = 1) -> int:
    """Consume quota for an account, with DB fallback if Redis fails."""
    key = f"quota:{acc_id}"
    try:
        # aiocache doesn't have native pipeline support, so we do operations sequentially
        current = await redis_client.get(key)
        if current is None:
            # Key doesn't exist, fallback to DB
            raise Exception("Key not found in Redis")
        
        new_quota = max(int(current) - amount, 0)
        await redis_client.set(key, str(new_quota))
        print(f'⚠️ Reduced quota for {acc_id} by {amount}. New amount = {new_quota}')
        return new_quota
    except Exception as e:
        print(f"⚠️ Redis unavailable while consuming quota for {acc_id}: {e}")
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
                await redis_client.set(key, str(new_value))
                print(f"✅ Updated Redis cache for {acc_id} with new quota: {new_value}")
            except Exception as cache_error:
                print(f"⚠️ Redis still unavailable, skipping cache update for {acc_id}: {cache_error}")
            
            return new_value


async def get_account_quota(acc_id: str):
    """Get quota for an account from Redis, with DB fallback."""
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
        
        # Set trial amount for all accounts (aiocache doesn't have pipeline, so we do it sequentially)
        for (acc_id,) in accounts:
            try:
                await redis_client.set(f"quota:{acc_id}", str(trial_amount))
            except Exception as e:
                print(f"⚠️ Failed to set quota for {acc_id}: {e}")
    
    print(f"[{datetime.utcnow().isoformat()}] Trial quotas preloaded into Redis")


async def sync_redis_to_db():
    """Sync all live Redis quotas back to DB (optional hourly job)."""
    try:
        # Get the underlying redis client from aiocache
        # aiocache stores the client in the 'client' attribute after initialization
        if not hasattr(redis_client, 'client') or redis_client.client is None:
            # Initialize connection if not already done
            await redis_client.get("_init_test")
        
        if hasattr(redis_client, 'client') and redis_client.client:
            keys = await redis_client.client.keys("quota:*")
        else:
            print("⚠️ Cannot access Redis keys for sync, using alternative method")
            await sync_redis_to_db_alternative()
            return
        
        if not keys:
            return
        
        async with PaymentSession() as session:
            for key in keys:
                # Decode key if it's bytes
                if isinstance(key, bytes):
                    key = key.decode('utf-8')
                
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
    except Exception as e:
        print(f"⚠️ Failed to sync Redis to DB: {e}, using alternative method")
        await sync_redis_to_db_alternative()


# Alternative sync method if direct access to keys doesn't work
async def sync_redis_to_db_alternative():
    """Alternative sync method using DB as the source of truth for account IDs."""
    async with PaymentSession() as session:
        # Get all account IDs from DB
        accounts_result = await session.execute(select(AccountQuota.account_id))
        accounts = accounts_result.all()
        
        for (acc_id,) in accounts:
            try:
                quota_val = await redis_client.get(f"quota:{acc_id}")
                if quota_val is not None:
                    await session.execute(
                        update(AccountQuota)
                        .where(AccountQuota.account_id == acc_id)
                        .values(quota=int(quota_val), last_updated=datetime.utcnow())
                    )
            except Exception as e:
                print(f"⚠️ Failed to sync quota for {acc_id}: {e}")
        
        await session.commit()
    
    print(f"[{datetime.utcnow().isoformat()}] Redis quotas synced to DB (alternative method).")