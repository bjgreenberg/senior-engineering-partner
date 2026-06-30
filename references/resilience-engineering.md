# Resilience Engineering (designing software to degrade, not die)

Companion reference for the senior-engineering-partner skill.

> **Rigor tier:** the *cheap, always-on* patterns — timeouts on every outbound call, retry-with-backoff on idempotent operations, fail-clear error handling — are a **floor** (a missing timeout is a latent hang at any tier). Circuit breakers, bulkheads, and formal degraded modes are **Tier-1+ where the system has real users and real dependencies**; a Tier-0 spike can defer them with a `TODO`. The point: build continuity *into the code* so a dependency failure is a degraded feature, not a full outage — the in-code complement to `disaster-recovery.md` (restore after the fact) and `business-continuity.md` (the wider plan).

The governing rule: **a failure in one dependency must not cascade into a total outage.** A senior engineer assumes every network call, every downstream service, and every external provider *will* fail, and designs the failure to be partial, fast, and visible. This is the Netflix/Hystrix lesson — show fallback recommendations rather than freeze the whole app. Cross-ref `threat-modeling-and-api-design.md` (idempotency keys, retries, the error-shape boundary — the API-design slice of this), `observability-and-incident-response.md` (you can't degrade gracefully if you can't *see* the failure; alert on SLO burn), `python-web-apis.md` (where these land in FastAPI), `databases.md` (pool/statement timeouts).

**Resilience is sustaining function under surprise, not just preventing failure (Safety-II).** The SRE controls below are the *prevent/contain* half; the other half is four cornerstones (Hollnagel/Woods): **anticipate** (name the next failure before it lands), **monitor** (watch the system and its environment — the SLO/readiness signals here), **respond** (the breakers, fallbacks, and kill-switches), and **learn** (from what goes *right* as well as wrong — the blameless postmortem). A system strong on respond but weak on anticipate/learn passes today's outage and repeats it. *Read [the four cornerstones of resilience](https://www.resilience-engineering-association.org/resources/where-do-i-start/) — verify the canonical wording against Hollnagel's source before citing.*

---

## 1. The cheap floor — timeouts, retries, idempotency, fail-clear (do these always)
- **Every outbound call gets a timeout.** A call with no timeout is an unbounded hang that holds a worker/connection until something else breaks. Set connect *and* read timeouts on every HTTP client, DB query (statement timeout — `databases.md`), and model call. A missing timeout is a bug, not a default.
- **Retry only what's safe, with backoff + jitter + a cap.** Retry transient failures (5xx, timeouts, connection resets) on **idempotent** operations only; use exponential backoff with jitter and a bounded attempt count. Never blind-retry a non-idempotent POST (you double-charge or double-write) — pair it with an **idempotency key** (`threat-modeling-and-api-design.md`) so a retry is safe.
- **Fail clear, never silent.** A failure surfaces as a non-zero exit / logged error / explicit error response — never a swallowed exception that returns a wrong-but-quiet result (SKILL.md *Structured Logging*: a silent failure is worse than a crash).
- **Make retries idempotent end-to-end** — the same lesson as `secrets-and-key-rotation.md`'s re-wrap and `databases.md`'s migrations: an operation that may run twice must converge to the same state.

---

## 2. Stop cascades — circuit breaker & bulkhead
- **Circuit breaker.** When a downstream dependency is failing, stop hammering it: after N consecutive failures the breaker *opens* and calls fail fast (returning a fallback) instead of piling up on a dead service; it periodically half-opens to test recovery. This protects *both* sides — you stop wasting workers waiting on a corpse, and you give the struggling dependency room to recover. Use a library (don't hand-roll the state machine); wrap the model provider, the payment processor, and any flaky third party.
- **Bulkhead.** Isolate resources per dependency so one slow/dead downstream can't exhaust the shared pool and sink everything. Separate connection pools / worker pools / concurrency limits per dependency (the ship-compartment metaphor: a breach floods one compartment, not the hull). Concretely: don't let a hung LLM call consume every worker that also serves logins.
- **Backpressure / load-shed.** Under overload, reject or queue *early and explicitly* (429 with `Retry-After`, a bounded queue) rather than accepting unbounded work until the process OOMs. A bounded queue that sheds load degrades; an unbounded one collapses.

---

## 3. Degraded modes & fallbacks — keep the core up
- **Design the degraded mode on purpose.** For each dependency, decide what the product does when it's down: serve cached/stale data (`caching.md`), queue the work for later, disable just the affected feature behind a banner, or return a clear "temporarily unavailable" — never a white-screen crash. The core path (auth, viewing existing data) should survive a non-core dependency (recommendations, enrichment, a third-party API) being down.
- **Fallbacks must be safe, not silently-wrong.** A fallback value or cached response is fine *if it's correct-enough and labeled*; a fallback that returns another tenant's data or a stale authorization is a security failure, not resilience. Tenant-scope and freshness still apply (`caching.md`, `data-protection.md`).
- **Validate before you depend.** Health/readiness checks must actually round-trip the dependency (a readiness probe that checks the DB pool for real — `observability-and-incident-response.md`), so the load balancer pulls a sick instance instead of routing into a degraded one.

---

## 4. Fast mitigation levers — flags & kill switches
- **Feature-flag / kill-switch the risky surfaces.** A new integration, an expensive code path, or a flaky provider gets a flag you can flip *without a deploy* so the first incident move (mitigate before you diagnose — `observability-and-incident-response.md`) is one toggle, not a hotfix-and-redeploy under pressure. Roll back first, debug after.
- **Prefer rolling back to rolling forward.** The fastest mitigation is usually reverting to the last known-good (deploy or flag state); the deploy/rollback discipline in `github-actions.md` is the continuity lever for a bad release.
- **Test the failure path.** A fallback/breaker/degraded mode that's never been exercised is `disaster-recovery.md`'s untested-backup problem in code form. Inject the failure (a fault test, a dependency stubbed to error, a lightweight game-day) and prove the system degrades as designed — don't first discover the breaker is misconfigured during the real outage.

---

## 5. Scheduled work must catch up after downtime
- **A wall-clock scheduler does not replay runs missed while the host was off/asleep.** `cron`, launchd `StartCalendarInterval`, and systemd calendar timers fire at a *clock time*; if the machine is down or suspended at that instant, the run is **silently skipped, not deferred** — it simply doesn't happen until the next scheduled time (on a laptop that sleeps overnight, a 7 AM job can be missed every single day). Don't assume "it'll just run when the machine wakes" — most wall-clock schedulers don't. (The catch-up exceptions: `anacron`, and systemd timers with `Persistent=true` — prefer them where the platform offers them.)
- **For a job that must run even across downtime, pair the wall-clock trigger with an elapsed-time/catch-up trigger + an idempotent due-gate.** Add a periodic elapsed-time trigger (launchd `StartInterval`, a systemd `OnUnitActiveSec` timer, or a frequent cron that self-throttles) that *does* fire on the next wake, and guard the real work with a **due-gate**: run only when a scheduled window is actually outstanding (e.g. "last success is older than the most recent scheduled occurrence"), else exit immediately. The gate turns the extra triggers into free no-ops and makes the job **idempotent** — the same property §1 demands of retries — so the on-time trigger and the catch-up trigger can't double-run it.
- **Keep the catch-up gate consistent with whatever monitors the job.** If a dead-man's-switch / heartbeat watches the job (`references/logging-and-monitoring.md`), compute "is a run outstanding?" the *same way* in the gate and in the monitor (same schedule math, same last-success signal) so they can never disagree — and make a no-op catch-up run write **nothing** to the watched artifact, or it resets the very heartbeat the monitor reads. Verify your scheduler's missed-run semantics (they differ across cron/anacron/launchd/systemd) before relying on either skip or catch-up behavior.

---

## Checklist
- [ ] Every outbound call (HTTP, DB, model) has connect + read/statement timeouts.
- [ ] Retries are backoff+jitter+capped and only on idempotent ops (non-idempotent writes carry an idempotency key).
- [ ] Failing/flaky dependencies are wrapped in a circuit breaker; critical dependencies have isolated pools (bulkhead).
- [ ] Overload sheds load explicitly (bounded queue / 429), never grows unbounded.
- [ ] Each dependency has a *designed* degraded mode; the core path survives a non-core failure; fallbacks stay tenant-scoped and labeled.
- [ ] Risky surfaces sit behind a flag/kill-switch flippable without a deploy; rollback is the first mitigation.
- [ ] The failure paths are actually tested (fault injection / game-day), not assumed.
- [ ] Scheduled/periodic jobs that must survive downtime have a catch-up trigger + idempotent due-gate (wall-clock schedulers silently skip missed runs), and the gate matches whatever heartbeat monitors the job.

### Cross-references
- Idempotency keys, retry/backoff at the API edge, RFC 7807 errors — `references/threat-modeling-and-api-design.md`.
- Seeing the failure (SLO burn-rate alerts, readiness that round-trips the pool), incident mitigation order — `references/observability-and-incident-response.md`.
- Stale-but-safe fallbacks + tenant-scoped cache keys — `references/caching.md`. Timeouts/pools in Postgres — `references/databases.md`. Deploy/rollback levers — `references/github-actions.md`.
- Restore *after* the failure — `references/disaster-recovery.md`; the wider continuity plan — `references/business-continuity.md`.
