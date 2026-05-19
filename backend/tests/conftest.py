"""
Test fixtures.

We swap Postgres → SQLite (aiosqlite) and Redis → fakeredis so the suite
runs offline. All business logic exercises the same code paths.
"""
import asyncio
import os
from typing import AsyncGenerator

# Point to SQLite BEFORE importing app modules so Settings picks it up.
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"  # overridden by fakeredis
os.environ["BASE_URL"] = "http://testserver"
os.environ["RATE_LIMIT_MAX_REQUESTS"] = "100"  # avoid 429s in tests

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

try:
    import fakeredis.aioredis as fakeredis_async
    HAS_FAKEREDIS = True
except ImportError:
    HAS_FAKEREDIS = False


@pytest.fixture(scope="session")
def event_loop():
    """Session-scoped loop so async fixtures persist across a test module."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def app_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Boot a FastAPI app with SQLite + fakeredis and yield an httpx client.
    """
    from app import main as app_main
    from app.db import database as db_mod
    from app.services import cache as cache_mod

    # Fresh in-memory engine per test for isolation.
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    db_mod.engine = engine
    db_mod.AsyncSessionLocal = SessionLocal

    from app.db.database import Base
    from app.models import url as _url_model  # noqa
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Swap in fakeredis.
    if HAS_FAKEREDIS:
        cache_mod.cache._client = fakeredis_async.FakeRedis(decode_responses=True)
    else:
        pytest.skip("fakeredis not installed")

    # Override init_db/cache.connect so lifespan doesn't try to reconnect.
    original_init_db = db_mod.init_db
    original_connect = cache_mod.cache.connect

    async def noop_init_db():
        return None

    async def noop_connect():
        return None

    db_mod.init_db = noop_init_db
    cache_mod.cache.connect = noop_connect

    transport = ASGITransport(app=app_main.app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Manually run lifespan startup
        async with app_main.app.router.lifespan_context(app_main.app):
            yield client

    db_mod.init_db = original_init_db
    cache_mod.cache.connect = original_connect
    await engine.dispose()
