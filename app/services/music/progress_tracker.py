"""
Progress tracking service for long-running music generation tasks
"""
import uuid
import json
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import redis.asyncio as redis
from config.config import settings


class ProgressTracker:
    """Track progress of music generation tasks using Redis"""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.ttl = 3600  # Task info expires after 1 hour

    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection"""
        if self.redis_client is None:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                decode_responses=True
            )
        return self.redis_client

    def _task_key(self, task_id: str) -> str:
        """Generate Redis key for task"""
        return f"music_gen:task:{task_id}"

    async def create_task(self, task_id: Optional[str] = None) -> str:
        """Create a new task and return task_id"""
        if task_id is None:
            task_id = str(uuid.uuid4())

        redis_client = await self._get_redis()
        key = self._task_key(task_id)

        task_data = {
            "task_id": task_id,
            "status": "pending",
            "progress": 0,
            "stage": "initializing",
            "message": "Task created",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        await redis_client.setex(
            key,
            self.ttl,
            json.dumps(task_data)
        )

        return task_id

    async def update_progress(
        self,
        task_id: str,
        progress: int,
        stage: str,
        message: str = "",
        status: str = "processing"
    ):
        """Update task progress (0-100)"""
        redis_client = await self._get_redis()
        key = self._task_key(task_id)

        # Get existing data
        existing = await redis_client.get(key)
        if not existing:
            return

        task_data = json.loads(existing)
        task_data.update({
            "status": status,
            "progress": max(0, min(100, progress)),  # Clamp 0-100
            "stage": stage,
            "message": message,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

        await redis_client.setex(
            key,
            self.ttl,
            json.dumps(task_data)
        )

    async def complete_task(self, task_id: str, result: Any):
        """Mark task as completed with result"""
        redis_client = await self._get_redis()
        key = self._task_key(task_id)

        task_data = {
            "task_id": task_id,
            "status": "completed",
            "progress": 100,
            "stage": "completed",
            "message": "Task completed successfully",
            "result": result,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Extend TTL for completed tasks
        await redis_client.setex(
            key,
            self.ttl * 2,  # Keep completed tasks longer
            json.dumps(task_data)
        )

    async def fail_task(self, task_id: str, error: str):
        """Mark task as failed with error"""
        redis_client = await self._get_redis()
        key = self._task_key(task_id)

        task_data = {
            "task_id": task_id,
            "status": "failed",
            "progress": 0,
            "stage": "failed",
            "message": "Task failed",
            "error": error,
            "failed_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        await redis_client.setex(
            key,
            self.ttl,
            json.dumps(task_data)
        )

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get current task status"""
        redis_client = await self._get_redis()
        key = self._task_key(task_id)

        data = await redis_client.get(key)
        if not data:
            return None

        return json.loads(data)

    async def delete_task(self, task_id: str):
        """Delete task from Redis"""
        redis_client = await self._get_redis()
        key = self._task_key(task_id)
        await redis_client.delete(key)

    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()


# Global instance
progress_tracker = ProgressTracker()

