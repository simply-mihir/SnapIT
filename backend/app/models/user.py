"""
User account (optional feature — anonymous shortening never needs one).

A user signs in with username+password, Google, or both. `password_hash`
is NULL for Google-only accounts; `google_sub` is NULL for password-only ones.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    username: Mapped[Optional[str]] = mapped_column(
        String(32), unique=True, nullable=True, index=True
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(320), unique=True, nullable=True, index=True
    )
    display_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    google_sub: Mapped[Optional[str]] = mapped_column(
        String(64), unique=True, nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
