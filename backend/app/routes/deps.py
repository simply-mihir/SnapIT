"""
Shared FastAPI dependencies: service factory, client IP extraction.
"""
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.services.cache import CacheClient, get_cache
from app.services.url_service import URLService


async def get_url_service(
    db: AsyncSession = Depends(get_session),
    cache: CacheClient = Depends(get_cache),
) -> URLService:
    return URLService(db=db, cache=cache)


def get_client_ip(request: Request) -> str:
    """
    Determine the caller's IP, respecting common proxy headers.

    When deployed behind a reverse proxy or load balancer, X-Forwarded-For
    contains the true client IP. We take the first (leftmost) entry,
    which is the original client.
    """
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"
