# services/quota_manager.py

import asyncio
from datetime import datetime
from typing import Optional

from app.entities.payment_service.token_rule import TokenRule
from config.config import settings
from sqlalchemy import select, update
from app.entities.payment_service.account_quota import AccountQuota
from app.entities.payment_service.database_payment import AsyncSessionLocal as PaymentSession

# We must avoid importing aiocache (and transitively redis) at module import time
# because in some deployment images an incompatible `redis` package may be
# present and cause a SyntaxError during import. Use lazy initialization and a
# safe in-memory fallback cache.

_cache_client = None
_cache_import_error = None


class InMemoryCache:
    """A very small asyncio-friendly in-memory cache used as a safe fallback.

    It implements async get/set/keys and mimics the minimal interface the
    quota service expects. This is NOT a replacement for Redis in production,
    but allows the service to start and operate degraded if Redis or aiocache
    cannot be imported.
    """

    def __init__(self):
        self._store: dict[str, tuple[str, Optional[float]]] = {}
        self.client = None

    async def get(self, key: str):
        entry = self._store.get(key)
        if not entry:
            return None
        value, expires_at = entry
        if expires_at is None or expires_at > datetime.utcnow().timestamp():
            return value
        # expired
        del self._store[key]
        return None

    async def set(self, key: str, value: str, ttl: Optional[int] = None):
        expires_at = None
        if ttl and ttl > 0:
            expires_at = datetime.utcnow().timestamp() + ttl
        self._store[key] = (value, expires_at)

    async def keys(self, pattern: str):
        # naive glob '*' support
        if pattern == "*":
            return list(self._store.keys())
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return [k for k in self._store.keys() if k.startswith(prefix)]
        return [k for k in self._store.keys() if k == pattern]


def init_cache():
    """Initialize aiocache Cache client if available, otherwise fallback."""
    global _cache_client, _cache_import_error
    if _cache_client is not None or _cache_import_error is not None:
        return _cache_client

    try:
        # import here to avoid import-time failures
        from aiocache import Cache
        from aiocache.serializers import StringSerializer

        client = Cache(
            Cache.REDIS,
            endpoint=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            serializer=StringSerializer(),
            namespace="",
        )
        _cache_client = client
        return _cache_client
    except Exception as e:
        _cache_import_error = e
        # fallback to in-memory cache
        _cache_client = InMemoryCache()
        print(f"⚠️ aiocache/redis import failed, using in-memory cache fallback: {e}")
        return _cache_client


def get_cache():
    return init_cache()


# Low-level redis client (attempt to reuse aiocache's underlying client or
# create a redis.asyncio.Redis instance when available). This is used for
# atomic operations (decrby, pipeline, keys) so quota updates behave like a
# real Redis-backed cache (matching other repo modules).
_redis_lowlevel = None


def init_redis_lowlevel():
    global _redis_lowlevel
    if _redis_lowlevel is not None:
        return _redis_lowlevel

    # Prefer underlying client from aiocache if present
    client = get_cache()
    try:
        if client is not None and hasattr(client, 'client') and getattr(client, 'client'):
            _redis_lowlevel = getattr(client, 'client')
            return _redis_lowlevel
    except Exception:
        pass

    # Otherwise try to import redis.asyncio directly (safe-guarded)
    try:
        from redis.asyncio import Redis as AsyncRedis

        rc = AsyncRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, password=settings.REDIS_PASSWORD, decode_responses=True)
        _redis_lowlevel = rc
        return _redis_lowlevel
    except Exception as e:
        # Could not initialize low-level redis client (e.g., incompatible package)
        print(f"⚠️ Low-level redis client not available: {e}")
        _redis_lowlevel = None
        return None


def get_redis_lowlevel():
    return init_redis_lowlevel()


async def safe_redis_get(key: str, fallback_fn):
    """Safely get a value from Redis with fallback to DB."""
    client = get_cache()
    if client is None:
        return await fallback_fn()
    try:
        value = await client.get(key)
        if value is not None:
            return int(value)
    except Exception as e:
        print(f"⚠️ Redis/unified cache unavailable, falling back for key: {key} - {e}")
    return await fallback_fn()


async def consume_quota(acc_id: str, amount: int = 1) -> int:
    """Consume quota for an account, with DB fallback if Redis fails."""
    key = f"quota:{acc_id}"
    # Try to use a low-level redis client for atomic decrement if available
    rc = get_redis_lowlevel()
    if rc is not None:
        try:
            # Prefer decrby if supported
            if hasattr(rc, 'decrby'):
                new_val = await rc.decrby(key, amount)
                print(f'⚠️ Reduced quota for {acc_id} by {amount}. New amount = {new_val}')
                return int(new_val)
            else:
                # fall back to pipeline of decr and get
                pipe = rc.pipeline()
                pipe.decrby(key, amount)
                pipe.get(key)
                res = await pipe.execute()
                # res[1] should be the new value as string
                new_val = res[1]
                return int(new_val)
        except Exception as e:
            print(f"⚠️ Low-level Redis error while consuming quota for {acc_id}: {e}")

    # If low-level client not available, use generic cache client (aiocache or in-memory)
    client = get_cache()
    if client is not None:
        try:
            current = await client.get(key)
            if current is None:
                # Key doesn't exist, fallback to DB
                raise Exception("Key not found in cache")

            new_quota = max(int(current) - amount, 0)
            await client.set(key, str(new_quota))
            print(f'⚠️ Reduced quota for {acc_id} by {amount}. New amount = {new_quota}')
            return new_quota
        except Exception as e:
            print(f"⚠️ Cache unavailable while consuming quota for {acc_id}: {e}")
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
                client = get_cache()
                if client is not None:
                    await client.set(key, str(new_value))
                    print(f"✅ Updated cache for {acc_id} with new quota: {new_value}")
                else:
                    print(f"⚠️ Cache client not available, skipping cache update for {acc_id}")
            except Exception as cache_error:
                print(f"⚠️ Cache still unavailable, skipping cache update for {acc_id}: {cache_error}")
            
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
        
        # Set trial amount for all accounts (cache may be Redis-backed or in-memory)
        client = get_cache()
        if client is None:
            print("⚠️ Cache client not available; skipping preload to cache")
            return
        for (acc_id,) in accounts:
            try:
                await client.set(f"quota:{acc_id}", str(trial_amount))
            except Exception as e:
                print(f"⚠️ Failed to set quota for {acc_id}: {e}")
    
    print(f"[{datetime.utcnow().isoformat()}] Trial quotas preloaded into Redis")


async def sync_redis_to_db():
    """Sync all live Redis quotas back to DB (optional hourly job)."""
    try:
        client = get_cache()
        # If the underlying client exposes a .client with direct redis access use it for keys
        keys = None
        if client is None:
            print("⚠️ Cache client not available; skipping sync")
            return
        if hasattr(client, 'client') and getattr(client, 'client'):
            try:
                keys = await client.client.keys("quota:*")
            except Exception:
                keys = None

        if keys is None:
            # Fall back to cache.keys (in-memory fallback supports this)
            try:
                keys = await client.keys("quota:*")
            except Exception:
                keys = None

        if not keys:
            await sync_redis_to_db_alternative()
            return

        async with PaymentSession() as session:
            for key in keys:
                # Decode key if it's bytes
                if isinstance(key, bytes):
                    key = key.decode('utf-8')

                acc_id = key.split(":")[1]
                quota_val = await client.get(key)
                if quota_val is not None:
                    await session.execute(
                        update(AccountQuota)
                        .where(AccountQuota.account_id == acc_id)
                        .values(quota=int(quota_val), last_updated=datetime.utcnow())
                    )
            await session.commit()

        print(f"[{datetime.utcnow().isoformat()}] Cache quotas synced to DB.")
    except Exception as e:
        print(f"⚠️ Failed to sync cache to DB: {e}, using alternative method")
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
                client = get_cache()
                if client is None:
                    continue
                quota_val = await client.get(f"quota:{acc_id}")
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