"""
URL ORM model.

Indexes:
- short_id: unique, primary lookup path for the redirect hot route.
- custom_alias: unique (nullable) to allow user-specified slugs.
- expires_at: indexed for efficient cleanup jobs of expired links.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class URL(Base):
    __tablename__ = "urls"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    original_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    short_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    custom_alias: Mapped[Optional[str]] = mapped_column(
        String(64), unique=True, nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    click_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_urls_expires_at", "expires_at"),
    )

    def is_expired(self) -> bool:
        """True if expires_at is set and in the past (UTC-aware)."""
        if self.expires_at is None:
            return False
        now = datetime.now(self.expires_at.tzinfo) if self.expires_at.tzinfo else datetime.utcnow()
        return self.expires_at <= now

    def __repr__(self) -> str:
        return f"<URL short_id={self.short_id!r} original_url={self.original_url!r}>"
