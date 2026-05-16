"""Redis cache service."""
import json
from typing import Optional, Any
import redis.asyncio as redis

from app.config import settings
from app.logging_config import log
from app.exceptions import CacheException


class CacheService:
    """Redis-based caching service."""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self._connected = False

    async def connect(self):
        """Connect to Redis."""
        try:
            self.redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password or None,
                decode_responses=True
            )
            await self.redis_client.ping()
            self._connected = True
            log.info("Redis cache connected")
        except Exception as e:
            log.error(f"Redis connection failed: {e}")
            self._connected = False

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
            self._connected = False
            log.info("Redis cache disconnected")

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        if not self._connected:
            return None

        try:
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            log.error(f"Cache get error: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set a value in cache."""
        if not self._connected:
            return False

        try:
            ttl = ttl or settings.redis_cache_ttl
            serialized = json.dumps(value)
            await self.redis_client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            log.error(f"Cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        if not self._connected:
            return False

        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            log.error(f"Cache delete error: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self._connected:
            return False

        try:
            return await self.redis_client.exists(key) > 0
        except Exception as e:
            log.error(f"Cache exists error: {e}")
            return False

    async def get_pattern(self, pattern: str) -> list:
        """Get all keys matching a pattern."""
        if not self._connected:
            return []

        try:
            keys = await self.redis_client.keys(pattern)
            return keys
        except Exception as e:
            log.error(f"Cache pattern error: {e}")
            return []

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a counter."""
        if not self._connected:
            return 0

        try:
            return await self.redis_client.incrby(key, amount)
        except Exception as e:
            log.error(f"Cache increment error: {e}")
            return 0

    async def get_ttl(self, key: str) -> int:
        """Get TTL of a key."""
        if not self._connected:
            return -2

        try:
            return await self.redis_client.ttl(key)
        except Exception as e:
            log.error(f"Cache TTL error: {e}")
            return -2

    # Session-specific methods
    async def get_session(self, session_id: str) -> Optional[dict]:
        """Get session data."""
        return await self.get(f"session:{session_id}")

    async def set_session(self, session_id: str, data: dict, ttl: int = 86400):
        """Set session data (24 hour default TTL)."""
        return await self.set(f"session:{session_id}", data, ttl)

    async def delete_session(self, session_id: str):
        """Delete session data."""
        return await self.delete(f"session:{session_id}")

    # Rate limiting methods
    async def check_rate_limit(self, key: str, limit: int, window: int) -> tuple:
        """
        Check rate limit for a key.
        Returns (allowed: bool, remaining: int, reset_at: int)
        """
        if not self._connected:
            return True, limit, 0

        try:
            current = await self.redis_client.get(key)
            if current is None:
                await self.redis_client.setex(key, window, "1")
                return True, limit - 1, window

            current = int(current)
            if current >= limit:
                ttl = await self.redis_client.ttl(key)
                return False, 0, ttl

            await self.redis_client.incr(key)
            remaining = limit - current - 1
            ttl = await self.redis_client.ttl(key)
            return True, remaining, ttl

        except Exception as e:
            log.error(f"Rate limit check error: {e}")
            return True, limit, 0


# Global cache instance
cache_service = CacheService()