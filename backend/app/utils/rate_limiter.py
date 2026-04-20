"""
DSA AutoGrader - Rate Limiter.

Simple in-memory rate limiting.
"""

import logging
import time
from collections import defaultdict
import threading
from typing import Dict, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import REDIS_URL

logger = logging.getLogger("dsa.rate_limiter")


class RateLimiter:
    """In-memory rate limiter with automatic cleanup."""

    _REDIS_SCRIPT = """
    local key = KEYS[1]
    local seq_key = key .. ":seq"
    local now = tonumber(ARGV[1])
    local minute_window = tonumber(ARGV[2])
    local hour_window = tonumber(ARGV[3])
    local per_minute = tonumber(ARGV[4])
    local per_hour = tonumber(ARGV[5])

    redis.call("ZREMRANGEBYSCORE", key, 0, now - hour_window)
    local minute_count = redis.call("ZCOUNT", key, now - minute_window + 1, now)
    local hour_count = redis.call("ZCARD", key)

    if minute_count >= per_minute then
        return {0, minute_window}
    end

    if hour_count >= per_hour then
        return {0, hour_window}
    end

    local seq = redis.call("INCR", seq_key)
    redis.call("EXPIRE", seq_key, hour_window)
    redis.call("ZADD", key, now, tostring(now) .. ":" .. tostring(seq))
    redis.call("EXPIRE", key, hour_window)
    return {1, 0}
    """

    def __init__(self, per_minute: int = 60, per_hour: int = 1000):
        self.per_minute = per_minute
        self.per_hour = per_hour
        self.requests: Dict[str, list] = defaultdict(list)
        self._last_cleanup = 0.0
        self._cleanup_interval = 300  # Cleanup every 5 minutes
        self._lock = threading.RLock()
        self._redis_url = REDIS_URL.strip()
        self._redis_client = None
        self._redis_script = None
        self._redis_available = False
        self._redis_checked = False

    def _ensure_redis(self) -> bool:
        """Lazy-load a Redis backend for shared rate limiting."""
        if self._redis_checked:
            return self._redis_available

        self._redis_checked = True
        if not self._redis_url:
            return False

        try:
            import redis.asyncio as redis

            self._redis_client = redis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            self._redis_script = self._redis_client.register_script(self._REDIS_SCRIPT)
            self._redis_available = True
            logger.info("Redis-backed rate limiting enabled")
        except Exception as exc:
            logger.warning("Redis rate limiter unavailable, using in-memory fallback: %s", exc)
            self._redis_client = None
            self._redis_script = None
            self._redis_available = False

        return self._redis_available

    def _cleanup(self) -> None:
        """Remove stale IPs that haven't been seen in 1 hour."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        self._last_cleanup = now

        with self._lock:
            stale_ips = [
                ip for ip, times in self.requests.items()
                if not times or max(times) < now - 3600
            ]
            for ip in stale_ips:
                del self.requests[ip]

        if stale_ips:
            logger.debug("Cleaned %d stale IPs entries", len(stale_ips))

    async def is_allowed(self, client_ip: str) -> Tuple[bool, int]:
        """
        Check if request is allowed.

        Returns:
            (allowed, retry_after_seconds)
        """
        if self._ensure_redis():
            try:
                now = int(time.time())
                key = f"dsa:rate_limit:{client_ip}"
                result = await self._redis_script(
                    keys=[key],
                    args=[now, 60, 3600, self.per_minute, self.per_hour],
                )
                allowed = int(result[0]) == 1
                retry_after = int(result[1])
                if not allowed:
                    logger.warning("Rate limit exceeded for %s", client_ip)
                return allowed, retry_after
            except Exception as exc:
                logger.warning("Redis rate limit check failed, falling back to memory: %s", exc)
                self._redis_available = False

        self._cleanup()  # Periodic stale IP cleanup
        now = time.time()
        minute_ago = now - 60
        hour_ago = now - 3600

        with self._lock:
            # Clean old requests
            self.requests[client_ip] = [t for t in self.requests[client_ip] if t > hour_ago]

            # Check limits
            recent = self.requests[client_ip]
            minute_count = sum(1 for t in recent if t > minute_ago)
            hour_count = len(recent)

            if minute_count >= self.per_minute:
                return False, 60
            if hour_count >= self.per_hour:
                return False, 3600

            # Record request
            self.requests[client_ip].append(now)
            return True, 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""

    def __init__(self, app, per_minute: int = 60, per_hour: int = 1000):
        super().__init__(app)
        self.limiter = RateLimiter(per_minute, per_hour)

    async def dispatch(self, request, call_next):
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Check rate limit
        allowed, retry_after = await self.limiter.is_allowed(client_ip)

        if not allowed:
            logger.warning("Rate limit exceeded for %s", client_ip)
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "retry_after": retry_after},
            )

        # Process request
        response = await call_next(request)
        return response
