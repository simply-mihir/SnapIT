"""
Shortening + analytics routes (mounted under /api).
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.config import settings
from app.core.exceptions import (
    AliasTakenError,
    InvalidAliasError,
    InvalidURLError,
    RateLimitExceededError,
    URLNotFoundError,
)
from app.routes.deps import get_client_ip, get_url_service
from app.schemas.url import ShortenRequest, ShortenResponse, URLAnalytics
from app.services.cache import CacheClient, get_cache
from app.services.rate_limiter import get_rate_limiter
from app.services.url_service import URLService

router = APIRouter(prefix="/api", tags=["urls"])


@router.post(
    "/shorten",
    response_model=ShortenResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Invalid URL or alias"},
        409: {"description": "Alias already taken"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def shorten(
    payload: ShortenRequest,
    request: Request,
    service: URLService = Depends(get_url_service),
    cache: CacheClient = Depends(get_cache),
) -> ShortenResponse:
    """Create a new short URL."""
    # Rate-limit per IP before doing any DB work.
    client_ip = get_client_ip(request)
    limiter = get_rate_limiter(cache)
    try:
        await limiter.check(client_ip)
    except RateLimitExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
            headers={"Retry-After": str(e.retry_after)},
        )

    try:
        url = await service.create_short_url(
            original_url=str(payload.original_url),
            custom_alias=payload.custom_alias,
            expires_in_seconds=payload.expires_in_seconds(),
        )
    except InvalidURLError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InvalidAliasError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AliasTakenError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return ShortenResponse(
        short_id=url.short_id,
        short_url=f"{settings.BASE_URL.rstrip('/')}/{url.short_id}",
        original_url=url.original_url,
        custom_alias=url.custom_alias,
        created_at=url.created_at,
        expires_at=url.expires_at,
    )


@router.get(
    "/analytics/{short_id}",
    response_model=URLAnalytics,
    responses={404: {"description": "Short URL not found"}},
)
async def analytics(
    short_id: str,
    service: URLService = Depends(get_url_service),
) -> URLAnalytics:
    """Return click-count and timestamps for a short link."""
    try:
        url = await service.get_analytics(short_id)
    except URLNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return URLAnalytics(
        short_id=url.short_id,
        original_url=url.original_url,
        click_count=url.click_count,
        created_at=url.created_at,
        last_accessed_at=url.last_accessed_at,
        expires_at=url.expires_at,
        is_expired=url.is_expired(),
    )
