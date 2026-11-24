# Accounts, link history, and pause/resume — roadmap

## Goal
Let people who want it sign in (Google or username + password) and see every
link they created, so a lost short link can be found again. Pause/resume per
link. **Accounts are strictly optional** — anonymous shortening works exactly
as before.

## Design decisions
| Topic | Decision | Why |
| :--- | :--- | :--- |
| Anonymous use | `POST /api/shorten` stays open; auth header optional | Core flow must not change |
| Ownership | nullable `urls.user_id`; set only if a valid token is sent | Old links stay valid and ownerless |
| Password hashing | stdlib `scrypt` + per-user salt | No native deps on Render free tier |
| Session | Signed JWT (HS256, 30 days) sent as `Authorization: Bearer` | Frontend (Netlify) and API (Render) are different origins; avoids cross-site cookie issues |
| Google sign-in | Google Identity Services button → ID token → backend verifies via Google `tokeninfo`, checks `aud` | No client secret, no redirect flow |
| Pause | `urls.is_active` boolean; redirect returns **403** when paused | Reversible, distinct from 410 (expired) |
| Cache | Pausing/resuming deletes the Redis entry; `resolve()` never caches a paused link | Redirect hot path reads Redis first, so stale cache would keep a paused link alive |
| Schema changes | Idempotent `ALTER TABLE … ADD COLUMN IF NOT EXISTS` at startup | Prod DB already has `urls`; `create_all` won't add columns |
| Supabase RLS | `ENABLE ROW LEVEL SECURITY` on `users` at startup | Otherwise the public anon key could read password hashes via Supabase's REST API |

## Phases
1. **Backend data layer** — `User` model; `urls.user_id`, `urls.is_active`; startup migration + RLS.
2. **Auth** — `/api/auth/register`, `/login`, `/google`, `/me`; JWT + password utils; login rate limit.
3. **History + pause/resume** — `GET /api/me/links`, `PATCH /api/links/{short_id}` (owner only); redirect honours `is_active`; shorten attaches owner.
4. **Tests** — register/login, Google (mocked), ownership, anonymous still works, pause → 403 even when cached, resume → 302.
5. **Frontend** — shared `Layout` (nav + background, same theme), `AuthContext`, `/login` page, `/history` page with pause/resume toggles, nav shows Sign in / account menu; shortener sends token if signed in.
6. **Docs/config** — env vars (`JWT_SECRET`, `GOOGLE_CLIENT_ID` (backend only — the frontend fetches it from `/api/auth/config`)), README.

## Out of scope (for now)
Password reset by email, email verification, deleting links, claiming old
anonymous links.
