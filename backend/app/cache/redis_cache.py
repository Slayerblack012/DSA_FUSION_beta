"""
DSA AutoGrader - Redis Cache Implementation.

Production-ready cache layer using Redis.
"""

import asyncio
import json
import logging
from typing import Any, Optional

from app.cache.cache_interface import ICache

logger = logging.getLogger("dsa.cache")


class RedisCache(ICache):
    """
    Redis cache implementation.

    Features:
    - TTL support
    - JSON serialization
    - Connection pooling
    - Automatic fallback on failure
    """

    def __init__(self, redis_url: str, prefix: str = "dsa:cache:"):
        self._redis_url = redis_url
        self._prefix = prefix
        self._client = None
        self._available = False
        self._connect()

    def _connect(self) -> None:
        """Connect to Redis."""
        try:
            import redis.asyncio as redis

            self._client = redis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            self._available = True
            logger.info("Redis cache connected: %s", self._redis_url)
        except ImportError:
            logger.warning("Redis package not installed, cache disabled")
            self._available = False
        except Exception as e:
            logger.warning("Failed to connect to Redis: %s, cache disabled", e)
            self._available = False

    def _key(self, key: str) -> str:
        """Add prefix to key."""
        return f"{self._prefix}{key}"

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        if not self._available:
            return None

        try:
            value = await self._client.get(self._key(key))
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error("Redis GET error: %s", e)
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        if not self._available:
            return

        try:
            serialized = json.dumps(value)
            if ttl:
                await self._client.setex(self._key(key), ttl, serialized)
            else:
                await self._client.set(self._key(key), serialized)
        except Exception as e:
            logger.error("Redis SET error: %s", e)

    async def delete(self, key: str) -> bool:
        """
        Delete value from cache.

        Args:
            key: Cache key

        Returns:
            True if deleted
        """
        if not self._available:
            return False

        try:
            result = await self._client.delete(self._key(key))
            return result > 0
        except Exception as e:
            logger.error("Redis DELETE error: %s", e)
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if exists
        """
        if not self._available:
            return False

        try:
            result = await self._client.exists(self._key(key))
            return result > 0
        except Exception as e:
            logger.error("Redis EXISTS error: %s", e)
            return False

    async def clear(self) -> None:
        """Clear all cache with our prefix."""
        if not self._available:
            return

        try:
            keys = await self._client.keys(f"{self._prefix}*")
            if keys:
                await self._client.delete(*keys)
                logger.info("Cleared %d cache keys", len(keys))
        except Exception as e:
            logger.error("Redis CLEAR error: %s", e)

    async def health_check(self) -> bool:
        """Check if Redis is available."""
        if not self._available:
            return False

        try:
            await self._client.ping()
            return True
        except Exception as e:
            logger.error("Redis health check failed: %s", e)
            return False

    def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            import asyncio

            asyncio.create_task(self._client.close())
            logger.info("Redis cache connection closed")

    # ==================== CONVENIENCE METHODS ====================

    async def get_or_set(
        self, key: str, factory: Any, ttl: Optional[int] = None
    ) -> Any:
        """
        Get from cache or set using factory.

        Args:
            key: Cache key
            factory: Callable to generate value if not cached
            ttl: Time to live in seconds

        Returns:
            Cached or generated value
        """
        cached = await self.get(key)
        if cached is not None:
            return cached

        # Generate value
        if asyncio.iscoroutinefunction(factory):
            value = await factory()
        else:
            value = factory()

        # Cache it
        await self.set(key, value, ttl)
        return value

    async def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment a counter in cache.

        Args:
            key: Cache key
            amount: Amount to increment

        Returns:
            New value
        """
        if not self._available:
            return 0

        try:
            return await self._client.incrby(self._key(key), amount)
        except Exception as e:
            logger.error("Redis INCREMENT error: %s", e)
            return 0
