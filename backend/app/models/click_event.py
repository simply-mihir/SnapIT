"""
Click event — one row per redirect, written asynchronously by the
Redis Streams consumer.

This is a fact table in a simple star schema:
- Dimension: urls (the short link being clicked)
- Fact: click_events (one event per redirect)

Keeping clicks out of the urls row lets us:
- Query temporal patterns (clicks per hour, weekly trends)
- Break clicks down by device/browser/referrer without bloating urls
- Replay history if the aggregation logic changes
"""
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ClickEvent(Base):
    """A single redirect occurrence."""

    __tablename__ = "click_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    short_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("urls.short_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Parsed User-Agent dimensions — populated by the consumer.
    device: Mapped[str | None] = mapped_column(String(32), nullable=True)
    browser: Mapped[str | None] = mapped_column(String(64), nullable=True)
    os: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Raw context (kept for replay / forensics).
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    referrer: Mapped[str | None] = mapped_column(String(512), nullable=True)

    __table_args__ = (
        Index("ix_click_events_short_id_occurred_at", "short_id", "occurred_at"),
    )