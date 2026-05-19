"""
Liveness + readiness endpoints.

/health/live is a shallow check used by Docker / Render for restart loops.
/health/ready verifies Postgres and Redis are reachable, which is what
a load balancer should use to decide whether to send traffic.
"""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.services.cache import CacheClient, get_cache

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def liveness() -> dict:
    return {"status": "ok"}


@router.get("/ready")
async def readiness(
    db: AsyncSession = Depends(get_session),
    cache: CacheClient = Depends(get_cache),
) -> JSONResponse:
    checks = {"db": False, "redis": False}
    try:
        await db.execute(text("SELECT 1"))
        checks["db"] = True
    except Exception:
        pass
    try:
        await cache.client.ping()
        checks["redis"] = True
    except Exception:
        pass

    ok = all(checks.values())
    return JSONResponse(
        status_code=200 if ok else 503,
        content={"status": "ok" if ok else "degraded", "checks": checks},
    )
