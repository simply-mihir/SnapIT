"""
Async SQLAlchemy engine + session management.

Uses an AsyncEngine with connection pooling for high-throughput reads.
Session lifecycle is dependency-injected into FastAPI routes.
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _make_engine() -> AsyncEngine:
    """
    Build the async engine with pooling tuned for a busy redirect service.

    - pool_pre_ping avoids "server closed the connection unexpectedly"
      after idle periods (common on managed Postgres).
    - pool_size + max_overflow limits total connections so we don't
      blow past provider quotas.
    """
    url = settings.DATABASE_URL
    connect_args = {}
    if url.startswith("sqlite"):
        # Test fallback — SQLite doesn't support pool args.
        return create_async_engine(url, echo=settings.DEBUG, future=True)
    return create_async_engine(
        url,
        echo=settings.DEBUG,
        future=True,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


engine: AsyncEngine = _make_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a scoped async session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """
    Create tables on startup.

    In production, prefer Alembic migrations — this is included so local
    Docker Compose works out of the box without a migration step.
    """
    from app.models import url as _url_model  # noqa: F401 (ensure registration)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
