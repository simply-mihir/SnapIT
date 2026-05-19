"""
Async SQLAlchemy engine + session management.
"""
import uuid
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _is_pgbouncer_url(url: str) -> bool:
    """Detect pgbouncer (Supabase Transaction Pooler) URLs."""
    lowered = url.lower()
    return (
        ":6543/" in lowered
        or ".pooler.supabase.com" in lowered
        or "pgbouncer=true" in lowered
    )


def _make_engine() -> AsyncEngine:
    url = settings.DATABASE_URL
    if url.startswith("sqlite"):
        return create_async_engine(url, echo=settings.DEBUG, future=True)

    if _is_pgbouncer_url(url):
        # pgbouncer in transaction mode:
        #   1. disable asyncpg's and SQLAlchemy's statement caches
        #   2. give every prepared statement a UNIQUE name so collisions
        #      across pooled underlying Postgres connections are impossible
        #   3. skip SQLAlchemy's own pool — pgbouncer is already pooling
        return create_async_engine(
            url,
            echo=settings.DEBUG,
            future=True,
            poolclass=NullPool,
            connect_args={
                "statement_cache_size": 0,
                "prepared_statement_cache_size": 0,
                "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4()}__",
            },
        )

    # Direct Postgres connection — regular pool.
    return create_async_engine(
        url,
        echo=settings.DEBUG,
        future=True,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_pre_ping=True,
        connect_args={},
    )


engine: AsyncEngine = _make_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    from app.models import url as _url_model  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)