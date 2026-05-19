"""
End-to-end API tests.

Covers:
- Basic shorten + redirect
- Custom alias success + collision
- Invalid URL rejection
- Invalid alias rejection
- Expired link returns 410
- Analytics increments click count
"""
import asyncio

import pytest


pytestmark = pytest.mark.asyncio


async def test_shorten_and_redirect(app_client):
    resp = await app_client.post(
        "/api/shorten",
        json={"original_url": "https://example.com/long/path"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["short_id"]
    assert body["short_url"].endswith(body["short_id"])
    assert body["original_url"] == "https://example.com/long/path"

    # Redirect should 302 to the original.
    short_id = body["short_id"]
    r2 = await app_client.get(f"/{short_id}", follow_redirects=False)
    assert r2.status_code == 302
    assert r2.headers["location"] == "https://example.com/long/path"


async def test_custom_alias(app_client):
    resp = await app_client.post(
        "/api/shorten",
        json={"original_url": "https://example.com", "custom_alias": "my-link"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["short_id"] == "my-link"

    # Redirect via alias.
    r2 = await app_client.get("/my-link", follow_redirects=False)
    assert r2.status_code == 302


async def test_duplicate_alias_rejected(app_client):
    payload = {"original_url": "https://example.com", "custom_alias": "dupe"}
    r1 = await app_client.post("/api/shorten", json=payload)
    assert r1.status_code == 201
    r2 = await app_client.post(
        "/api/shorten",
        json={"original_url": "https://other.com", "custom_alias": "dupe"},
    )
    assert r2.status_code == 409


async def test_invalid_url(app_client):
    resp = await app_client.post(
        "/api/shorten",
        json={"original_url": "not-a-url"},
    )
    # Pydantic HttpUrl → 422 before our handler; acceptable.
    assert resp.status_code in (400, 422)


async def test_reserved_alias_rejected(app_client):
    resp = await app_client.post(
        "/api/shorten",
        json={"original_url": "https://example.com", "custom_alias": "api"},
    )
    assert resp.status_code == 400


async def test_short_alias_rejected(app_client):
    resp = await app_client.post(
        "/api/shorten",
        json={"original_url": "https://example.com", "custom_alias": "ab"},
    )
    # Pydantic min_length=3 catches this as 422.
    assert resp.status_code in (400, 422)


async def test_expired_link_returns_410(app_client):
    # Create a link with expires_in_days=1, then manipulate the DB record
    # to make it expired.
    resp = await app_client.post(
        "/api/shorten",
        json={"original_url": "https://example.com", "expires_in_days": 1},
    )
    assert resp.status_code == 201
    short_id = resp.json()["short_id"]

    from datetime import datetime, timedelta, timezone
    from sqlalchemy import update
    from app.db.database import AsyncSessionLocal
    from app.models.url import URL
    from app.services.cache import cache

    async with AsyncSessionLocal() as session:
        await session.execute(
            update(URL)
            .where(URL.short_id == short_id)
            .values(expires_at=datetime.now(timezone.utc) - timedelta(days=1))
        )
        await session.commit()

    # Invalidate cached copy so the DB path runs.
    await cache.delete_url(short_id)

    r2 = await app_client.get(f"/{short_id}", follow_redirects=False)
    assert r2.status_code == 410


async def test_not_found(app_client):
    r = await app_client.get("/does-not-exist-xyz", follow_redirects=False)
    assert r.status_code == 404


async def test_expires_in_minutes(app_client):
    """New API: value + unit lets us pick minutes, hours, or days."""
    resp = await app_client.post(
        "/api/shorten",
        json={
            "original_url": "https://example.com",
            "expires_in_value": 30,
            "expires_in_unit": "minutes",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["expires_at"] is not None

    # Sanity: the expires_at should be between now and now+60min.
    from datetime import datetime, timezone, timedelta
    expires_at = datetime.fromisoformat(body["expires_at"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    assert timedelta(minutes=25) <= (expires_at - now) <= timedelta(minutes=35)


async def test_expires_in_hours(app_client):
    resp = await app_client.post(
        "/api/shorten",
        json={
            "original_url": "https://example.com",
            "expires_in_value": 6,
            "expires_in_unit": "hours",
        },
    )
    assert resp.status_code == 201, resp.text
    from datetime import datetime, timezone, timedelta
    expires_at = datetime.fromisoformat(resp.json()["expires_at"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    assert timedelta(hours=5, minutes=55) <= (expires_at - now) <= timedelta(hours=6, minutes=5)


async def test_legacy_expires_in_days_still_works(app_client):
    """Backwards-compat: old clients sending expires_in_days must keep working."""
    resp = await app_client.post(
        "/api/shorten",
        json={"original_url": "https://example.com", "expires_in_days": 2},
    )
    assert resp.status_code == 201, resp.text
    from datetime import datetime, timezone, timedelta
    expires_at = datetime.fromisoformat(resp.json()["expires_at"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    assert timedelta(days=1, hours=23) <= (expires_at - now) <= timedelta(days=2, hours=1)


async def test_analytics_click_count(app_client):
    resp = await app_client.post(
        "/api/shorten",
        json={"original_url": "https://example.com"},
    )
    short_id = resp.json()["short_id"]

    # Trigger three redirects.
    for _ in range(3):
        await app_client.get(f"/{short_id}", follow_redirects=False)

    # BackgroundTasks run after the response — give them a beat.
    await asyncio.sleep(0.2)

    a = await app_client.get(f"/api/analytics/{short_id}")
    assert a.status_code == 200
    body = a.json()
    assert body["click_count"] >= 1  # at least one recorded
