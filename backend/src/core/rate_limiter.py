import time
from uuid import UUID

from redis.asyncio import Redis

from src.metrics.instruments import RATE_LIMIT_REJECTIONS


class RateLimiter:
    """Fixed-window rate limiter backed by Redis.

    Each device key gets `max_requests` per `window_seconds` window.
    """

    def __init__(self, redis: Redis, max_requests: int = 100, window_seconds: int = 60) -> None:
        self.redis = redis
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def check(self, device_id: UUID) -> tuple[bool, int, int]:
        """Check whether a request from this device is allowed.

        Returns (allowed, remaining, reset_seconds).
        """
        window = int(time.time()) // self.window_seconds
        key = f"rl:{device_id}:{window}"

        count = await self.redis.incr(key)
        if count == 1:
            await self.redis.expire(key, self.window_seconds)

        remaining = max(0, self.max_requests - count)
        ttl = await self.redis.ttl(key)

        allowed = count <= self.max_requests
        if not allowed:
            RATE_LIMIT_REJECTIONS.inc()

        return allowed, remaining, max(ttl, 0)
