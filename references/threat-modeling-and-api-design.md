# Threat Modeling & API Design

Companion reference for the senior-engineering-partner skill.

> **Rigor tier:** a formal STRIDE-per-trust-boundary threat model and the full API-hardening surface are **Tier-2 (production/commercial) posture** from SKILL.md's *Project Phase & Rigor Ladder*. At Tier 0/1, a few lines naming the obvious threats to auth/data + the floor controls suffice; defer the formal model with a `TODO` — but high-risk surfaces (multi-tenancy, file ingestion, billing, secrets) pull a project to Tier 2.

Two halves of one job: **model the threats before you build the high-risk surface, then design the API surface so the model has fewer entries to begin with.** The example multi-tenant SaaS is the worked example — attacker-controlled files in, Claude in the middle, paying tenants' sensitive data at rest. Threats here are cross-tenant reads, free compute, prompt-injected output, and evidence tampering. Cross-ref `secure-data-processing.md` (the three threat surfaces), `python-web-apis.md` (the auth/RLS pipeline, error contract), `databases.md` (RLS, injection), `compliance.md` (OWASP/SOC 2), `testing.md` (the gates that prove a control).

---

## 1. Threat modeling — lightweight, before the build, in the PR

**Threat-model BEFORE you write a high-risk change, not after it ships.** High-risk = anything touching **auth, multi-tenancy, file ingestion, billing, or secret handling.** A normal CRUD endpoint on already-isolated data does not need its own model; a new file parser, a new RLS policy, a billing path, or a new trust boundary does.

**The artifact is a section in the design doc / PR description, not a 50-page document.** A short, real threat model that ships beats an exhaustive one that never gets written. Four lines per threat: the threat, the existing control, the gap (if any), and the test that proves the control. If a threat has no test, it has no control — it has a hope.

### Trust boundaries in this stack

Name the boundaries first; every threat lives at one. A *trust boundary* is any point where data or control crosses from less-trusted to more-trusted.

| Boundary | Less-trusted side | More-trusted side | Primary control |
|---|---|---|---|
| Client → API | bearer token, request body | FastAPI handler | Token verify (`Depends`), Pydantic validation, never trust client-supplied tenant id |
| API → DB | app code holding a tenant id | row visibility | RLS via session GUC + `SECURITY DEFINER` resolver — isolation lives in the DB, not app code |
| Untrusted file → parser | attacker-controlled bytes | extracted text | Magic-byte routing, bombs bounded, ephemeral per-job scratch, resource caps |
| Document text → model | attacker-authored content | Claude + your system prompt | Content is data not instructions; validate structured output |
| Worker → provider | tenant PII in the request | Anthropic API | Per-tenant key (DI'd), send only what analysis needs, known retention terms |
| Job → billing | work performed | `usage_events` | Metered in the *same transaction* as the work |

### STRIDE applied to this stack

Walk STRIDE per boundary; it forces you past the threat you already thought of. Map each to the control that exists and the test that proves it.

| STRIDE | Concrete abuse case here | Existing control | Proven by |
|---|---|---|---|
| **S**poofing | Forged/expired token; client claims another tenant's id | Firebase token verify (PyJWT; dev HS256 verifier **fails closed**); tenant id derived server-side, never from body | `tests_api/` auth tests; dev-verifier rejects when secret unset |
| **T**ampering | Edit an evidence/audit row; mutate `content_sha256` | Append-only evidence tables (pgTAP `03_append_only.sql`); content hash on ingest | pgTAP append-only gate; hash-mismatch test |
| **R**epudiation | Tenant denies an action; no trail | Append-only audit tables, structured logs with actor + request id | audit-row assertions |
| **I**nformation disclosure | **Cross-tenant evidence read** (the breach); leaked `key_ciphertext`; verbose error reveals internals | RLS `FORCE` + default-deny; KMS-encrypted per-tenant keys; generic error contract (§2) | pgTAP `01_isolation.sql` + `tests_api/test_isolation.py`; key-secrecy test |
| **D**enial of service | Zip/image/XML bomb pins CPU/memory; unbounded model retry = billing-DoS; offset pagination on a huge tenant set | Bombs bounded + wall-clock timeout in a **Cloud Run Job** off the request path; capped `max_tokens` + bounded backoff honoring `retry-after`; cursor pagination + page-size cap | malicious-corpus tests under a resource cap; rate-limit test |
| **E**levation of privilege | `SET LOCAL ROLE` to a higher role; SECURITY DEFINER resolver abused | Role allowlist on `SET LOCAL ROLE`; resolver is narrow, `search_path`-pinned, audited | role-allowlist test; resolver unit test |

### Assume-breach mindset

Design as if one layer is already compromised. App code *will* eventually pass the wrong tenant id — RLS is what makes that a no-op instead of a breach (defense in depth: the control that holds when the layer above it fails). The standing questions for any high-risk change:

- **What does the attacker want?** Cross-tenant data, free compute on your or another tenant's key, a prompt-injected verdict, a tampered evidence record. Enumerate the *goal*, then trace the path to it.
- **If the API layer is bypassed, does the DB still deny?** (RLS must — not an app `if`.)
- **If the parser is fed a malicious file, what is the blast radius?** (Ephemeral per-job scratch + caps + Job isolation → one job, killed, not the fleet.)
- **If the model is prompt-injected, does anything downstream act on it?** (Output is a validated schema, not free text the caller executes.)

Every row above terminates in a **security test** (cross-ref `testing.md`, `secure-data-processing.md`). The model is not done until each new threat has a failing-without-the-control test in CI.

---

## 2. API design — shrink the attack surface by contract

A clean, explicit contract removes whole classes of threat (ambiguous types, silent breakage, double-charges). Design these in from the first endpoint.

### OWASP API Security Top 10 (2023) — the map (the *API* list, not the web list)

This section's controls already implement the API Top 10; name them by the **API** codes, not the web ones. The API list is its own taxonomy — **API1:2023 BOLA ≠ web `A01:2021 Broken Access Control`.** Where `python-web-apis.md` tags the client-supplied-tenant-id hole `OWASP A01`, that's the broad web category; the precise, make-or-break API code is **API1:2023**. Verify codes against the live project — *OWASP API Security Top 10 2023*, `owasp.org/API-Security/editions/2023/`.

| Control in this stack | API Top 10 (2023) |
|---|---|
| Tenant id from the **verified token, NEVER the client** → `FORCE` RLS denies cross-tenant rows (§1, `python-web-apis.md`) | **API1:2023 Broken Object Level Authorization** (BOLA/IDOR) — *the* one; cross-tenant read is exactly this |
| The verify → resolve → role-drop auth pipeline (`require_token`/`require_session`) | **API2:2023 Broken Authentication** (token verify, fail-closed dev mode) + **API5:2023 Broken Function Level Authorization** (the `Depends` gate per route) |
| Capped `max_tokens`, bounded backoff, `429`+`Retry-After`, body-size cap, bombs bounded | **API4:2023 Unrestricted Resource Consumption** (the billing-DoS row in §1) |
| Pydantic reject-unknown-fields / no auto-bind of client input to model fields | **API3:2023 Broken Object Property Level Authorization** — mass assignment **and** excessive data exposure merged into one 2023 code (no separate "API6 Mass Assignment" as in 2019) |
| **Allowlist the destination of any server-fetched user-supplied URL** (webhook target, image/avatar/import URL, link-preview fetch); block link-local/metadata + private ranges (`169.254.169.254`, `::1`, RFC-1918) and non-`http(s)` schemes; re-validate **after** redirects. The file-parse SSRF path (XXE, doc-XML-driven fetch) is covered in `secure-data-processing.md` §2 | **API7:2023 Server-Side Request Forgery** — the server making a request *to an attacker-chosen address* (cloud metadata theft, internal-network pivot) |
| `/docs` off in prod, CORS allowlist, generic error contract (§2) | **API8:2023 Security Misconfiguration** |

### Versioning & deprecation

- **Version the API from day one; never break a published contract.** Pick one scheme and hold it: a URL prefix (`/v1/...`) or a version header — URL prefix is the simpler, more cacheable default for this stack. Do not mix schemes.
- **A published response is a contract.** Adding an optional field is non-breaking; removing a field, renaming one, tightening a type, or changing an error shape is breaking → new version.
- **Deprecate on a schedule, never by surprise.** Announce, set a sunset date, and keep the old version serving through it. The IETF `Deprecation` and `Sunset` response headers are the standard signals — *verify the exact header names/format against current docs* before relying on them. At minimum, document the sunset in the changelog and the OpenAPI description.

### Idempotency (directly protects billing & the jobs path)

**Unsafe POSTs that cost money or create work MUST accept an idempotency key — job submit, billing, onboarding.** A client retry after a dropped response must not double-process or double-charge.

- Client sends a unique key (header is the common convention — confirm the exact name you adopt and document it). Server stores `(key → result)` and returns the stored result on replay instead of re-running.
- **Tie the idempotency record to the work in the same transaction that writes `usage_events`** — so a retry can never produce a second metered/billed event. This is the concrete link between idempotency and metering integrity (cross-ref `secure-data-processing.md` §3).
- Scope keys per tenant; expire them. A replayed key must return the original result, not start a new job.

### Error contract — one shape, and the 401/403/422 boundary

**Adopt one machine-readable error shape and use it everywhere.** RFC 7807 `application/problem+json` (`type`/`title`/`status`/`detail`/`instance`) is the standard choice; a documented house schema is acceptable if it is *consistent*. The failure mode to avoid: every endpoint inventing its own error JSON.

- **Keep auth errors generic to the client; log the real reason server-side.** "Invalid credentials" out, the specific cause in the logs (cross-ref `python-web-apis.md`) — a precise auth error is a spoofing aid.
- Respect the status boundary — getting it wrong leaks information or breaks clients:

| Status | Means | Use when |
|---|---|---|
| **401** Unauthorized | not authenticated | missing/invalid/expired token |
| **403** Forbidden | authenticated, not allowed | valid token, no access to *this* resource/tenant |
| **422** Unprocessable | authenticated, request malformed | Pydantic validation failed (FastAPI's default for body errors) |

Returning 403 where RLS already returns "no rows" is a design choice — decide deliberately whether a cross-tenant id is a `404`/empty (don't confirm the row exists) or a `403`; **never let it succeed.**

### Pagination — cursor, not offset

**Use cursor (keyset) pagination for any large or tenant-scoped collection; never `LIMIT/OFFSET` on big sets.** Offset pagination degrades (the DB scans and discards skipped rows) and is unstable under concurrent inserts (rows shift, clients skip/duplicate). Return an opaque cursor; cap page size server-side. Offset is acceptable only for small, bounded admin lists.

### Rate limiting & input/output validation

- **Rate-limit, and say so honestly: `429 Too Many Requests` with a `Retry-After`.** A bounded client backoff depends on it (cross-ref the billing-DoS row in §1, and `python-web-apis.md`).
- **Validate every request body and every response with Pydantic** — bound string lengths, enumerate choices, reject unknown fields. Validation *is* a security control (it's the Tampering and DoS mitigation at the client→API boundary).
- **Allowlist any client-chosen sort/filter/order column — never interpolate it into SQL.** A client-supplied column or direction is injection if it reaches the query as a string; map the client value to a fixed, server-side set of allowed columns (cross-ref `databases.md` injection rule). Parameterization does not cover identifiers — only an allowlist does.

### OpenAPI is the contract — but lock the docs in prod

- **OpenAPI is the source of truth for the contract** (request/response schemas, error shapes, versioning). Generate it from the Pydantic models; review it in the PR like code — a schema diff is an API-change diff.
- **Disable the public `/docs` and `/redoc` (and the raw `openapi.json` if it leaks internals) in production** (cross-ref `python-web-apis.md`). The contract is published to consumers deliberately, not auto-exposed at a guessable path on the prod host.

### Webhooks — only if you add them (none today; design them right when you do)

If/when an outbound or inbound webhook is added (e.g. billing/Stripe callbacks):

- **Sign every payload and verify the signature before acting on it** — an unauthenticated webhook endpoint is a spoofing + free-action surface. Use the provider's documented signing scheme and its verification helper; *verify the exact scheme against current provider docs* rather than hand-rolling HMAC from memory.
- Make handlers **idempotent** (providers retry and may deliver duplicates) — reuse the idempotency-key discipline above so a redelivered event is not double-processed.
- Validate the body with Pydantic after signature verification; check the timestamp to reject replays; respond fast (do work async).

---

## The through-line

A threat model lists what can go wrong; good API design removes entries from that list before they're written. Cursor pagination deletes a DoS row. Idempotency keys delete a double-charge row. A server-side tenant id and `FORCE` RLS delete the cross-tenant row. An allowlisted sort column deletes an injection row. **Design the surface so the model is short — then prove each remaining entry with a test.**
