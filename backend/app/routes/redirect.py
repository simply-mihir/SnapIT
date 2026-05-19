"""
Redirect route — the latency-sensitive hot path.

Lives at the app root (not /api) so short URLs look like https://host/abc123.
Click analytics are produced as Redis Stream events; a background consumer
materializes them into the click_events table asynchronously.
"""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from app.core.exceptions import URLExpiredError, URLNotFoundError
from app.routes.deps import get_url_service
from app.services.event_producer import EventProducer, get_event_producer
from app.services.url_service import URLService

router = APIRouter(tags=["redirect"])


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
    request: Request,
    background_tasks: BackgroundTasks,
    service: URLService = Depends(get_url_service),
    producer: EventProducer = Depends(get_event_producer),
) -> RedirectResponse:
    """Resolve short_id → original_url and 302 redirect."""
    # Cheap path filter — favicon, paths with dots/slashes, oversized IDs.
    if not short_id or len(short_id) > 64 or "." in short_id or "/" in short_id:
        raise HTTPException(status_code=404, detail="Not found")

    try:
        original_url = await service.resolve(short_id)
    except URLNotFoundError:
        raise HTTPException(status_code=404, detail="Short URL not found")
    except URLExpiredError:
        raise HTTPException(status_code=410, detail="Short URL has expired")

    # Fire-and-forget analytics — publishes to Redis stream; consumer
    # processes asynchronously. Never blocks the redirect.
    background_tasks.add_task(
        producer.publish_click,
        short_id=short_id,
        user_agent=request.headers.get("user-agent"),
        referrer=request.headers.get("referer"),  # HTTP spec misspells it
    )

    return RedirectResponse(
        url=original_url,
        status_code=status.HTTP_302_FOUND,
    )