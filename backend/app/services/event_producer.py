"""
Click-event producer.

Publishes click events to a Redis stream. Lightweight — no DB writes,
no synchronous waits. The redirect hot path calls this and immediately
returns the 302.

A downstream consumer (event_consumer.py) reads from the stream and
materializes events into the click_events table plus aggregate updates
on the urls table.

Why Redis Streams (not Pub/Sub):
- Persistent: events survive consumer restarts.
- Consumer groups: at-least-once delivery with explicit XACK.
- MAXLEN cap: prevents unbounded growth — old events drop when capped.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from app.services.cache import CacheClient

logger = logging.getLogger(__name__)

# Stream key + cap. 100k events is roughly a week of traffic at our scale —
# well past the point a consumer would still be catching up.
STREAM_KEY = "snapit:clicks"
STREAM_MAXLEN = 100_000


class EventProducer:
    """Publishes click events to the Redis stream."""

    def __init__(self, cache: CacheClient):
        self._cache = cache

    async def publish_click(
        self,
        short_id: str,
        user_agent: Optional[str] = None,
        referrer: Optional[str] = None,
    ) -> None:
        """
        Append a click event to the stream. Fire-and-forget — errors
        are logged but never propagated. Analytics must never break the
        redirect path.
        """
        fields: dict[str, str] = {
            "short_id": short_id,
            "ts": str(datetime.now(timezone.utc).timestamp()),
        }
        # Cap header values to 512 chars to keep stream entries bounded.
        if user_agent:
            fields["ua"] = user_agent[:512]
        if referrer:
            fields["referrer"] = referrer[:512]

        try:
            await self._cache.client.xadd(
                STREAM_KEY,
                fields,
                maxlen=STREAM_MAXLEN,
                approximate=True,  # ~ trim is dramatically cheaper than exact
            )
        except Exception:
            logger.exception(
                "Failed to publish click event for short_id=%s", short_id
            )


# Module-level singleton — reuses the CacheClient's Redis connection.
from app.services.cache import cache as _cache_singleton

producer = EventProducer(_cache_singleton)


def get_event_producer() -> EventProducer:
    """FastAPI dependency."""
    return producer