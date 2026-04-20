"""
DSA AutoGrader - Cache Interface.

Abstract base class for caching.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class ICache(ABC):
    """
    Interface for cache layer.

    Implementations: RedisCache, InMemoryCache
    """

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with optional TTL (seconds)."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if cache is healthy."""
        pass
