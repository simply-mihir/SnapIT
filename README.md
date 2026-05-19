# Scalable URL Shortener

A production-ready URL shortener built with **FastAPI**, **PostgreSQL**, **Redis**, **Next.js**, and **Tailwind CSS** — with caching, rate limiting, analytics, expiration handling, and a clean, minimal UI.

- Low-latency redirects via Redis cache-aside (DB is only touched on miss).
- Custom aliases with race-safe uniqueness enforced at the DB layer.
- Per-IP rate limiting backed by Redis (fixed-window).
- Click-count + last-accessed analytics recorded asynchronously so redirects never block.
- Graceful expiration with HTTP 410.
- Fully containerised with Docker Compose for one-command local dev.

## Project structure

```
url-shortener/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entrypoint + lifespan
│   │   ├── core/                   # config, utils, exceptions
│   │   ├── db/                     # async SQLAlchemy engine + session
│   │   ├── models/                 # ORM models
│   │   ├── schemas/                # Pydantic request/response models
│   │   ├── services/               # cache, rate limiter, url service (business logic)
│   │   └── routes/                 # shorten, redirect, health, deps
│   ├── tests/                      # pytest suite (SQLite + fakeredis)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── pages/                      # _app.js, index.js
│   ├── components/                 # ShortenerForm, ThemeToggle
│   ├── styles/globals.css
│   ├── Dockerfile
│   ├── package.json
│   └── .env.example
├── docker-compose.yml
└── README.md
```

## Architecture

```
Client ──▶ FastAPI ──▶ Redis ──▶ PostgreSQL
                │
                └──▶ Analytics (background task, fire-and-forget)
```

**Redirect flow**

1. `GET /{short_id}` → check Redis.
2. Cache hit → 302 redirect immediately.
3. Cache miss → query Postgres, check `expires_at`, repopulate cache, 302.
4. Click-count + `last_accessed_at` updated via a `BackgroundTask` so the redirect response returns first.

## Database schema

Table `urls`:

| column             | type                      | notes                                    |
|--------------------|---------------------------|------------------------------------------|
| `id`               | bigint, PK, autoincrement |                                          |
| `original_url`     | varchar(2048)             | not null                                 |
| `short_id`         | varchar(64)               | unique, indexed (hot-path lookup)        |
| `custom_alias`     | varchar(64), nullable     | unique, indexed                          |
| `created_at`       | timestamptz               | default now()                            |
| `expires_at`       | timestamptz, nullable     | indexed (for cleanup jobs)               |
| `click_count`      | integer                   | default 0, incremented via atomic UPDATE |
| `last_accessed_at` | timestamptz, nullable     |                                          |

## API

| Method | Path                    | Description                             |
|--------|-------------------------|-----------------------------------------|
| POST   | `/api/shorten`          | Create short URL                        |
| GET    | `/api/analytics/{id}`   | Click-count + timestamps                |
| GET    | `/{short_id}`           | 302 redirect (404 missing, 410 expired) |
| GET    | `/health/live`          | Liveness                                |
| GET    | `/health/ready`         | Readiness (DB + Redis)                  |
| GET    | `/docs`                 | OpenAPI Swagger UI                      |

### POST /api/shorten

```json
{
  "original_url": "https://example.com/very/long/path",
  "custom_alias": "my-link",
  "expires_in_days": 30
}
```

Response `201 Created`:

```json
{
  "short_id": "my-link",
  "short_url": "http://localhost:8000/my-link",
  "original_url": "https://example.com/very/long/path",
  "custom_alias": "my-link",
  "created_at": "2026-04-23T10:15:00Z",
  "expires_at": "2026-05-23T10:15:00Z"
}
```

Errors: `400` invalid URL/alias, `409` alias taken, `429` rate-limited (with `Retry-After` header).

## Local development (Docker Compose)

```bash
cd url-shortener
docker compose up --build
```

- Backend: http://localhost:8000 (Swagger at `/docs`)
- Frontend: http://localhost:3000
- Postgres: `localhost:5432` (postgres/postgres)
- Redis: `localhost:6379`

The backend auto-creates tables on first boot (convenient for dev; use Alembic for migrations in prod).

### Running tests

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install fakeredis
pytest -q
```

The suite swaps Postgres → SQLite (aiosqlite) and Redis → fakeredis, so it runs offline.

## Configuration

All configuration is via environment variables — see `backend/.env.example` and `frontend/.env.example`.

Key knobs:

- `DATABASE_URL` — async SQLAlchemy URL (`postgresql+asyncpg://...`)
- `REDIS_URL` — `redis://...` or `rediss://...` for TLS (Upstash)
- `RATE_LIMIT_MAX_REQUESTS` / `RATE_LIMIT_WINDOW_SECONDS` — per-IP limit on `/api/shorten`
- `CACHE_DEFAULT_TTL` — default Redis TTL for short URLs (seconds)
- `SHORT_ID_LENGTH` — Base62 length (default 7 → 62^7 ≈ 3.5T keyspace)
- `CORS_ORIGINS` — comma-separated list

## Free-tier deployment

### 1) Postgres (Supabase or Railway)

**Supabase**: create project → Settings → Database → copy the "Connection pooling" URL. Replace prefix with `postgresql+asyncpg://` for SQLAlchemy.

**Railway**: New Project → Provision Postgres → Variables → `DATABASE_URL`. Prefix with `postgresql+asyncpg://`.

### 2) Redis (Upstash)

- Create a Redis database at upstash.com (free tier).
- Copy the **TLS (rediss://)** URL from the "Redis" tab.
- Set `REDIS_URL=rediss://default:<password>@<host>:6379`.

### 3) Backend (Render)

- New → Web Service → connect repo → root `backend/`.
- Docker runtime (auto-detects `backend/Dockerfile`).
- Environment variables:
  - `DATABASE_URL` (from Supabase/Railway)
  - `REDIS_URL` (from Upstash)
  - `BASE_URL=https://<your-service>.onrender.com`
  - `CORS_ORIGINS=https://<your-frontend>.vercel.app`
  - `APP_ENV=production`
- Health check path: `/health/ready`.

### 4) Frontend (Vercel)

- Import the repo into Vercel, root `frontend/`.
- Env var: `NEXT_PUBLIC_API_URL=https://<your-backend>.onrender.com`.
- Deploy.

### 5) Custom domain (optional)

Point your domain at the Render backend service if you want short URLs like `https://sho.rt/abc123`. Update `BASE_URL` accordingly.

## Production notes

- The `init_db()` call on startup is a local-dev convenience. For production, use Alembic migrations and remove (or guard) that call.
- For HA, run `uvicorn` with multiple workers behind a reverse proxy, and scale horizontally — all state lives in Postgres + Redis.
- Redis is a shared singleton; for extreme scale, consider Redis Cluster or a regional read replica.
- Consider moving analytics from in-process background tasks to a real queue (RQ, Arq, or SQS/Celery) so a crash doesn't drop click records.
- Add a nightly cleanup job that deletes rows where `expires_at < now() - interval '7 days'`.

## Licence

MIT — do what you want.
## Deployed Link

https://snapit-url-shortener.netlify.app
