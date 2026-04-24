"""
Redirect route — the latency-sensitive hot path.

Lives at the app root (not /api) so short URLs look like https://host/abc123.
We schedule analytics writes in the background so they never block redirect.
"""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import URLExpiredError, URLNotFoundError
from app.db.database import AsyncSessionLocal, get_session
from app.routes.deps import get_url_service
from app.services.cache import CacheClient, get_cache
from app.services.url_service import URLService

router = APIRouter(tags=["redirect"])


async def _record_click_async(short_id: str) -> None:
    """
    Background task — opens its own session because the request-scoped one
    will already be closed by the time BackgroundTasks runs.
    """
    async with AsyncSessionLocal() as session:
        # Cache isn't needed here; we go straight to DB.
        from app.services.cache import cache  # module-level singleton
        service = URLService(db=session, cache=cache)
        try:
            await service.record_click(short_id)
        except Exception:
            # Analytics should never break the redirect path — swallow + log.
            import logging
            logging.exception("Failed to record click for %s", short_id)


@router.get(
    "/{short_id}",
    responses={
        302: {"description": "Redirect to original URL"},
        404: {"description": "Not found"},
        410: {"description": "Expired"},
    },
    include_in_schema=False,
)
async def redirect(
    short_id: str,
    background_tasks: BackgroundTasks,
    service: URLService = Depends(get_url_service),
) -> RedirectResponse:
    """Resolve short_id → original_url and 302 redirect."""
    # Simple guard against obviously-bad paths (favicon, etc.) — cheaper
    # than a DB round-trip.
    if not short_id or len(short_id) > 64 or "." in short_id or "/" in short_id:
        raise HTTPException(status_code=404, detail="Not found")

    try:
        original_url = await service.resolve(short_id)
    except URLNotFoundError:
        raise HTTPException(status_code=404, detail="Short URL not found")
    except URLExpiredError:
        raise HTTPException(status_code=410, detail="Short URL has expired")

    # Fire-and-forget analytics.
    background_tasks.add_task(_record_click_async, short_id)

    return RedirectResponse(
        url=original_url,
        status_code=status.HTTP_302_FOUND,
    )
