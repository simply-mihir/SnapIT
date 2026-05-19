"""
Utility functions: Base62 encoding, short ID generation, URL validation.
"""
import secrets
import string
from typing import Optional
from urllib.parse import urlparse

import validators

BASE62_ALPHABET = string.ascii_letters + string.digits  # a-zA-Z0-9


def generate_short_id(length: int = 7) -> str:
    """
    Generate a cryptographically secure Base62 random short ID.

    Using secrets.choice avoids the predictability of random.choice and
    gives us ~62^length total namespace (62^7 ≈ 3.5 trillion combinations).
    """
    return "".join(secrets.choice(BASE62_ALPHABET) for _ in range(length))


def is_valid_url(url: str) -> bool:
    """
    Validate a URL's structure and scheme.

    Rejects anything without http(s) scheme to prevent open-redirect
    style abuse via javascript: or data: URIs.
    """
    if not url or len(url) > 2048:
        return False
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if not parsed.netloc:
        return False
    return bool(validators.url(url))


ALIAS_ALLOWED = set(string.ascii_letters + string.digits + "-_")


def is_valid_alias(alias: str) -> bool:
    """
    Custom aliases must be 3-32 chars, alphanumeric + dash/underscore only.
    Reserved words blocked to avoid collisions with API routes.
    """
    if not alias or not (3 <= len(alias) <= 32):
        return False
    if not all(c in ALIAS_ALLOWED for c in alias):
        return False
    reserved = {"api", "shorten", "docs", "redoc", "openapi.json", "health", "admin", "static"}
    if alias.lower() in reserved:
        return False
    return True


def normalize_url(url: str) -> str:
    """Strip whitespace and lowercase the scheme/host for consistency."""
    url = url.strip()
    parsed = urlparse(url)
    return parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
    ).geturl()
