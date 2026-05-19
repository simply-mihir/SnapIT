"""
Pydantic v2 request/response schemas for the URL shortener API.
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


ExpiryUnit = Literal["minutes", "hours", "days"]

_UNIT_TO_SECONDS = {
    "minutes": 60,
    "hours": 3600,
    "days": 86400,
}


class ShortenRequest(BaseModel):
    """
    Body for POST /api/shorten.

    Expiration may be specified as either:
      - `expires_in_value` + `expires_in_unit` (new, flexible), or
      - `expires_in_days` (legacy, kept for backward compatibility).

    If both are provided, the (value, unit) pair wins.
    """

    original_url: HttpUrl = Field(..., description="The URL to shorten (http/https only).")
    custom_alias: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=32,
        description="Optional custom slug. 3-32 chars, alphanumeric + - _.",
    )

    # New flexible expiration API
    expires_in_value: Optional[int] = Field(
        default=None,
        ge=1,
        le=525600,  # 1 year in minutes — generous upper bound
        description="How many `expires_in_unit` before the link expires. Omit for no expiration.",
    )
    expires_in_unit: Optional[ExpiryUnit] = Field(
        default=None,
        description="Unit for expires_in_value: 'minutes', 'hours', or 'days'.",
    )

    # Legacy field — still accepted so existing clients don't break.
    expires_in_days: Optional[int] = Field(
        default=None,
        ge=1,
        le=3650,
        description="(Deprecated) Days until the short link expires. Use expires_in_value + expires_in_unit.",
    )

    @model_validator(mode="after")
    def _normalize_expiry(self):
        """
        Normalize to a single canonical (value, unit) pair on the instance.

        If only legacy `expires_in_days` is given, promote it to
        (value=..., unit='days'). If the new fields are given, keep them.
        """
        if self.expires_in_value is not None and self.expires_in_unit is None:
            self.expires_in_unit = "days"
        if self.expires_in_value is None and self.expires_in_days is not None:
            self.expires_in_value = self.expires_in_days
            self.expires_in_unit = "days"
        return self

    def expires_in_seconds(self) -> Optional[int]:
        """
        Effective TTL in seconds, or None for no expiration.
        """
        if self.expires_in_value is None or self.expires_in_unit is None:
            return None
        return self.expires_in_value * _UNIT_TO_SECONDS[self.expires_in_unit]


class ShortenResponse(BaseModel):
    """Response returned after creating a short URL."""

    short_id: str
    short_url: str
    original_url: str
    custom_alias: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class URLAnalytics(BaseModel):
    """Analytics payload for GET /api/analytics/{short_id}."""

    short_id: str
    original_url: str
    click_count: int
    created_at: datetime
    last_accessed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_expired: bool

    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    """Uniform error payload."""

    detail: str
