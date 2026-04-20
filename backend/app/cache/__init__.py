"""
DSA AutoGrader - Cache Package.

Caching layer for performance.
"""

from app.cache.cache_interface import ICache
from app.cache.redis_cache import RedisCache

__all__ = [
    "RedisCache",
    "ICache",
]
