"""
FastAPI application entrypoint.

Wiring:
- Lifespan context manages Redis + DB connections.
- CORS configured for the frontend.
- Three routers: api/shorten+analytics, health, and the redirect catch-all
  (mounted last so /api and /health take precedence).
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.database import init_db
from app.routes import health, redirect, shorten
from app.services.cache import cache

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start/stop Redis + DB; create tables on first boot for local dev."""
    logger.info("Starting %s (env=%s)", settings.APP_NAME, settings.APP_ENV)
    await cache.connect()
    await init_db()
    logger.info("Startup complete.")
    try:
        yield
    finally:
        logger.info("Shutting down...")
        await cache.disconnect()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Scalable URL shortener with Redis caching, rate limiting, and analytics.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Order matters: API + health first, redirect catch-all last.
app.include_router(shorten.router)
app.include_router(health.router)
app.include_router(redirect.router)


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
    }
