# services/quota_manager.py

import asyncio
import traceback
from datetime import datetime
from typing import Optional
import json
from app.entities.payment_service.subscription import Subscription
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
    
    async def set(self, key: str, value: str, ttl: Optional[int] = 30 * 60):
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
        
        rc = AsyncRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, password=settings.REDIS_PASSWORD,
                        decode_responses=True)
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
            # Deserialize JSON dict
            return json.loads(value)
    except Exception as e:
        print(f"⚠️ Redis/unified cache unavailable, falling back for key: {key} - {e}")
    return await fallback_fn()


async def consume_quota(acc_id: str, amount: int = 1) -> int:
    """Consume quota for an account, with DB fallback if Redis fails."""
    key = f"quota::{acc_id}"
    rc = get_redis_lowlevel()
    client = get_cache()

    if rc is not None:
        try:
            # low-level redis: handle as before
            new_val = await rc.decrby(key, amount)
            return int(new_val)
        except Exception as e:
            print(f"⚠️ Low-level Redis error while consuming quota:: {e}")

    # Generic cache (aiocache / in-memory)
    if client is not None:
        try:
            val_dict = await client.get(key)
            if val_dict is None:
                raise Exception("Key not found in cache")

            if isinstance(val_dict, str):
                val_dict = json.loads(val_dict)

            current_quota = val_dict.get('quota', 0)
            new_quota = max(current_quota - amount, 0)
            val_dict['quota'] = new_quota

            # Save back to cache
            await client.set(key, json.dumps(val_dict))
            return new_quota
        except Exception as e:
            print(f"⚠️ Cache unavailable while consuming quota for {acc_id}: {e}")

    # Fallback DB update
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
        # Update cache
        if client is not None:
            await client.set(key, json.dumps({'acc_id': acc_id, 'quota': new_value, 'type': 'Quota'}))
        return new_value


async def get_account_quota(acc_id: str):
    """Get quota for an account from Redis, with DB fallback."""
    key = f"quota::{acc_id}"
    client = get_cache()
    async def fallback_from_db():
        async with PaymentSession() as session:
            now = datetime.utcnow()
            
            # 1. Try to find an active subscription first
            sub_query = (
                select(Subscription)
                .where(
                    Subscription.account_id == acc_id,
                    Subscription.status == 1,
                    Subscription.end_date > now,
                )
                .limit(1)
            )
            sub_result = await session.execute(sub_query)
            subscription = sub_result.scalar_one_or_none()
            
            if subscription:
                res = {'acc_id': acc_id, 'quota': 0, 'type': "Subscription"}
                try:
                    await client.set(key, json.dumps(res), 30 * 60)
                except:
                    pass
                return res
            
            # 2. Nếu không có subscription → fallback sang AccountQuota
            acc_query = select(AccountQuota).where(AccountQuota.account_id == acc_id)
            acc_result = await session.execute(acc_query)
            record = acc_result.scalar_one_or_none()
            res = {'acc_id': acc_id, 'quota': record.quota if record else 0, 'type': "Quota"}
            try:
                await client.set(key, json.dumps(res), 30 * 60)
            except:
                pass
            return res
    
    result = await safe_redis_get(key, fallback_from_db)
    
    return result


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
                val_dict = {'acc_id': acc_id, 'quota': trial_amount, 'type': 'Quota'}
                await client.set(f"quota::{acc_id}", json.dumps(val_dict), 30 * 60)
            except Exception as e:
                print(f"⚠️ Failed to set quota for {acc_id}: {e}")
    
    print(f"[{datetime.utcnow().isoformat()}] Trial quotas preloaded into Redis")


async def sync_redis_to_db():
    """Sync all live Redis quotas back to DB (runs every 5 minutes)."""
    try:
        client = get_cache()
        if client is None:
            print("⚠️ Cache client not available; skipping sync")
            return
        
        # Get Redis keys
        keys = None
        if hasattr(client, 'client') and getattr(client, 'client'):
            try:
                keys = await client.client.keys("quota::*")
            except Exception:
                keys = None
        
        if keys is None:
            try:
                keys = await client.keys("quota::*")
            except Exception:
                print("⚠️ Failed to fetch keys from cache; skipping sync")
                return
        
        if not keys:
            print("No quota keys found in cache")
            return
        
        async with PaymentSession() as session:
            updates = []
            
            for key in keys:
                try:
                    # Decode key if it's bytes
                    if isinstance(key, bytes):
                        key = key.decode('utf-8')
                    
                    acc_id = key.split("::")[1]
                    quota_val = await client.get(key)
                    
                    if isinstance(quota_val, str):
                        quota_val = json.loads(quota_val)
                    
                    # Only sync type "Quota"
                    if quota_val.get('type') != 'Quota':
                        continue
                    
                    quota_int = int(quota_val.get('quota', 0))
                    updates.append({
                        'account_id': acc_id,
                        'quota': quota_int,
                        'last_updated': datetime.utcnow()
                    })
                except Exception as e:
                    print(f"⚠️ Failed to process key {key}: {e}")
            
            if updates:
                await session.execute(update(AccountQuota), updates)
                await session.commit()
                print(f"[{datetime.utcnow().isoformat()}] Synced {len(updates)} quotas to DB.")
            else:
                print(f"[{datetime.utcnow().isoformat()}] No Quota-type entries to sync.")
    
    except Exception as e:
        traceback.print_exc()
        print(f"⚠️ Failed to sync cache to DB: {e}")
        # Just log and move on - will retry in 5 minutes