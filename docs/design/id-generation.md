# Short ID Generation — Design Notes

> Why SnapIt uses 7-character Base62 IDs with collision retry instead of
> Snowflake, UUIDs, or sequential IDs.

## Context

The URL shortener needs identifiers for short URLs. These IDs become the
user-facing slug after the domain — e.g. `https://snpt.is/AbCdE12`. The
constraints:

| Requirement | Why it matters |
|---|---|
| **Compact** | Shorter URLs are the whole point of the product. |
| **Collision-safe** | Two different long URLs must never map to the same short ID. |
| **Concurrency-safe** | Two simultaneous shorten requests must not race onto the same ID. |
| **URL-safe** | The ID goes in a URL path segment — no special characters. |
| **Unpredictable** | Guessing one ID shouldn't easily reveal others. |

## Decision

Use **7-character Base62 IDs generated with `secrets.choice()`**, with a
small in-app retry loop and a Postgres `UNIQUE` constraint as the source
of truth for race-safety.

Implementation:
- Alphabet: `[a-zA-Z0-9]` — 62 characters
- Length: 7 → keyspace ≈ 62⁷ ≈ **3.5 trillion** IDs
- Generator: `secrets.choice()` (cryptographically random, not predictable)
- Race-safety: app pre-checks for nicer UX, but the DB unique index is the
  ground truth; `IntegrityError` triggers a single regenerate + retry.

## Alternatives considered

### Base62 random (chosen) 

```text
Example IDs:   AbCdE12   xY3kQp7   m9NpQrS
Keyspace:      62⁷  ≈ 3.5T
Per-write cost: 1 INSERT (+ rare retry on collision)
```

**Pros:** short, URL-safe, unpredictable, no coordination required.
**Cons:** requires retry-on-collision (essentially never triggered at
our scale — birthday-paradox math says collisions become a measurable
risk only around 60M+ existing IDs).

### UUID v4

```text
Example ID:    f47ac10b-58cc-4372-a567-0e02b2c3d479
Length:        36 chars
Keyspace:      2¹²² ≈ 5.3 × 10³⁶
```

**Pros:** virtually zero collision risk; standardized.
**Cons:** **5× longer than our Base62 IDs**. Visually ugly. Users dislike
them. Forces URL-escaping in some contexts (hyphens are URL-safe but tools
sometimes split on them). Defeats the entire purpose of a "short" URL.

### Snowflake IDs

```text
Example ID (encoded): 1Ldz4mNqA9X  (~11 chars)
Format:               64-bit int → Base62
Components:           41-bit timestamp + 10-bit machine ID + 12-bit sequence
```

**Pros:** monotonically increasing (good for DB B-tree locality);
distributed-ready; widely understood.
**Cons:**
- **Requires machine-ID coordination** — single replica is fine, but
  scaling to N writers needs a coordination service (ZooKeeper, etcd,
  or static config).
- **Clock-skew handling** is non-trivial; clocks moving backward generate
  duplicate IDs.
- **Monotonic ordering enables enumeration** — `/aaaaaab` and `/aaaaaac`
  are likely valid IDs, revealing your URL inventory.
- **~11 chars vs our 7** — Snowflake's compactness advantage over UUIDs
  doesn't translate to an advantage over our shorter Base62 random IDs.
- The distributed-systems benefits Snowflake provides (multi-region
  monotonic ordering, partitioning hints) don't apply at SnapIt's scale.

### DB auto-increment + Base62 encode

```text
Example IDs:   a, b, c, ..., aa, ab, ..., aaa, ...
```

**Pros:** shortest possible IDs; trivial to generate.
**Cons:**
- **Enumeration attack:** trivially iterate `/a`, `/b`, `/c` to discover
  other links. Catastrophic for any private URL.
- **Sequence advancement is a write hotspot** — every shorten requires
  the DB to allocate the next sequence value, serializing all writes.
- **URL count is publicly inferable** — anyone seeing your latest ID
  knows your total URL count. Some businesses consider this leakage.

### Deterministic hash of original URL

```text
Hash: sha256("https://example.com/...")[:7]
```

**Pros:** same input always produces same short ID (idempotent).
**Cons:**
- Custom aliases break — two users wanting different aliases for the same
  underlying URL conflict.
- Hash collisions still need handling, adding the same retry loop we'd
  have anyway.
- Idempotent shortening isn't actually a feature users ask for; if
  someone shortens `example.com` twice, they often *want* two different
  short IDs (different campaigns, different expirations).

## Why Base62 wins for SnapIt

| Criterion | Base62 (7 chars) | UUID v4 | Snowflake | Auto-inc + B62 |
|---|---|---|---|---|
| URL length | ✅ 7 chars | ❌ 36 chars | ⚠️ ~11 chars | ✅ 1-N chars |
| URL-safe | ✅ | ✅ | ✅ | ✅ |
| Collision-safe at scale | ✅ 3.5T keyspace | ✅ | ✅ | ✅ |
| Concurrency-safe | ✅ DB unique idx | ✅ | ✅ | ⚠️ Hotspot |
| Resists enumeration | ✅ Random | ✅ Random | ❌ Sequential | ❌ Sequential |
| No coordination needed | ✅ | ✅ | ❌ Machine IDs | ✅ |
| No PII / sensitive leak | ✅ | ✅ | ⚠️ Time leak | ❌ Count leak |

## Concurrency safety in practice

Two parallel `POST /api/shorten` requests *could* theoretically generate
the same Base62 ID. The probability for a fresh request given N existing
IDs is roughly `N / 62⁷`. Even at 1 million existing URLs, that's a 1 in
3.5 million chance per request — and we still handle the collision
gracefully:

1. Request A and Request B both call `generate_short_id(7)` and happen
   to get the same value.
2. Both attempt `INSERT INTO urls(short_id, original_url, ...)`.
3. The first commit succeeds; the second raises `IntegrityError` because
   of the Postgres unique index on `short_id`.
4. The handler catches the `IntegrityError`, generates a fresh ID with
   `_generate_unique_short_id()`, and retries the INSERT once.

The pattern is: **the database is the ground truth, not the application**.
The pre-check (`SELECT WHERE short_id = ...`) is a UX optimization — it
lets us return a friendly 409 error instead of a 500 — but the actual
race guarantee comes from the DB's atomic constraint enforcement.

This means a future migration to multi-region writes wouldn't break
anything: Postgres replication still enforces uniqueness, the retry loop
still works, no extra coordination needed.

## When we'd revisit this decision

Three scenarios that would justify rethinking:

| Trigger | Likely new choice | Reason |
|---|---|---|
| 100M+ existing URLs | 8- or 9-char Base62 | Collision retry rate becomes measurable. |
| Multi-region writes | KSUID or Snowflake | Need globally-monotonic ordering for downstream sharding. |
| Compliance need: provable randomness | UUID v4 | Some auditors require a standardized random format. |

At SnapIt's current scale (~thousands of URLs, single-region deployment),
none of these apply. Base62-with-retry is **provably the simplest
correct choice** — and "simplest correct" is the right default in
production engineering.

## References in the codebase

- [`app/core/utils.py:generate_short_id`](../../backend/app/core/utils.py) — the random generator
- [`app/services/url_service.py:_generate_unique_short_id`](../../backend/app/services/url_service.py) — the retry loop
- [`app/models/url.py`](../../backend/app/models/url.py) — the `UNIQUE` constraint on `short_id`
