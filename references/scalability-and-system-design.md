# Scalability & System Design (the "-ilities")

Companion reference for the senior-engineering-partner skill.

> **Rigor tier:** statelessness and "don't do slow work in the request" are a **floor for anything multi-instance or user-facing** (they're nearly free and a retrofit is expensive). Queues + DLQ + outbox + load-tested capacity targets are **Tier-1+** where there's real traffic; a Tier-0 spike defers them with a `TODO`. The principle is portable; *verify Cloud Tasks/Pub/Sub/Cloud Run concurrency specifics against current GCP docs.*

Designing a *system*, not just a script: this is the layer SKILL.md's coding standards don't cover — how the thing behaves as load and instance count grow. It pairs with `resilience-engineering.md` (how it degrades when a dependency fails) and `observability-and-incident-response.md` (how you see the ceiling coming). The governing rule: **design for horizontal scale and bounded work from the start — scale-out is cheap only if the code is stateless and slow work is off the request path; retrofitting either under load is a rewrite.** Worked example: the example SaaS is FastAPI on Cloud Run (autoscales by adding instances) → a Cloud Run Job does the heavy extraction → Postgres with a bounded pool.

**Name the loop — the shared design *and* debug lens.** Almost every behaviour here is a feedback loop, and naming which kind you're in is the highest-leverage move. **Balancing loops** stabilize toward a goal and self-correct — autoscaling, backpressure/load-shed, an SLO alert that pulls a sick instance, the rigor ladder itself; you *want* these, and a missing one is why a system has no governor. **Reinforcing loops** compound and self-amplify — a retry storm (failures → more retries → more load → more failures), a cache stampede, debt → slower change → more debt; left alone they run away. The question at every design and `DEBUG:` step: **which loop am I in, and is it self-correcting or self-amplifying?** A self-amplifying loop needs a balancing brake (a cap, a breaker, a flag — `resilience-engineering.md`), not a bigger machine.

---

## 1. Statelessness — the precondition for horizontal scale
- **Hold no per-user state in the process.** Cloud Run (and any autoscaler) runs N interchangeable instances and can kill one any time; an in-memory session, an in-process cache of tenant data, an uploaded file on local disk, or a "current job" variable **breaks the moment a second instance spins up or the first is evicted**. Externalize: sessions/tokens are stateless (the RLS-scoped bearer token — `python-web-apis.md`), shared cache → Redis/Memorystore (tenant-keyed — `caching.md`), uploads → GCS, durable work → the DB/queue.
- **Sticky sessions are a smell, not a fix.** If correctness needs a user to hit the same instance, the state is in the wrong place. The only acceptable local state is a *read-through cache that can be rebuilt from the source of truth* (and even then, tenant-keyed).
- A stateless service scales by changing one number (max instances / concurrency); a stateful one needs a migration to scale at all.

## 2. Get slow work off the request path — queue + worker
- **Synchronous request handlers are for fast, bounded work.** Anything slow, CPU-bound, bursty, or third-party-dependent (file extraction, a model call, a bulk export, sending email) belongs on a **queue + worker**, not in the HTTP handler — both to keep p95 low and so a burst doesn't exhaust request capacity. On GCP: **Cloud Tasks** (HTTP-target task queue, per-queue rate/concurrency control) or **Pub/Sub** (fan-out/event) → a **Cloud Run Job** or a push endpoint.
- **Every queue has a dead-letter queue (DLQ) + a retry policy.** A message that fails N times goes to the DLQ for inspection instead of poison-looping forever or vanishing. Alert on DLQ depth > 0 (`observability-and-incident-response.md`).
- **At-least-once means the consumer MUST be idempotent.** Cloud Tasks/Pub/Sub redeliver — a message *will* sometimes arrive twice. The worker must converge to the same state on a duplicate (an idempotency key / a dedup on `(tenant, job_id)` / an upsert), the same discipline as `resilience-engineering.md` retries and `secrets-and-key-rotation.md` re-wrap. A non-idempotent consumer double-charges or double-writes under normal operation, not just under failure.
- **The transactional outbox** when a DB commit must reliably produce an event: write the event to an `outbox` table *in the same transaction* as the business write, and a relay publishes it — so a crash between "commit" and "publish" can't lose the event (dual-write hazard). Cross-ref the append-only/`usage_events` patterns in `databases.md`/`secure-data-processing.md`.

## 3. Know your scaling ceilings (the failure modes that bite first)
- **The database connection pool is the classic Cloud Run ceiling.** Each instance opens its own pool; `instances × pool_max` can blow past Postgres `max_connections` the moment autoscaling kicks in — presenting as connection-refused under load, not gradual slowdown. Size the per-instance pool for per-instance concurrency, and put a **pooler in front** (PgBouncer / the Supabase/Cloud SQL connection pooler) so the DB sees a bounded connection count regardless of instance count. (Cross-ref `databases.md`, `python-web-apis.md` pool sizing, `gcp.md` Cloud Run concurrency.)
- **N+1 queries** turn one logical request into hundreds of round-trips — the most common "it's slow at scale" cause. Batch/join/`IN`-query; catch them in review and with a query-count assertion in tests.
- **Hot partitions / hot keys** — a tenant-id or time prefix that concentrates writes on one shard/index range. Design keys to spread load; watch per-tenant rate (the cost/abuse metric in `observability-and-incident-response.md` doubles as a hot-tenant signal).
- **Unbounded anything** — an unpaginated list endpoint, an in-memory accumulation of a whole result set, a query with no `LIMIT`. Cursor-paginate (`threat-modeling-and-api-design.md`), stream, and bound memory; an instance that OOMs under a big tenant is a scale bug.

## 4. Capacity & performance targets (design inputs, not afterthoughts)
- **Name the numbers:** expected and peak throughput (req/s, jobs/hr), a **latency budget** (p95/p99 target — the SLO in `observability-and-incident-response.md`), and a **frontend performance budget** (Core Web Vitals — `observability` client-side section). A target you didn't write down can't be designed-to or tested-against.
- **Prove them with a load test** (`testing.md` load/perf tier — `locust`/`k6` + the per-job LLM token/cost ceiling), run before a launch and when the shape of load changes. The load test is also where you discover the connection-pool ceiling (§3) before a customer does.
- **Right-size, don't over-build.** Scale-to-zero Cloud Run + a pooler + a queue carries a solo product a very long way; multi-region, sharding, and read-replicas are **stated Tier-2 decisions** with a cost (cross-ref `business-continuity.md` on single-vs-multi-region), not defaults. Match the mechanism to the measured need.

## Checklist
- [ ] Request handlers hold no per-user/instance state; sessions/cache/uploads/work are externalized.
- [ ] Slow/CPU-bound/bursty work is on a queue + worker, not the request path.
- [ ] Every queue has a DLQ + retry policy; the consumer is idempotent (at-least-once safe).
- [ ] DB write that must emit an event uses the transactional outbox (no dual-write loss).
- [ ] Connection-pool math checked (`instances × pool_max` vs `max_connections`); a pooler is in front if needed.
- [ ] No N+1, no unbounded list/memory; lists are cursor-paginated.
- [ ] Throughput + latency (+ Web Vitals) targets are written down and load-tested.

### Cross-references
- Degrade under overload (load-shed, circuit breaker, bulkhead) — `references/resilience-engineering.md`.
- Pool sizing, indexes, query patterns — `references/databases.md`; Cloud Run concurrency/autoscaling — `references/gcp.md`.
- Tenant-keyed cache + invalidation — `references/caching.md`; cursor pagination + idempotency keys — `references/threat-modeling-and-api-design.md`.
- Load/perf test tier — `references/testing.md`; SLO/latency budget + DORA + DLQ alerting — `references/observability-and-incident-response.md`; single-vs-multi-region — `references/business-continuity.md`.
