# Python Web API Standards (FastAPI / Uvicorn / psycopg)

Companion reference for the senior-engineering-partner skill.


The house API stack is **FastAPI + Uvicorn (ASGI) + psycopg3 pool**, deployed as a single container on **Cloud Run** (cross-ref `gcp.md` and `containers-and-orchestration.md`). The the example SaaS `api/` package is the reference implementation — its patterns below are the standard, not a suggestion. The governing principle: **tenant isolation is enforced by the database on every query (RLS), never re-implemented per handler.** A handler that hand-rolls a `WHERE company_id = …` filter is a bug waiting to leak across tenants.

## Application structure & lifecycle

- **Init shared state in a `lifespan` async context manager, not `@app.on_event`.** `on_event("startup"/"shutdown")` is deprecated. Open the connection pool and build the auth verifier once, in `lifespan`, store them on `app.state`, and close the pool in the `finally`:
  ```python
  @asynccontextmanager
  async def lifespan(app: FastAPI) -> AsyncIterator[None]:
      config = Config.from_env()
      app.state.config = config
      app.state.verifier = build_verifier(config)
      pool = create_pool(config); await pool.open()
      app.state.pool = pool
      try: yield
      finally: await pool.close()
  ```
  The `finally` is your **graceful-shutdown** hook: Cloud Run sends **`SIGTERM`** before evicting an instance (with a termination grace window — verify the current default), and the ASGI server (uvicorn) stops accepting new connections and translates it into the `lifespan` shutdown so in-flight requests drain and the pool closes cleanly. Don't `kill -9` your own workers or skip the close — an abrupt exit drops in-flight requests and leaks pool connections. A **Cloud Run Job / background worker** needs the same: trap `SIGTERM`, stop pulling new work, finish or checkpoint the current item, exit 0.
- **Never block the event loop.** FastAPI runs handlers on one async event loop per worker; a **synchronous or CPU-bound call inside an `async def`** (a blocking `requests.get`, a heavy parse, `time.sleep`, a sync DB driver) stalls *every* concurrent request on that worker's event loop, not just its own — and with uvicorn's default single worker (the Cloud Run deployment below), that is the whole instance. Push blocking I/O to `await asyncio.to_thread(...)`/`run_in_executor`, use async clients (the async psycopg pool above, `httpx.AsyncClient`), and offload genuinely heavy/long work (file extraction) to a **Cloud Run Job** off the request path (`scalability-and-system-design.md`). If a route must be sync, define it with `def` (not `async def`) so Starlette runs it in a threadpool instead of on the loop — mixing a blocking call into an `async def` is the trap.
- **One app, JSON-only, thin handlers.** Handlers validate input (Pydantic), acquire an RLS-scoped transaction (one dependency), run their queries, return a Pydantic response model. Business rules that touch multiple tenants or bypass RLS live in `SECURITY DEFINER` SQL functions (`app.onboard_user`, `app.resolve_session`) — see `databases.md` — never in Python that re-grants itself broad DB rights.
- **A `GET /health` liveness endpoint, unauthenticated**, returning `{"status": "ok"}`. Cloud Run and any uptime check hit it; it must not touch the database (a DB blip should not fail liveness and trigger a restart storm). If you want a readiness check that *does* probe the DB, make it a separate path.

## Input validation — Pydantic at the boundary

- **Every request body is a Pydantic `BaseModel` with field constraints.** Validation happens before your handler runs; malformed input returns 422 automatically. Constrain strings and enums explicitly:
  ```python
  class OnboardRequest(BaseModel):
      company_name: str = Field(min_length=1, max_length=200)
      type: Literal["individual", "company"] = "company"
  ```
- **Bound every string (`max_length`) and enumerate every choice (`Literal`).** An unbounded `str` is a DoS vector (multi-MB field) and a downstream-injection risk. Numbers get `ge`/`le`. This is the API-layer mirror of SKILL.md's "validate all inputs at system boundaries."
- **Never accept the tenant id from the client.** `company_id`/`user_id` come from the verified token → resolved session → RLS GUCs, *never* from the request body or a query param. A client-supplied tenant id is the classic broken-access-control hole (OWASP A01 — cross-ref `compliance.md`).

## Authentication & authorization — one dependency, DB-enforced

- **Auth is a FastAPI `Depends()`, not per-handler code.** Two dependencies: `require_token` (verified identity only — for onboarding, before any membership exists) and `require_session` (verified identity **+** an RLS-scoped DB transaction). A handler that takes `session: Session = Depends(require_session)` literally cannot run without tenant scoping.
- **Verify bearer tokens behind a `Protocol`, with a prod and a dev implementation:**
  - `FirebaseVerifier` (production) — verifies a real Firebase ID token via `firebase-admin` (lazy-initialized so the dep stays out of dev/test import paths).
  - `DevTokenVerifier` (local/test) — verifies a locally-minted HS256 JWT (`PyJWT`), so the dev stack and the test harness need **no Firebase project**. `mint_dev_token()` issues one.
  - `build_verifier(config)` selects by `AUTH_MODE`. **Production must FAIL CLOSED on dev mode, not just warn.** The `DevTokenVerifier` is a tenant-forgery backdoor — one leaked `DEV_AUTH_SECRET` mints a valid token for *any* tenant. A loud log `WARNING` is not a control: the config must **raise at startup** when `AUTH_MODE=dev` and a production signal is present (on Cloud Run, `K_SERVICE` is always set), so a misconfigured prod process refuses to boot rather than serving the backdoor. CI-safe — the local/test harness never sets `K_SERVICE` — and it gets its own test (dev mode + `K_SERVICE` ⇒ raises).
- **Return generic auth errors; log the specific reason.** A failed verify returns `401 "invalid or expired token"`; the actual cause (expired, wrong signature, malformed) is logged at INFO, never returned. Leaking *why* a token failed helps an attacker.
- **A missing/malformed `Authorization: Bearer …` header is a 401 before any verify call** — partition the header, check the scheme is `bearer`, reject empties.

## The tenant-isolation pipeline (token → session GUCs → RLS)

This is the spine of the multi-tenant build. Every authenticated request:
1. **Verify** the bearer token → `firebase_uid` (+ email). Trust only what the token proves.
2. **Resolve** `firebase_uid → (user_id, company_ids)` via `app.resolve_session` (a `SECURITY DEFINER` function — necessary because, with no GUCs set yet, the role is in RLS default-deny and cannot read `users`/`memberships` directly). No onboarded user → **403** (distinct from the 401 of a bad token).
3. **Drop role + set identity GUCs** inside one transaction: `SET LOCAL ROLE app_api`, then `set_config('app.current_user_id', …, true)` and `set_config('app.current_company_ids', …, true)`. The `true` = `SET LOCAL`, so **both clear at COMMIT/ROLLBACK** — a pooled connection can never leak one request's identity into the next.
4. **Run handler queries** on that connection. RLS policies read the GUCs and scope every row; the transaction commits on clean exit, rolls back on any raised exception.

The DB-side policies, the GUC accessor functions, and the `SECURITY DEFINER` resolver are owned by `databases.md` — this reference owns the *application half* (the dependency, the verify, the role-drop). Keep them in sync.

## Connection pooling & roles

- **`psycopg_pool.AsyncConnectionPool`, opened in `lifespan`, sized from env** (`DB_POOL_MIN`/`DB_POOL_MAX`, validated `1 ≤ min ≤ max`). On Cloud Run, size for per-instance concurrency, not total — each instance has its own pool (cross-ref `gcp.md` Cloud Run concurrency).
- **`SET LOCAL ROLE` cannot be parameterized** (it's an identifier, not a value). Allowlist the role to code-controlled constants and quote it with `psycopg.sql.Identifier` — never f-string a role name in:
  ```python
  _ALLOWED_ROLES = frozenset({"app_api", "app_worker"})
  if role not in _ALLOWED_ROLES: raise ValueError(...)
  await conn.execute(sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier(role)))
  ```
- **The connecting (login) role is not the query role.** Connect as a principal that can merely *assume* `app_api`; every request drops to it. The login role is never the table owner doing un-scoped reads.

## Configuration — twelve-factor, fail-fast

- **Every value from the environment, validated at startup, into a frozen dataclass.** `Config.from_env()` raises `ConfigError` on a missing `DATABASE_URL`, a bad `AUTH_MODE`, a `dev` mode with no `DEV_AUTH_SECRET`, or non-integer pool sizes — the process refuses to start misconfigured rather than failing the first request.
- **Secrets via `op run --env-file=.op-env` locally (1Password), Cloud Run env + Secret Manager in cloud.** Never hardcoded, never logged. Log the *resolved posture* (`auth_mode`, pool size) but never the connection string or any secret.

## API surface hygiene

- **Disable the public OpenAPI/Swagger UI in production** unless you deliberately publish it: `FastAPI(docs_url=None, redoc_url=None)`. An open `/docs` hands an attacker your entire schema and every parameter.
- **CORS: allowlist explicit origins, never `allow_origins=["*"]` with credentials.** A wildcard + `allow_credentials=True` is rejected by browsers and is a CSRF-adjacent misconfiguration; name the exact frontend origins.
- **Cap request body size** (a reverse proxy / Cloud Run setting or middleware) — an unbounded upload is a memory-exhaustion DoS. For the file-ingestion endpoints, also see `secure-data-processing.md`.
- **Rate-limit per authenticated principal** (and per-IP for unauthenticated routes). A commercial API without rate limiting is a billing-runaway and DoS surface.
- **Structured logging via `logging`, INFO default, no secrets** (SKILL.md logging standard). Log auth outcomes, onboarding, and per-request identity (`user`, `company`) — they are your SOC 2 access-audit trail (cross-ref `compliance.md`).

## QA & quality gates

- **A schema/contract test per endpoint** — assert status codes (201 on create, 401/403/422 on the failure paths), and that the response validates against the Pydantic response model. FastAPI's `TestClient`/`httpx.AsyncClient` drives them.
- **Pin dependencies** in a dedicated `requirements-api.txt` (separate from the CLI engine's `requirements.txt`); install with the pinned set, `bandit` over `api/`, and the API integration gate in CI (cross-ref `github-actions.md`).
- **The dev-token verifier is what makes auth testable** without a Firebase project: tests mint an HS256 token, drive the real HTTP API, and assert the auth→session→RLS pipeline end to end.

## Test cases (what to test and how)

- **Tenant isolation over HTTP (the test you cannot skip):** onboard two tenants, mint a token for each, and assert tenant A's token cannot read or write tenant B's rows through the real API — proving the auth→GUC→RLS pipeline, not just the SQL policies. (`tests_api/test_isolation.py` is the model; the SQL-level twin lives in `databases.md`/pgTAP.)
- **The 401 vs 403 boundary:** bad/expired/missing token → 401; valid token for a user who never onboarded → 403. They are different failures and clients branch on them.
- **Validation rejects:** over-length strings, missing required fields, bad enum values → 422; assert the handler never ran.
- **Fail-closed on a vanished row:** a session that resolves to a real user whose row was deleted mid-request returns 500 (fail closed), not an empty 200 — test it.
- **Config validation:** each missing/invalid env var raises `ConfigError` at startup (positive and negative cases).

## Security testing

- **Authorization tests are security tests** — every cross-tenant read/write attempt must be denied; treat a passing cross-tenant test as a release blocker.
- **Assert `AUTH_MODE=dev` is impossible in prod:** a config/deploy test that the production environment sets `firebase` and that `dev` mode is loud and refused where it matters.
- **`bandit` over `api/`** in CI (HIGH/MEDIUM gate; document any accepted skip with the reason, as the engine CI does for B310/B108).
- **Dependency + supply-chain scanning** on `requirements-api.txt` (cross-ref `compliance.md` A06/A03:2025); `fastapi`/`uvicorn`/`psycopg`/`firebase-admin`/`PyJWT` are all attack-surface — keep them patched.
- **Verify the JWT properly:** algorithm pinned (HS256 only for dev; Firebase verifies RS256 with rotating Google public keys), signature + expiry checked, `sub`/`email` claims required. Never accept `alg: none`; never trust an unverified claim.

## Deploying on Cloud Run

- **One image, `$PORT`-aware, non-root** (cross-ref `containers-and-orchestration.md` + `gcp.md`): `CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-8080}`. The same image runs under docker-compose locally and on Cloud Run.
- **Secrets mounted from Secret Manager**, dedicated least-privilege runtime service account, `min-instances` tuned against cold-start vs cost, request-auth on unless a route is deliberately public (`/health`). See `gcp.md` Cloud Run.
