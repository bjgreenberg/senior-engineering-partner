# Caching Strategy

Companion reference for the senior-engineering-partner skill.


`observability-and-incident-response.md` *measures* latency; this is the caching layer that *reduces* it — without breaking correctness or, the make-or-break for this product, tenant isolation. **The cardinal rule: never cache tenant-scoped data in a shared cache — a mis-scoped cache is a cross-tenant leak, the exact breach RLS exists to prevent** (`databases.md`, `secure-data-processing.md` §3). Worked example: the example multi-tenant SaaS already uses the **Anthropic prompt cache** (`cache_control: ephemeral`) to cut repeat-input cost; HTTP/CDN/query caching are the additions. Cross-ref `python-web-apis.md` (where cache headers/keys are set), `gcp.md` (Cloud CDN), `databases.md` (query caching / materialized views), `secure-data-processing.md` (prompt cache as cost control), `threat-modeling-and-api-design.md` (a cache is an attack + leak surface), `data-protection.md` (don't cache PII past its retention).

The governing rule: **every cache entry's key must encode *who is allowed to see it*, and every cached value must have a defined invalidation. A cache without a tenant-scoped key or an invalidation story is a latent leak or a stale-data bug.** *Verify exact cache-header semantics, CDN flags, and library APIs against current docs; the principles are durable.*

---

## 1. The cardinal rule: isolation before performance
- **Tenant identity is part of the cache key, always** — or the resource is not cached in a shared store at all. The first request warms the cache; the second tenant must never receive the first tenant's cached response. This is RLS's twin: the DB scopes rows, the cache must scope entries.
- **Safe to cache freely:** genuinely public, identical-for-everyone assets (the SPA bundle, static images, public marketing pages). **Cache with the tenant in the key:** anything derived from tenant data. **Don't cache in a shared layer at all:** auth/session responses, signed URLs, PII-bearing payloads (§4).
- **A per-object signed URL is already its own access control** — caching the *object* by its content path is fine; caching the *signed URL string* past its expiry hands out an expired (or worse, still-valid-to-the-wrong-person) credential (§4).

---

## 2. The cache layers (pick deliberately; each has a different blast radius)
| Layer | Use for | Key discipline |
|---|---|---|
| **Browser / HTTP** | static assets, cacheable GETs | `Cache-Control` (`private` vs `public`, `max-age`, `no-store` for sensitive), `ETag`/`Last-Modified` for revalidation; **`private`/`no-store` on anything tenant-scoped** so a shared proxy/CDN never holds it |
| **CDN** (Cloud CDN) | the SPA + truly public assets | never front tenant-scoped responses with a shared-key CDN; respect `private`/`Vary`; cache static, authenticate dynamic |
| **App / query cache** (in-process or shared store) | expensive repeat reads | tenant-scoped key; bounded size + TTL; a shared store (Redis/Memcached) needs the tenant in the key *and* network/ACL isolation |
| **LLM prompt cache** (`cache_control: ephemeral`) | repeated system-prompt/input tokens | already in use for cost (`secure-data-processing.md`); cache the *stable* prompt prefix, never let one tenant's content seed another's cache entry |

- **In-process cache on Cloud Run is per-instance and dies on scale-to-zero** — fine for hot read-mostly data, useless as a source of truth, and *not* shared across instances (so it can't leak across instances, but also can't be invalidated across them — §3).

---

## 3. Invalidation (the genuinely hard part — have a strategy, not a hope)
- **Every cached value needs a defined invalidation:** a TTL (time-bounded staleness you've accepted), explicit bust-on-write (invalidate/replace the entry in the same path that mutates the data), or revalidation (`ETag` → `304`). "It'll expire eventually" with no bound is how stale data becomes a correctness bug.
- **Write-through or bust-on-write for data that must be fresh** (e.g. a matter's state after an edit); TTL-only for data where bounded staleness is acceptable (e.g. an aggregate dashboard).
- **Distributed invalidation is hard** — a per-instance in-process cache can't be invalidated fleet-wide on Cloud Run; if you need cross-instance freshness, use a shared cache with explicit invalidation or keep TTLs short. Name the tradeoff; don't pretend the in-process cache is coherent.
- **Cache stampede:** when a hot entry expires, many requests can hammer the origin at once — use a short lock / single-flight or jittered TTLs for expensive recomputations.

---

## 4. What NOT to cache
- **Auth/session responses, tokens, and signed URLs** beyond their intended lifetime — caching a credential is handing it out (`secrets-and-key-rotation.md`, `frontend-web-security.md`).
- **PII / evidence in any layer that outlives its retention** (`data-protection.md`) — a cache is data-at-rest; a cached PII payload in a shared store is the same exposure as a logged one.
- **Tenant-scoped data in a shared-key cache** — the cardinal rule (§1). When unsure whether a response is tenant-scoped, treat it as `private`/`no-store`.
- **Error responses, indefinitely** — negative caching is useful but bounded; caching a transient 5xx as if permanent breaks recovery.

---

## QA, testing & checklist
- **Cross-tenant cache test (un-skippable):** prime the cache as tenant A, request the same resource as tenant B, assert B gets B's data (or a miss) — never A's. This is the cache-layer twin of the RLS isolation test (`testing.md` §2); a cache bug bypasses RLS entirely.
- **Header assertions in CI:** tenant-scoped responses carry `Cache-Control: private`/`no-store`; static assets carry the intended `public, max-age=...`; `Vary` is correct.
- **Invalidation test:** mutate the underlying data, assert the next read reflects it within the documented bound (no indefinite staleness).
- Pre-merge checklist:
  - [ ] Every cached tenant-scoped entry has the tenant in its key; nothing tenant-scoped sits in a shared-key cache or CDN.
  - [ ] Every cached value has a defined invalidation (TTL, bust-on-write, or revalidation).
  - [ ] No tokens/signed-URLs/PII cached beyond their lifetime; sensitive responses are `private`/`no-store`.
  - [ ] Cross-tenant cache isolation test present and green.

### Cross-references
- Where cache headers/keys and CORS are set; the request pipeline — `references/python-web-apis.md`.
- Cloud CDN + asset serving — `references/gcp.md`; query caching / materialized views — `references/databases.md`.
- The prompt cache as a cost control — `references/secure-data-processing.md` §2; cost/latency metrics — `references/observability-and-incident-response.md`.
- A cache as an attack/leak surface — `references/threat-modeling-and-api-design.md`; never cache PII past retention — `references/data-protection.md`.
- The tenant boundary RLS enforces (the same boundary the cache must respect) — `references/databases.md`. The cross-tenant isolation test pattern — `references/testing.md`.
