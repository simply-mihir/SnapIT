"""
Optional-account endpoints: register, login, Google login, me.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthError, RateLimitExceededError, UserExistsError
from app.core.security import create_access_token
from app.db.database import get_session
from app.models.user import User
from app.routes.deps import get_client_ip, get_current_user
from app.schemas.auth import (
    AuthResponse,
    GoogleLoginRequest,
    LoginRequest,
    RegisterRequest,
    UserOut,
)
from app.services.auth_service import AuthService
from app.services.cache import CacheClient, get_cache
from app.services.rate_limiter import RateLimiter

router = APIRouter(prefix="/api/auth", tags=["auth"])


async def _limit(request: Request, cache: CacheClient) -> None:
    """Throttle credential attempts per IP (brute-force protection)."""
    limiter = RateLimiter(
        cache=cache,
        max_requests=settings.AUTH_RATE_LIMIT_MAX_REQUESTS,
        window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
    )
    try:
        await limiter.check(f"auth:{get_client_ip(request)}")
    except RateLimitExceededError as e:
        raise HTTPException(
            status_code=429, detail=str(e), headers={"Retry-After": str(e.retry_after)}
        )


def _auth_response(user: User) -> AuthResponse:
    return AuthResponse(
        access_token=create_access_token(user.id),
        user=UserOut.model_validate(user),
    )


@router.get("/config")
async def auth_config() -> dict:
    """Lets the frontend know whether to render the Google button."""
    return {"google_client_id": settings.GOOGLE_CLIENT_ID or None}


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(
    payload: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
    cache: CacheClient = Depends(get_cache),
) -> AuthResponse:
    await _limit(request, cache)
    try:
        user = await AuthService(db).register(payload.username, payload.password)
    except UserExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return _auth_response(user)


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
    cache: CacheClient = Depends(get_cache),
) -> AuthResponse:
    await _limit(request, cache)
    try:
        user = await AuthService(db).login(payload.username, payload.password)
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    return _auth_response(user)


@router.post("/google", response_model=AuthResponse)
async def google_login(
    payload: GoogleLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
    cache: CacheClient = Depends(get_cache),
) -> AuthResponse:
    await _limit(request, cache)
    try:
        user = await AuthService(db).login_with_google(payload.credential)
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    return _auth_response(user)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(user)
