"""
Redis-backed fixed-window rate limiter.

Uses INCR + EXPIRE atomically per window. Fixed-window is simple and
has a small burst edge case at window boundaries, but it's cheap and
more than sufficient for anti-abuse at the URL-creation endpoint.
"""
from app.core.config import settings
from app.core.exceptions import RateLimitExceededError
from app.services.cache import CacheClient


class RateLimiter:
    def __init__(self, cache: CacheClient, max_requests: int, window_seconds: int):
        self._cache = cache
        self._max = max_requests
        self._window = window_seconds

    async def check(self, identifier: str) -> None:
        """
        Increment the counter for `identifier` and raise if over limit.

        Single round-trip via a pipeline keeps latency low on the create path.
        """
        key = f"ratelimit:{identifier}"
        pipe = self._cache.client.pipeline()
        pipe.incr(key, 1)
        pipe.expire(key, self._window, nx=True)  # only set TTL on first hit
        pipe.ttl(key)
        count, _expire_ok, ttl = await pipe.execute()

        if count > self._max:
            retry_after = ttl if ttl and ttl > 0 else self._window
            raise RateLimitExceededError(retry_after=int(retry_after))


def get_rate_limiter(cache: CacheClient) -> RateLimiter:
    return RateLimiter(
        cache=cache,
        max_requests=settings.RATE_LIMIT_MAX_REQUESTS,
        window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
    )
