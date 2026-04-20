"""
DSA AutoGrader - In-Memory Cache Implementation.

Simple cache for development/testing when Redis is not available.
"""

import asyncio
import logging
import time
from collections import OrderedDict
from typing import Any, Dict, Optional

from app.cache.cache_interface import ICache

logger = logging.getLogger("dsa.cache")


class InMemoryCache(ICache):
    """
    In-memory cache implementation.

    Features:
    - TTL support
    - LRU eviction
    - Thread-safe with asyncio lock
    """

    def __init__(self, max_size: int = 1000):
        self._cache: OrderedDict = OrderedDict()
        self._expiry: Dict[str, float] = {}
        self._max_size = max_size
        self._lock = asyncio.Lock()
        self._available = True
        logger.info("In-memory cache initialized")

    def _key(self, key: str) -> str:
        """Return key as-is (no prefix needed)."""
        return key

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        async with self._lock:
            if key not in self._cache:
                return None

            # Check expiry
            if key in self._expiry:
                if time.time() > self._expiry[key]:
                    del self._cache[key]
                    del self._expiry[key]
                    return None

            # Move to end (LRU)
            self._cache.move_to_end(key)
            return self._cache[key]

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with optional TTL."""
        async with self._lock:
            # Evict if at capacity
            if len(self._cache) >= self._max_size:
                oldest = next(iter(self._cache))
                del self._cache[oldest]
                if oldest in self._expiry:
                    del self._expiry[oldest]
                logger.debug("Evicted oldest key: %s", oldest)

            self._cache[key] = value
            self._cache.move_to_end(key)

            if ttl:
                self._expiry[key] = time.time() + ttl
            elif key in self._expiry:
                del self._expiry[key]

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                if key in self._expiry:
                    del self._expiry[key]
                return True
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        async with self._lock:
            if key not in self._cache:
                return False

            # Check expiry
            if key in self._expiry:
                if time.time() > self._expiry[key]:
                    del self._cache[key]
                    del self._expiry[key]
                    return False

            return True

    async def clear(self) -> None:
        """Clear all cache."""
        async with self._lock:
            self._cache.clear()
            self._expiry.clear()
            logger.info("In-memory cache cleared")

    async def health_check(self) -> bool:
        """Check if cache is available."""
        return self._available

    def close(self) -> None:
        """Close cache (no-op for in-memory)."""
        self._cache.clear()
        self._expiry.clear()
        logger.info("In-memory cache closed")

    # ==================== CONVENIENCE METHODS ====================

    async def get_or_set(
        self, key: str, factory: Any, ttl: Optional[int] = None
    ) -> Any:
        """Get from cache or set using factory."""
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
        """Increment a counter in cache."""
        async with self._lock:
            current = self._cache.get(key, 0)
            new_value = current + amount
            self._cache[key] = new_value
            return new_value

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "available": self._available,
        }
