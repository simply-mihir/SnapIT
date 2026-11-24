"""
Accounts, link history, and pause/resume.

Key invariants:
- anonymous shortening is unchanged
- history only shows the caller's own links
- pausing a link blocks redirects immediately, even when cached in Redis
- only the owner can pause/resume
"""
import pytest

pytestmark = pytest.mark.asyncio


async def _register(client, username="alice", password="correct-horse"):
    r = await client.post("/api/auth/register", json={"username": username, "password": password})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_anonymous_shorten_still_works_and_is_ownerless(app_client):
    r = await app_client.post("/api/shorten", json={"original_url": "https://example.com"})
    assert r.status_code == 201
    headers = await _register(app_client)
    hist = await app_client.get("/api/me/links", headers=headers)
    assert hist.json() == {"items": [], "total": 0}


async def test_register_login_me(app_client):
    headers = await _register(app_client, "Bob_1")  # normalized to lowercase
    me = await app_client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200 and me.json()["username"] == "bob_1"

    ok = await app_client.post("/api/auth/login", json={"username": "BOB_1", "password": "correct-horse"})
    assert ok.status_code == 200 and ok.json()["access_token"]

    bad = await app_client.post("/api/auth/login", json={"username": "bob_1", "password": "wrong-pass"})
    assert bad.status_code == 401
    ghost = await app_client.post("/api/auth/login", json={"username": "nobody", "password": "wrong-pass"})
    assert ghost.status_code == 401 and ghost.json() == bad.json()  # no user enumeration


async def test_register_validation_and_duplicate(app_client):
    await _register(app_client, "carol")
    dup = await app_client.post("/api/auth/register", json={"username": "CAROL", "password": "another-pass"})
    assert dup.status_code == 409
    short_pw = await app_client.post("/api/auth/register", json={"username": "dave", "password": "short"})
    assert short_pw.status_code == 422
    bad_name = await app_client.post("/api/auth/register", json={"username": "a b!", "password": "long-enough-pw"})
    assert bad_name.status_code == 422


async def test_protected_endpoints_require_auth(app_client):
    assert (await app_client.get("/api/me/links")).status_code == 401
    assert (await app_client.patch("/api/links/x", json={"is_active": False})).status_code == 401
    bad = {"Authorization": "Bearer not.a.token"}
    assert (await app_client.get("/api/me/links", headers=bad)).status_code == 401


async def test_history_lists_only_own_links(app_client):
    a = await _register(app_client, "alice")
    b = await _register(app_client, "bobby")
    la = (await app_client.post("/api/shorten", json={"original_url": "https://a.example"}, headers=a)).json()
    await app_client.post("/api/shorten", json={"original_url": "https://b.example"}, headers=b)
    await app_client.post("/api/shorten", json={"original_url": "https://anon.example"})

    hist = (await app_client.get("/api/me/links", headers=a)).json()
    assert hist["total"] == 1
    item = hist["items"][0]
    assert item["short_id"] == la["short_id"]
    assert item["is_active"] is True and item["is_expired"] is False
    assert item["short_url"].endswith(la["short_id"])


async def test_pause_blocks_redirect_even_when_cached_then_resume(app_client):
    h = await _register(app_client)
    link = (await app_client.post(
        "/api/shorten", json={"original_url": "https://example.com/x"}, headers=h
    )).json()
    sid = link["short_id"]

    # Warm the cache with a successful redirect first.
    assert (await app_client.get(f"/{sid}", follow_redirects=False)).status_code == 302

    r = await app_client.patch(f"/api/links/{sid}", json={"is_active": False}, headers=h)
    assert r.status_code == 200 and r.json()["is_active"] is False
    assert (await app_client.get(f"/{sid}", follow_redirects=False)).status_code == 403
    # Still paused on repeat (paused links must never be cached).
    assert (await app_client.get(f"/{sid}", follow_redirects=False)).status_code == 403
    hist = (await app_client.get("/api/me/links", headers=h)).json()
    assert hist["items"][0]["is_active"] is False

    r = await app_client.patch(f"/api/links/{sid}", json={"is_active": True}, headers=h)
    assert r.json()["is_active"] is True
    resp = await app_client.get(f"/{sid}", follow_redirects=False)
    assert resp.status_code == 302 and resp.headers["location"] == "https://example.com/x"


async def test_pause_works_for_custom_alias(app_client):
    h = await _register(app_client)
    await app_client.post(
        "/api/shorten",
        json={"original_url": "https://example.com", "custom_alias": "my-pausable"},
        headers=h,
    )
    assert (await app_client.get("/my-pausable", follow_redirects=False)).status_code == 302
    await app_client.patch("/api/links/my-pausable", json={"is_active": False}, headers=h)
    assert (await app_client.get("/my-pausable", follow_redirects=False)).status_code == 403


async def test_only_owner_can_pause(app_client):
    owner = await _register(app_client, "owner1")
    other = await _register(app_client, "other1")
    sid = (await app_client.post(
        "/api/shorten", json={"original_url": "https://example.com"}, headers=owner
    )).json()["short_id"]
    anon_sid = (await app_client.post("/api/shorten", json={"original_url": "https://example.com"})).json()["short_id"]

    assert (await app_client.patch(f"/api/links/{sid}", json={"is_active": False}, headers=other)).status_code == 404
    assert (await app_client.patch(f"/api/links/{anon_sid}", json={"is_active": False}, headers=owner)).status_code == 404
    assert (await app_client.get(f"/{sid}", follow_redirects=False)).status_code == 302


async def test_google_login_disabled_without_client_id(app_client):
    r = await app_client.post("/api/auth/google", json={"credential": "x" * 20})
    assert r.status_code == 401
    cfg = await app_client.get("/api/auth/config")
    assert cfg.json() == {"google_client_id": None}


async def test_google_login_creates_and_reuses_account(app_client, monkeypatch):
    from app.core.config import settings
    from app.services.auth_service import AuthService

    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "client-123")

    async def fake_verify(credential):
        return {"sub": "g-42", "email": "Eve@Example.com", "name": "Eve"}

    monkeypatch.setattr(AuthService, "_verify_google_token", staticmethod(fake_verify))

    r1 = await app_client.post("/api/auth/google", json={"credential": "x" * 20})
    assert r1.status_code == 200, r1.text
    r2 = await app_client.post("/api/auth/google", json={"credential": "x" * 20})
    assert r1.json()["user"]["id"] == r2.json()["user"]["id"]
    assert r1.json()["user"]["email"] == "eve@example.com"
    # Google-only accounts have no password to log in with.
    bad = await app_client.post("/api/auth/login", json={"username": "eve@example.com", "password": "anything-long"})
    assert bad.status_code == 401


async def test_google_token_audience_checked(monkeypatch):
    import httpx
    from app.core.config import settings
    from app.core.exceptions import AuthError
    from app.services.auth_service import AuthService

    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "mine")

    class FakeResp:
        status_code = 200
        def json(self):
            return {"aud": "someone-else", "iss": "accounts.google.com",
                    "email_verified": "true", "sub": "1"}

    class FakeClient:
        def __init__(self, *a, **k): ...
        async def __aenter__(self): return self
        async def __aexit__(self, *a): ...
        async def get(self, *a, **k): return FakeResp()

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    with pytest.raises(AuthError):
        await AuthService._verify_google_token("tok")
