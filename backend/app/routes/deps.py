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


# ----- Auth dependencies -----

from typing import Optional  # noqa: E402

from fastapi import Header, HTTPException, status  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.core.security import decode_access_token  # noqa: E402
from app.models.user import User  # noqa: E402


async def get_optional_user(
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_session),
) -> Optional[User]:
    """The signed-in user, or None for anonymous callers / bad tokens."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    user_id = decode_access_token(authorization[7:].strip())
    if user_id is None:
        return None
    return (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()


async def get_current_user(user: Optional[User] = Depends(get_optional_user)) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
