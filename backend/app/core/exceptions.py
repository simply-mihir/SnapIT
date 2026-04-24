"""
Domain-specific exceptions. Mapped to HTTP responses at the route layer.
"""


class URLShortenerError(Exception):
    """Base exception for this service."""


class InvalidURLError(URLShortenerError):
    """Raised when the provided URL fails validation."""


class InvalidAliasError(URLShortenerError):
    """Raised when a custom alias is malformed."""


class AliasTakenError(URLShortenerError):
    """Raised when a custom alias is already in use."""


class URLNotFoundError(URLShortenerError):
    """Raised when a short_id has no matching record."""


class URLExpiredError(URLShortenerError):
    """Raised when a short link is past its expires_at."""


class RateLimitExceededError(URLShortenerError):
    """Raised when a client exceeds the configured rate limit."""

    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after}s.")
