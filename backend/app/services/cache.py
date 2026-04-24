"""
Redis cache client and cache-aside helpers.

The redirect hot path uses this first; DB is only hit on cache miss.
We namespace keys with `url:` to keep room for future caches
(e.g. analytics counters).
"""
from typing import Optional

import redis.asyncio as redis

from app.core.config import settings

_URL_KEY_PREFIX = "url:"
_NEGATIVE_TTL = 30  # short TTL for "not found" markers to dampen DB stampedes


class CacheClient:
    """Thin async wrapper around redis-py for URL lookups."""

    def __init__(self, url: str):
        self._url = url
        self._client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        if self._client is None:
            self._client = redis.from_url(
                self._url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
            )
            # Fail fast at startup if Redis is unreachable.
            await self._client.ping()

    async def disconnect(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            raise RuntimeError("CacheClient not connected. Call connect() first.")
        return self._client

    @staticmethod
    def _key(short_id: str) -> str:
        return f"{_URL_KEY_PREFIX}{short_id}"

    async def get_url(self, short_id: str) -> Optional[str]:
        """
        Returns the cached original_url, or None on miss.

        A sentinel value "__NOT_FOUND__" is used to cache negative lookups
        briefly, protecting the DB from repeated requests for bogus IDs.
        """
        value = await self.client.get(self._key(short_id))
        if value == "__NOT_FOUND__":
            return None
        return value

    async def set_url(
        self, short_id: str, original_url: str, ttl_seconds: Optional[int] = None
    ) -> None:
        ttl = ttl_seconds if ttl_seconds and ttl_seconds > 0 else settings.CACHE_DEFAULT_TTL
        await self.client.set(self._key(short_id), original_url, ex=ttl)

    async def set_not_found(self, short_id: str) -> None:
        await self.client.set(self._key(short_id), "__NOT_FOUND__", ex=_NEGATIVE_TTL)

    async def delete_url(self, short_id: str) -> None:
        await self.client.delete(self._key(short_id))


# Module-level singleton — FastAPI lifespan manages connect/disconnect.
cache = CacheClient(settings.REDIS_URL)


def get_cache() -> CacheClient:
    """FastAPI dependency."""
    return cache
