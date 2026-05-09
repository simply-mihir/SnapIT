"""
URL service layer — all business logic for shortening, resolving, and analytics.

Keeping this separate from routes makes it trivially unit-testable and
allows us to swap transports later (CLI, gRPC, worker job) without
touching the core logic.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AliasTakenError,
    InvalidAliasError,
    InvalidURLError,
    URLExpiredError,
    URLNotFoundError,
)
from app.core.utils import (
    generate_short_id,
    is_valid_alias,
    is_valid_url,
    normalize_url,
)
from app.models.url import URL
from app.services.cache import CacheClient


class URLService:
    def __init__(self, db: AsyncSession, cache: CacheClient):
        self.db = db
        self.cache = cache

    # ----- Creation -----

    async def create_short_url(
        self,
        original_url: str,
        custom_alias: Optional[str] = None,
        expires_in_seconds: Optional[int] = None,
    ) -> URL:
        """
        Create a new short URL.

        - Validates URL + alias format up front.
        - Uses DB unique constraint as the source of truth for alias collisions
          (race-safe — two concurrent inserts can't both win).
        - Caches the mapping on create so the first redirect is a cache hit.
        """
        original_url = normalize_url(original_url)
        if not is_valid_url(original_url):
            raise InvalidURLError("Invalid URL. Must be http(s) and well-formed.")

        if custom_alias is not None:
            if not is_valid_alias(custom_alias):
                raise InvalidAliasError(
                    "Alias must be 3-32 chars, alphanumeric + - _, "
                    "and not a reserved word."
                )
            # Pre-check for nicer error; real enforcement is the unique index.
            existing = await self._find_by_short_id_or_alias(custom_alias)
            if existing is not None:
                raise AliasTakenError(f"Alias '{custom_alias}' is already in use.")

        expires_at: Optional[datetime] = None
        if expires_in_seconds is not None and expires_in_seconds > 0:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)

        short_id = custom_alias or await self._generate_unique_short_id()

        url = URL(
            original_url=original_url,
            short_id=short_id,
            custom_alias=custom_alias,
            expires_at=expires_at,
        )
        self.db.add(url)
        try:
            await self.db.commit()
        except IntegrityError:
            # Lost the race on alias/short_id uniqueness.
            await self.db.rollback()
            if custom_alias:
                raise AliasTakenError(f"Alias '{custom_alias}' is already in use.")
            # Short_id collision is astronomically rare at 62^7 but possible;
            # just retry once with a fresh one.
            url.short_id = await self._generate_unique_short_id()
            self.db.add(url)
            await self.db.commit()

        await self.db.refresh(url)

        # Warm the cache; TTL aligned with expiration if set.
        ttl = self._cache_ttl_for(url)
        await self.cache.set_url(url.short_id, url.original_url, ttl_seconds=ttl)
        return url

    # ----- Resolution (redirect hot path) -----

    async def resolve(self, short_id: str) -> str:
        """
        Resolve a short_id to its original URL.

        1. Check cache.
        2. On miss, query DB.
        3. Honor expiration.
        4. Populate cache for next time.

        Returns the original_url string. Caller is responsible for the redirect.
        """
        # Step 1: cache.
        cached = await self.cache.get_url(short_id)
        if cached is not None:
            return cached

        # Step 2: DB.
        url = await self._find_by_short_id_or_alias(short_id)
        if url is None:
            # Negative-cache to dampen repeated bogus lookups.
            await self.cache.set_not_found(short_id)
            raise URLNotFoundError(f"Short URL '{short_id}' not found.")

        # Step 3: expiration.
        if url.is_expired():
            raise URLExpiredError(f"Short URL '{short_id}' has expired.")

        # Step 4: repopulate cache.
        ttl = self._cache_ttl_for(url)
        await self.cache.set_url(url.short_id, url.original_url, ttl_seconds=ttl)
        return url.original_url

    # ----- Analytics -----

    async def record_click(self, short_id: str) -> None:
        """
        Fire-and-forget style analytics write.

        Uses a single atomic UPDATE to avoid read-modify-write races
        when many clicks arrive concurrently.
        """
        stmt = (
            update(URL)
            .where(URL.short_id == short_id)
            .values(
                click_count=URL.click_count + 1,
                last_accessed_at=datetime.now(timezone.utc),
            )
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def get_analytics(self, short_id: str) -> URL:
        url = await self._find_by_short_id_or_alias(short_id)
        if url is None:
            raise URLNotFoundError(f"Short URL '{short_id}' not found.")
        return url

    # ----- Internals -----

    async def _find_by_short_id_or_alias(self, identifier: str) -> Optional[URL]:
        """Lookup by short_id first, then custom_alias (both unique indexes)."""
        stmt = select(URL).where(
            (URL.short_id == identifier) | (URL.custom_alias == identifier)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _generate_unique_short_id(self) -> str:
        """
        Generate a short_id not present in DB. 62^7 ≈ 3.5T keyspace makes
        the retry loop almost never execute past the first attempt.
        """
        for _ in range(settings.SHORT_ID_MAX_RETRIES):
            candidate = generate_short_id(settings.SHORT_ID_LENGTH)
            existing = await self._find_by_short_id_or_alias(candidate)
            if existing is None:
                return candidate
        # Fall back to a longer ID rather than raising — keeps the service up.
        return generate_short_id(settings.SHORT_ID_LENGTH + 3)

    @staticmethod
    def _cache_ttl_for(url: URL) -> Optional[int]:
        """
        Cache TTL strategy:
        - Links with an expiration: cache for exactly that window. The link
          and its cache entry die together — no stale reads possible.
        - Permanent links: cache for 30 days, auto-renewed on every visit
          (resolve() re-warms on miss) so popular links effectively live
          forever.
        LFU eviction in Upstash is the safety net for memory pressure:
        cold/never-visited entries get pushed out before hot ones.
        """
        PERMANENT_TTL = 30 * 24 * 3600  # 30 days
        if url.expires_at is None:
            return PERMANENT_TTL
        now = datetime.now(url.expires_at.tzinfo or timezone.utc)
        remaining = int((url.expires_at - now).total_seconds())
        return max(1, remaining)
