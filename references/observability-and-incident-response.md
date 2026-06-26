# Observability & Incident Response (SRE)

Companion reference for the senior-engineering-partner skill.


Two halves of one loop: **you cannot respond to what you cannot see, and you cannot see what you never instrumented.** This builds on SKILL.md's structured-logging + monitoring/dead-man's-switch standards — it does not repeat them. SKILL.md governs *how a script logs and a LaunchAgent gets watched*; this reference governs *how the deployed example multi-tenant SaaS stays observable and how you respond when it breaks.* The the example SaaS is the worked example throughout: FastAPI on Cloud Run → Cloud Run Job (extraction) → Anthropic call, on Cloud SQL Postgres with per-tenant RLS.

The discipline carries forward from the unattended-automation rules: alert on what's NEW, allowlist benign noise, summarize don't itemize, dead-man's-switch for silent non-runs. A noisy alerter gets muted within a week — that rule does not relax because the target is Cloud Run instead of a LaunchAgent.

---

## 1. Observability — instrument before you need it

### Structured logs (extends SKILL.md structured logging)
- **JSON to stdout, one event per line — Cloud Logging parses it for free.** Cloud Run captures stdout/stderr into Cloud Logging automatically; emit a JSON object per log line and the fields become queryable `jsonPayload`. Do not invent a logging sidecar. Set `severity` (Cloud Logging promotes the `severity` field to the log-entry level), a short `message`, and structured context — never f-string everything into one opaque string.
- **Thread a correlation/request id through the entire path: request → Cloud Run Job → model call.** Generate (or accept from an inbound `traceparent` / `X-Request-Id`) one id at the API edge, bind it into the logging context, and pass it explicitly to the extraction Job and into the Anthropic call's logged metadata. One `jobId`/`requestId` must let you `grep` the whole lifecycle across all three services. Without it you have three disconnected log streams and no way to reconstruct a single tenant's failed job.
- **NEVER log document content, extracted text, PII, prompts, model responses, secrets, or `key_ciphertext`.** This is the §2 cost-as-security rule's twin and it is absolute (cross-ref `data-protection.md`, `secure-data-processing.md` §2/§3). Log *about* the work, not the work: `tenant_id` (an opaque uuid, fine), `jobId`, `content_sha256`, token counts, `error_code`, duration_ms, `stop_reason`. The sensitive content and the prompt stay out of logging entirely — a log line is the easiest place to accidentally exfiltrate a tenant's data.
- **Log levels mean what SKILL.md says.** INFO = lifecycle milestones (job started/finished). WARNING = degraded-but-handled (a retry fired, a parser rejected a bomb). ERROR = the operation failed. CRITICAL = the service is down / data integrity at risk. Production runs at INFO; full prompt/response logging at DEBUG is a privacy footgun even gated — prefer to never have that code path.

### Metrics — RED, USE, business, cost
Four metric families. Cloud Run + Cloud SQL emit most of the first two as built-in Cloud Monitoring metrics; the last two you must instrument.

| Family | Applies to | Signals |
|---|---|---|
| **RED** | the API (request-driven) | **R**ate (req/s), **E**rrors (5xx / failed-job rate), **D**uration (p50/p95/p99 latency) |
| **USE** | resources (pool, CPU, mem) | **U**tilization, **S**aturation (pool waiters, mem near the Cloud Run limit), **E**rrors (pool checkout timeouts, OOM-kills) |
| **Business** | the product | jobs submitted / succeeded / failed, queue depth, time-to-first-result, files-rejected-by-the-parser-gate |
| **Cost** | per-tenant LLM spend | tokens in/out + cache_read/cache_creation + **$ per tenant**, derived from `usage_events` (the billing source of truth) |

- **Drive cost + business metrics off `usage_events`, not a parallel counter.** `usage_events` is already the billing source of truth (`secure-data-processing.md` §3) recorded in the same transaction as the work it bills — read per-tenant token/$ aggregates from it so observability and billing can never disagree.
- **Watch the psycopg3 pool as a first-class resource** (cross-ref `python-web-apis.md`, `databases.md`): pool size, checked-out count, and **waiters/checkout-wait time**. A saturated pool presents as latency, not errors — RED alone misses it; the USE family catches it.
- **DLQ depth + queue age** (cross-ref `scalability-and-system-design.md`): a non-empty dead-letter queue or a growing oldest-message age is a backlog/poison-message signal that the RED/USE families on the API miss entirely.

### Delivery metrics — the DORA four keys
Separate from runtime health: are you *shipping* well? Track the four (the industry standard — `dora.dev`), most derivable from data you already have:
- **Deployment frequency** and **change lead time** (commit→prod) — from the deploy workflow / git history. **Change failure rate** (deploys needing a rollback/hotfix) and **failed-deployment recovery time** (how fast you roll back) — from your rollback events + the incident/postmortem record (§3). The 2024 report adds **rework rate** as a fifth stability signal.
- For a solo product this is **lightweight, not a dashboard project** — but change-fail-rate and recovery-time are exactly the DR/resilience posture measured, and a creeping lead time or change-fail rate is an early "the system is getting hard to change safely" signal worth watching. Don't gold-plate it; do glance at it.

### Distributed tracing (OpenTelemetry)
- **One trace must span API → Cloud Run Job → Anthropic call.** Use OpenTelemetry to create a root span at the request, propagate context (W3C `traceparent`) to the extraction Job, and wrap the model call in a child span tagged with token counts and `stop_reason` (never the prompt). Export to **Cloud Trace** (GCP-native; the OTel exporter is supported — verify the current exporter package + setup against current OpenTelemetry/GCP docs before wiring it). A trace turns "the job was slow" into "extraction took 40s, the model call took 4s" — actionable instead of a guess.
- Trace context and the log correlation id should be **the same id** (or trivially joinable) so a trace links to its logs and back.

### Health vs readiness (cross-ref `python-web-apis.md`)
- **`/healthz` (liveness) and `/readyz` (readiness) are different endpoints with different jobs.** Liveness = "the process is up, don't kill me" — cheap, no dependencies. Readiness = "I can serve traffic" — and **readiness MUST verify the DB pool is usable** (acquire a connection, `SELECT 1`, release) before reporting ready. If readiness only returns `200 OK` unconditionally, Cloud Run routes traffic to an instance whose pool is exhausted or whose Cloud SQL connection is dead, and every request 500s. Readiness is the gate that keeps a half-broken revision out of rotation.
- Keep the readiness DB check cheap and bounded (short timeout) — a readiness probe that hangs is itself an outage. Don't run a full query; `SELECT 1` proves the pool round-trips.

### GCP-native stack
Cloud Logging (logs), Cloud Monitoring (metrics + alerting policies + uptime checks + dashboards), Cloud Trace (traces), Error Reporting (auto-groups exception stacktraces from logs). Prefer these over standing up a parallel Prometheus/Grafana/ELK stack — it is one bill, one IAM surface, and scale-to-zero-friendly, consistent with the local-first → GCP cost strategy. *Verify exact metric type names, alerting-policy fields, and exporter package names against current GCP docs* — the durable principle (GCP-native four pillars) is stable; specific resource/field names drift.

### Client-side / frontend monitoring (the browser blind spot)
The four pillars above watch the **server** — API, Job, model call. They are blind to everything that happens in the user's browser: an unhandled JS exception, a failed `fetch`, a render crash, a slow page. For a commercial SaaS with an SPA (`frontend-web-security.md`), a feature can be fully broken for users while every server metric stays green. Close the gap:
- **Capture client errors.** A global `window.onerror` / `unhandledrejection` handler (or a tool's SDK) reports uncaught exceptions and failed requests back to a sink, tagged with the **same correlation id** the API uses so a browser error joins its server-side trace. Without this, the first signal of a frontend break is a support email.
- **Real-User Monitoring (RUM) + Core Web Vitals.** Track LCP/INP/CLS and route timing from real sessions — synthetic uptime checks (which hit the API) never see a broken render. Cheap and high-signal for a user-facing product.
- **Tool choice — name the trade-off.** **Sentry** (or similar) is the best-of-breed for browser error tracking + tracing + session replay; **Firebase Performance Monitoring + Crashlytics** is the more GCP-/Firebase-native option (natural if the re-platform lands on Firebase Auth — `frontend-web-security.md`). GA4 covers Web Vitals but not error tracking. Pick one; don't ship a user-facing SPA with *zero* client visibility.
- **Privacy still applies — a client monitor is a subprocessor.** It sees URLs, user agents, and potentially screen content (session replay): it needs a **DPA + no-train/retention posture** like any other subprocessor (`data-protection.md`), must **scrub PII** (mask inputs in replay, strip tokens/PII from breadcrumbs and URLs), and must honor the CSP (`frontend-web-security.md` — its script is allowlisted/SRI-pinned, not an `unsafe-inline` hole). The no-PII-in-logs rule does not stop at the server boundary.

---

## 2. SLOs & alert quality — alert on symptoms, not causes

- **Define SLOs, then alert on the SLO, not on raw thresholds.** Pick a small number: e.g. availability (proportion of non-5xx requests) and latency (p95 under a target). The SLO sets an error budget; the alert fires on **burn rate** — the rate at which you're consuming that budget — not on "CPU > 80%" or "5 errors appeared." Burn-rate alerting (fast-burn = page now, slow-burn = ticket) is the standard for low-noise, actionable alerts. Cloud Monitoring supports SLO + burn-rate alerting policies — *configure against current docs*; the principle (alert on budget burn, page on fast burn) is what's load-bearing.
- **Alert on symptoms the user feels, not internal causes.** "p95 latency breached / error rate up / job-success rate down" is a symptom — actionable and user-visible. "CPU is high" is a cause that may or may not matter; alerting on it is cause-spam that trains the operator to ignore the channel. This is the deployed-service form of SKILL.md's "summarize, don't itemize" + allowlist-benign-noise rules: one meaningful symptom alert beats a hundred threshold pings.
- **Every alert is actionable, low-noise, and links a runbook.** If an alert fires and the responder's correct action is "nothing" or "wait," it should not be an alert — demote it to a dashboard. Every alert's notification text **must link the runbook** (§3) for that exact condition. An alert with no runbook is an unanswered question at 3am.
- **Cost spikes are alerts, not month-end surprises (cross-ref `secure-data-processing.md` §2).** LLM cost is a security + billing property: a per-tenant token/$ spike can mean a billing-DoS (unbounded retry loop on `overloaded`), an abuse pattern, or a runaway job. Alert on **per-tenant** token/cost rate crossing a baseline — not just the global GCP billing budget, which aggregates the signal away. The tenant dimension is the whole point; a global budget alert tells you *that* you're bleeding money, not *whose* tenant did it.

---

## 3. Incident response — detect → triage → mitigate → resolve → postmortem

### Severity levels
Encode both the solo-now and team-later modes (SKILL.md team model). Solo + AI agents: you are every role; the table sets *response expectations*, not a staffing org.

| Sev | Meaning | Examples (example-saas) | Response expectation |
|---|---|---|---|
| **SEV1** | Service down OR data integrity / tenant-isolation at risk | API hard-down; DB unreachable; suspected cross-tenant data exposure; per-tenant key compromise | Drop everything, mitigate now, all-hands (team), notify stakeholders |
| **SEV2** | Major degradation, partial outage, no confirmed data risk | Extraction Jobs failing for one tenant; latency SLO fast-burn; Anthropic sustained `overloaded` | Active mitigation this session; status updates |
| **SEV3** | Minor / single-feature / cosmetic, workaround exists | One parser rejecting a valid edge-case file; non-critical dashboard gap | Ticket, scheduled fix, no page |

- **Any suspected breach of the tenant boundary is SEV1 on sight** — the tenant boundary is a legal boundary (`secure-data-processing.md` §3, `data-protection.md`). Treat "I'm not sure if tenant A saw tenant B's data" as SEV1 until proven otherwise; assume-breach, don't assume-benign.

### On-call & escalation (both modes)
- **Solo + agents (now):** you are primary. The escalation path is **you → the human owner** for any SEV1 or any irreversible/customer-visible decision (notify a tenant, rotate a key, roll back) — surface it, don't self-decide. Use an interrupting push/page channel to escalate a SEV1 when the owner has stepped away.
- **Notification channels — route by severity, don't fire everything at one inbox.** Cloud Monitoring alerting policies fan out to **notification channels**: email, Slack, **PagerDuty/Opsgenie**, SMS, the **Cloud Mobile App** (push), and Pub/Sub/webhook (for custom routing or auto-remediation). Map them to severity so noise can't bury a page: **fast-burn / SEV1 → a push/page channel** (the GCP mobile app push, or mobile-push per `feedback_mobile_push.md`) that interrupts; **slow-burn / SEV2-3 → a ticket or a digest** (Slack/email), never a page. This is the deployed-service form of SKILL.md's *deliver durably + summarize-don't-itemize*: ephemeral toast for nothing critical, an interrupting channel only for what truly needs a human now. A full paging tool (PagerDuty) is **team-mode** posture — overkill for solo, where mobile push is the page; wire the channel abstraction now so adding a rotation later is config, not re-architecture.
- **Team (later):** named primary/secondary rotation, documented escalation timeout (no ack in N min → escalate), and a single declared **Incident Commander** per incident who owns decisions and comms. Encode this so onboarding a human is zero-friction — same as the branch-protection/CODEOWNERS posture (SKILL.md team model): disciplined now, frictionless later.

### Lifecycle
**Detect** (an alert fired, or a tenant reported it) → **Triage** (assign Sev, find blast radius: which tenants, which revisions, since when — the correlation id earns its keep here) → **Mitigate** (stop the bleeding: roll back the revision, shed load, disable the broken path — restoring service beats finding root cause) → **Resolve** (root cause fixed, verified, SLO recovered) → **Postmortem** (within days, while memory is fresh). Mitigate-before-diagnose is the rule: a rolled-back revision buys you the calm to investigate.

### Runbooks — every alert maps to exactly one
A runbook is a flat, copy-pasteable checklist: **symptom → verify → mitigate → escalate → verify-recovered.** No prose. The the example SaaS deploy needs at minimum these, each pre-written *before* the incident:

| Runbook | First moves (principle — verify exact commands against current `gcloud`/`dbmate`/KMS docs) |
|---|---|
| **DB down / pool exhausted** | Check Cloud SQL instance health + connection count; confirm via `/readyz`; check for a connection leak vs. real instance failure; fail over / restart instance; the API should already be 503-ing cleanly via readiness, not serving garbage |
| **Cloud Run failure / bad revision** | Identify the bad revision; **roll back by routing 100% traffic to the last-known-good revision** (Cloud Run keeps prior revisions — instant rollback, no rebuild); confirm health; then diagnose the bad image offline |
| **Per-tenant key compromise** | Treat as SEV1; **rotate the tenant's KMS-encrypted BYO key** (re-encrypt `key_ciphertext`, bump `kms_key_version` — `secure-data-processing.md` §3); revoke the leaked provider key at the provider; audit `usage_events` for anomalous spend on that key; notify the tenant |
| **Suspected tenant-data exposure** | SEV1; **contain first** (revoke access, freeze the suspect path); scope blast radius from audit/append-only tables + the correlation id; preserve evidence; then enter **Breach Response** (§4) — the privacy clock may have started |
| **Anthropic degraded** (`overloaded`/`rate_limited`) | Confirm bounded retry/backoff is honoring `retry-after` (not a billing-DoS loop — `secure-data-processing.md` §2); shed or queue non-urgent jobs; surface `error_code` to tenants; watch per-tenant cost during the retry storm |

- **Each alert's notification links its runbook URL.** A runbook nobody can find at 3am is a runbook that doesn't exist.

### Blameless postmortems
- **The system failed, not the person** — including when "the person" was an AI agent's PR. A postmortem that assigns blame teaches people to hide incidents; a blameless one teaches the org to fix the system that let the mistake reach prod.
- Required contents: **timeline** (reconstructed from the correlation id / Cloud Logging, with timestamps), **contributing causes** (plural — outages are rarely one cause; ask why-it-wasn't-caught, not just why-it-broke), **action items with named owners and due dates** (a postmortem with no owned action items is a journal entry, not a fix), and **what detection/alerting would have caught it sooner** (feeds back into §2). For SOC 2, the postmortem + tracked action items are CC7 evidence (cross-ref `compliance.md`).

---

## 4. Breach response — the privacy + security overlap

When an incident involves (or might involve) personal data, the security incident becomes a **privacy breach** with legal clocks. Pre-write this runbook; you do not want to be reading the GDPR text for the first time during a SEV1.

- **The GDPR / UK-GDPR 72-hour clock starts at awareness.** Under GDPR Art. 33, a controller must notify the supervisory authority of a personal-data breach **without undue delay and, where feasible, within 72 hours** of becoming aware — and notify affected data subjects without undue delay where the risk to them is high (Art. 34). CCPA/CPRA adds its own consumer-notification and (for some breaches) AG-notification duties on California residents' data. *These are the regimes in scope (GDPR/UK-GDPR + CCPA/CPRA; HIPAA is NOT in scope). Verify the current statutory text and your role (controller vs. processor) against counsel — the durable rule is "there is a hard clock, instrument so you can hit it"; do not invent thresholds.* Maps to SOC 2 **CC7** (incident handling) — cross-ref `compliance.md`, `data-protection.md`.
- **Lifecycle: detect → assess → contain → notify → remediate.**
  - **Detect** — an alert or report indicates possible personal-data exposure.
  - **Assess** — *is personal data involved, and whose?* Scope it precisely: which tenants, which data subjects, what categories. The append-only audit tables + `content_sha256` + correlation id are what make this answerable instead of a guess.
  - **Contain** — stop ongoing exposure (revoke access, rotate keys, pull the revision) *before* worrying about notification wording.
  - **Notify** — work the chain: if you are a **processor** for a tenant, you notify the **controller** (the tenant) without undue delay so *they* can meet *their* 72h regulator clock; if you are the controller, you notify the supervisory authority and, where high-risk, the data subjects. Know which hat you wear per data flow.
  - **Remediate** — fix the root cause, then feed the gap back into detection (§2) and the postmortem (§3).
- **Pre-write the breach runbook**: who decides it's a breach, who contacts counsel/DPO, the controller/processor notification templates, the regulator contact, and the assess-scope query playbook against the audit tables. A breach runbook written calmly in advance is the difference between a 72-hour notification and a 72-day one.

---

## 5. QA & testing the observability itself

Instrumentation and runbooks are code paths — untested ones rot silently and fail exactly when you need them.

- **Test that alerts actually fire.** Inject a synthetic failure (force a burst of 5xx, push synthetic latency, or temporarily lower a threshold in a staging env) and assert the alert fires and routes to the right channel. An alerting policy that has never been observed to fire is an assumption, not a control. This is the deployed-service analog of SKILL.md's "actually run the tests."
- **Exercise runbooks with game days.** Periodically rehearse a runbook end-to-end in staging — roll back a Cloud Run revision, simulate a DB failover, walk the key-rotation steps. A runbook that's never been run is a hypothesis. Game days find the stale `gcloud` flag, the missing permission, the step that assumes a tool you removed — *before* the real SEV1.
- **The dead-man's-switch catches the silent non-run (SKILL.md).** The worst failure emits no error string: a scheduled extraction sweep or a metering job that simply *stops running*. A freshness check — "did each scheduled job run within its expected cadence?" (last-success timestamp vs. expected interval) — catches what error-grepping never will. This is the same dead-man's-switch standard from SKILL.md, applied to Cloud Run Jobs / Cloud Scheduler instead of a LaunchAgent: alert on *absence*, not just on errors.
- **Verify logs don't leak.** A test (or a periodic scan) that asserts no document content, PII, prompt text, secret, or `key_ciphertext` appears in the structured-log output for a representative job — the §1 "never log content" rule, enforced, not just stated (cross-ref `secure-data-processing.md` §2 cost/PII logging discipline).
- **Treat dashboards + alerting policies as code.** Keep them in version control (IaC — cross-ref `iac-terraform.md`) so an alerting policy can be reviewed in a PR, rolled back, and reproduced across environments — not click-configured once in the console and lost. A dashboard that exists only in one person's console is a single point of failure for the whole observability story.
