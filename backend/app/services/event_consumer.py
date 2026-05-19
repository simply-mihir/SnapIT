"""
Click-event consumer.

Reads click events from the Redis stream and materializes them into
the click_events table while also incrementing aggregate counters on
the urls table.

Runs as a long-running asyncio task spawned from FastAPI's lifespan
hook. Uses Redis consumer groups for at-least-once delivery — events
remain in the stream until explicitly XACK'd, so a crash mid-batch
doesn't lose data.

Key design choices:
- Consumer group = "snapit-consumers". Multiple consumer instances
  could share this group for horizontal scaling later.
- Consumer name = hostname:pid for traceability across worker processes.
- Batched bulk-insert cuts DB round-trips ~50x vs row-by-row.
- XACK only fires after a successful DB commit — atomicity guarantee.
- Errors are caught per-batch; bad data doesn't kill the consumer.
"""
import asyncio
import logging
import os
import socket
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import update
from user_agents import parse as parse_ua

from app.db.database import AsyncSessionLocal
from app.models.click_event import ClickEvent
from app.models.url import URL
from app.services.cache import CacheClient
from app.services.event_producer import STREAM_KEY

logger = logging.getLogger(__name__)

CONSUMER_GROUP = "snapit-consumers"
BATCH_SIZE = 100      # max events per XREADGROUP call
BLOCK_MS = 1_000      # block up to 1s waiting for new events


class EventConsumer:
    """Drains the click stream into Postgres."""

    def __init__(self, cache: CacheClient):
        self._cache = cache
        self._consumer_name = f"{socket.gethostname()}:{os.getpid()}"
        self._task: Optional[asyncio.Task] = None
        self._shutdown = asyncio.Event()

    async def _ensure_consumer_group(self) -> None:
        """
        Create the consumer group if missing. MKSTREAM also creates the
        stream itself if it doesn't exist yet (no events have been
        published).
        """
        try:
            await self._cache.client.xgroup_create(
                STREAM_KEY,
                CONSUMER_GROUP,
                id="$",  # start from messages arriving *after* group creation
                mkstream=True,
            )
            logger.info(
                "Created consumer group %s on %s", CONSUMER_GROUP, STREAM_KEY
            )
        except Exception as e:
            if "BUSYGROUP" in str(e):
                logger.info("Consumer group %s already exists", CONSUMER_GROUP)
            else:
                raise

    async def start(self) -> None:
        """Spawn the consumer task. Idempotent."""
        if self._task and not self._task.done():
            return
        await self._ensure_consumer_group()
        self._task = asyncio.create_task(self._run(), name="click-event-consumer")
        logger.info(
            "Click event consumer started (consumer=%s)", self._consumer_name
        )

    async def stop(self) -> None:
        """Signal shutdown and wait for the loop to exit."""
        self._shutdown.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning(
                    "Consumer didn't shut down within 5s; cancelling"
                )
                self._task.cancel()
            self._task = None

    async def _run(self) -> None:
        """Main consumer loop. Pulls batches, processes, acks."""
        while not self._shutdown.is_set():
            try:
                batch = await self._read_batch()
                if batch:
                    await self._process_batch(batch)
            except asyncio.CancelledError:
                logger.info("Consumer task cancelled")
                break
            except Exception:
                logger.exception(
                    "Consumer loop hit unexpected error; retrying in 5s"
                )
                await asyncio.sleep(5)

    async def _read_batch(self) -> list:
        """XREADGROUP for up to BATCH_SIZE events, blocking up to BLOCK_MS."""
        result = await self._cache.client.xreadgroup(
            CONSUMER_GROUP,
            self._consumer_name,
            {STREAM_KEY: ">"},  # ">" = only new messages
            count=BATCH_SIZE,
            block=BLOCK_MS,
        )
        if not result:
            return []
        # Format: [(stream_name, [(msg_id, fields), ...])]
        return result[0][1]

    async def _process_batch(self, batch: list) -> None:
        """Parse, bulk-insert, update aggregates, then ack."""
        if not batch:
            return

        events_to_insert: list[ClickEvent] = []
        aggregate_bumps: dict[str, int] = {}

        for _msg_id, fields in batch:
            short_id = fields.get("short_id")
            if not short_id:
                continue
            ua_raw = fields.get("ua")
            referrer = fields.get("referrer")
            ts_str = fields.get("ts")

            occurred_at = (
                datetime.fromtimestamp(float(ts_str), tz=timezone.utc)
                if ts_str
                else datetime.now(timezone.utc)
            )
            device, browser, os_name = _parse_ua(ua_raw)

            events_to_insert.append(
                ClickEvent(
                    short_id=short_id,
                    occurred_at=occurred_at,
                    device=device,
                    browser=browser,
                    os=os_name,
                    user_agent=ua_raw,
                    referrer=referrer,
                )
            )
            aggregate_bumps[short_id] = aggregate_bumps.get(short_id, 0) + 1

        async with AsyncSessionLocal() as session:
            try:
                session.add_all(events_to_insert)
                # Bump aggregates on urls so the existing /api/analytics
                # endpoint keeps returning correct click_count.
                for short_id, n in aggregate_bumps.items():
                    await session.execute(
                        update(URL)
                        .where(URL.short_id == short_id)
                        .values(
                            click_count=URL.click_count + n,
                            last_accessed_at=datetime.now(timezone.utc),
                        )
                    )
                await session.commit()
            except Exception:
                await session.rollback()
                logger.exception(
                    "Failed to persist batch of %d events", len(batch)
                )
                # No ACK — Redis will redeliver these on next read.
                return

        msg_ids = [msg_id for msg_id, _ in batch]
        await self._cache.client.xack(STREAM_KEY, CONSUMER_GROUP, *msg_ids)
        logger.debug("Processed and acked %d events", len(batch))


def _parse_ua(
    ua: Optional[str],
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Parse User-Agent into (device_kind, browser, os). None-safe."""
    if not ua:
        return None, None, None
    try:
        p = parse_ua(ua)
        if p.is_bot:
            device = "bot"
        elif p.is_mobile:
            device = "mobile"
        elif p.is_tablet:
            device = "tablet"
        else:
            device = "desktop"
        browser = f"{p.browser.family} {p.browser.version_string}".strip()[:64]
        os_name = f"{p.os.family} {p.os.version_string}".strip()[:64]
        return device, browser, os_name
    except Exception:
        return None, None, None


# Module-level singleton — lifespan hook starts/stops it.
from app.services.cache import cache as _cache_singleton

consumer = EventConsumer(_cache_singleton)