"""Schemas for auth + link-history endpoints."""
import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

_USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,31}$")


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def _username(cls, v: str) -> str:
        v = v.strip().lower()
        if not _USERNAME_RE.match(v):
            raise ValueError(
                "Username must be 3-32 chars: letters, digits, '.', '_' or '-'."
            )
        return v


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=320)
    password: str = Field(..., min_length=1, max_length=128)


class GoogleLoginRequest(BaseModel):
    credential: str = Field(..., min_length=10, description="Google ID token (JWT).")


class UserOut(BaseModel):
    id: int
    username: Optional[str] = None
    email: Optional[str] = None
    display_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class LinkOut(BaseModel):
    short_id: str
    short_url: str
    original_url: str
    custom_alias: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    click_count: int
    last_accessed_at: Optional[datetime] = None
    is_active: bool
    is_expired: bool


class LinkListResponse(BaseModel):
    items: list[LinkOut]
    total: int


class LinkUpdateRequest(BaseModel):
    is_active: bool
