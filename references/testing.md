# Testing Strategy (strict, enforced gates)

Companion reference for the senior-engineering-partner skill.

> **Rigor tier:** this is **Tier-2 (production/commercial) posture** from SKILL.md's *Project Phase & Rigor Ladder*. At Tier 0/1 (prototype/MVP) apply the lean baseline (critical-path/smoke tests, basic CI) and defer these heavy gates with explicit `TODO`s + promotion triggers — the security floor still holds at every tier.

This is the umbrella standard. The specifics live in siblings: `testing-single-file.md` (the conftest argv-patch harness), `databases.md` (pgTAP RLS, the seed→`SET LOCAL ROLE`→GUC→assert→`ROLLBACK` pattern), `python-web-apis.md` (httpx auth/contract tests), and `github-actions.md`/`github-teams.md` (how these become *required, merge-blocking* checks). The proving ground is `example-org/example-saas` — a commercial multi-tenant SaaS — so the posture is **strict, not aspirational: gates that FAIL CI, not advice that gets skipped.** A green-but-untested merge is the failure mode this file exists to prevent.

The governing rule (from SKILL.md, restated because it is load-bearing here): **when a test reveals real behavior differing from expectation, fix the test AND comment WHY. Never delete a failing test, never retry it to green, never `xfail` it to unblock a merge.**

---

## 1. The test taxonomy (mapped to the stack)

Every change lands somewhere in this taxonomy. Know which layer you are writing, because the gates (§3) are keyed to it.

| Layer | What it covers | I/O | Tooling | Speed |
|---|---|---|---|---|
| **Unit** | Pure logic — parsers' helpers, regexes, token/cost math, formatters | none | `pytest` | ms |
| **Integration** | Real Postgres in a per-test txn; real HTTP via `httpx.AsyncClient` | DB + ASGI | `pytest` + `httpx` + ephemeral PG | 10s–100s ms |
| **Contract** | Responses validate against the Pydantic response models | ASGI | `pytest` + `model_validate` | fast |
| **Tenant-isolation** | Cross-tenant denial at SQL (pgTAP) AND HTTP — incl. NEGATIVE asserts | DB + ASGI | `pg_prove` + `httpx` | medium |
| **Security** | Auth bypass, injection, the malicious-file corpus | varies | `pytest` + corpus | medium |
| **Property-based** | Parsers/regexes under generated input | none/light | `hypothesis` | medium |
| **Fuzzing** | Hostile-input parsers — find the crash you didn't imagine | none | `atheris` / libFuzzer | slow (nightly/manual) |
| **Mutation** | Tests the tests — do they actually catch a broken change? | none | mutation runner | slow (nightly) |
| **Load/perf** | API latency + an **LLM token/cost ceiling per job** | live-ish | `locust` or `k6` + cost asserts | slow (manual/nightly) |
| **DAST** | The *running* service — auth/headers/injection from outside | live (staging) | OWASP ZAP (`compliance.md`) | slow (manual/nightly) |

- **Unit tests do no I/O.** If a "unit" test touches the DB, the network, the filesystem, or the clock, it is an integration test in disguise — move it and mock or fixture the boundary. A unit suite that needs a database is the first thing that rots.
- **Integration tests use a real Postgres, never SQLite-as-a-stand-in.** RLS, `SECURITY DEFINER`, session GUCs, and `FORCE ROW LEVEL SECURITY` do not exist in SQLite — a passing SQLite test on tenant code is a false green. Run the same `postgres:16` you ship.
- **Contract tests prove the wire shape.** Validate the response JSON against the actual Pydantic model (`Model.model_validate(resp.json())`) — a handler that drifts from its declared schema is a silent API break that unit tests miss.
- **Tenant-isolation is the one test you cannot skip.** It gets its own subsection (§2).

---

## 2. Tenant-isolation: the un-skippable test (with deny assertions)

A cross-tenant leak in this product is a breach, not a bug (`secure-data-processing.md` §3). Isolation is tested at **both** layers, and **every isolation test asserts a DENY, not just an allow** — proving tenant A *sees its own row* is worthless without proving tenant A *cannot see tenant B's*.

- **SQL layer (pgTAP).** Seed as the migration/superuser role, then drop to the app role and set the session GUCs the resolver reads:
  ```sql
  SET LOCAL ROLE app_api;
  SELECT set_config('app.current_user_id',  '<tenant-a-user>', true);
  SELECT set_config('app.current_company_ids', '{<company-a>}', true);
  -- positive: A sees A's row
  SELECT is( (SELECT count(*) FROM documents WHERE id = '<a-row>'), 1::bigint, 'A reads own row' );
  -- NEGATIVE (the load-bearing assert): A cannot see B's row
  SELECT is( (SELECT count(*) FROM documents WHERE id = '<b-row>'), 0::bigint, 'A denied B row' );
  ```
  The full seed→`SET LOCAL ROLE`→set-GUCs→assert→`ROLLBACK` pattern, role allowlist, and `pg_prove` invocation live in `databases.md` — do not duplicate it, read it. **One caveat that suite alone can't cover:** seeding/migrating *as the superuser* makes the `SECURITY DEFINER` helpers bypass RLS via superuser status — which production doesn't have — so add the **production-parity gate** (re-run the suite under a non-superuser `BYPASSRLS` owner, with a fail-first `NOBYPASSRLS` negative) from `databases.md`.
- **HTTP layer.** Mint a tenant-A token, call the endpoint for a tenant-B resource id, assert **404/403, not 200-with-empty** (a 200 with `[]` can still hide a leak in a sibling field). Then assert A's own id returns 200. The token→session-GUC→RLS pipeline is in `python-web-apis.md`.
- **Why both.** pgTAP proves the policy is correct in the database (the legal boundary). HTTP proves the request actually *enters* an RLS-scoped transaction with the right GUCs — an endpoint that forgets the `Depends()` passes pgTAP and fails HTTP. You need both signals.
- **Tenant id is never client-supplied.** A test that takes the tenant id from the request body is testing nothing — assert that a forged/foreign `company_id` in the payload is ignored in favor of the token-derived identity.

---

## 3. ENFORCED GATES (the strict posture)

These are **required CI checks wired into branch protection** (`github-actions.md` for the workflow, `github-teams.md` for making them required + non-overridable). A red gate blocks the merge — for admins too.

### 3a. Coverage threshold that FAILS CI
- **Measure BRANCH coverage, not just line** — `pytest --cov=<pkg> --cov-branch`. Line coverage hides untaken `if`/`except` paths, which is exactly where auth and isolation bugs live.
- **The gate fails the build below the floor** — `--cov-fail-under=<N>` (pytest-cov exits non-zero, which fails the job). A coverage *report* nobody enforces is not a gate.
- **Tiered floor, highest on the dangerous code.** A sane default: a moderate floor repo-wide, and a **high floor (target ~90%+ branch) on the core/auth/RLS/parser packages** — the code where a miss is a breach or a billing error. Enforce the high floor *per-package*, not as a single blended repo number; a blended average lets a fully-tested utility module mask an untested auth module. Exact per-package config: verify pytest-cov's current options against its docs before pinning syntax.
- **Coverage is measured on the REAL package, never the shim.** A single-file engine imported via the `conftest.py` argv-patch harness must report coverage for the engine module itself, not for a 3-line re-export shim (which trivially shows 100%). Point `--cov` at the actual module under test. See `testing-single-file.md`.

### 3b. Required test TYPES per change-class (the merge contract)
Reviewers and CI enforce: **a change of class X does not merge without test Y.**

| Change | Required test(s) | Must include |
|---|---|---|
| **New API endpoint** | contract test + authz/isolation test | unauth → 401; wrong-tenant → 403/404; happy path validates the Pydantic model |
| **New RLS policy** | pgTAP test | a positive AND a **DENY** assertion (cross-tenant 0-rows) |
| **New file parser** | malicious-input test | the bomb/malformed sample is rejected cleanly — caught error + logged reason, no crash/hang/OOM (`secure-data-processing.md` §1) |
| **Any bugfix** | a regression test | **the test FAILS on the pre-fix code and passes after** — commit it red-then-green, or you have not proven the fix |

- **The regression-test rule is literal:** write the test, confirm it fails against the unfixed code, *then* fix. A regression test that was never seen to fail proves nothing about the bug.
- These are checked in review (CODEOWNERS-gated on sensitive paths — `github-teams.md`) and, where mechanizable, in CI. A human reviews every agent-authored PR before merge — no blind self-merge of test-bearing changes.

### 3c. A gate must be able to fail — and assert its own preconditions
The red-first rule (3b) is about individual tests; it generalizes to **whole gates**. A gate that *cannot go red* is decorative — it gives false confidence precisely when you most rely on it.

- **Prove the gate can fail (the inversion).** When a gate asserts a security property (tenant isolation under the prod privilege model, a parser refusing a bomb, a signature check), build a **negative scenario** that *removes* the property and confirm the gate **fails** on it — and wire the assertion so a *passing* negative **fails the gate**. A positive run that has never been shown to go red proves nothing about what it claims; the negative is what makes the positive *mean* something (the `databases.md` RLS production-parity gate is the worked example: a `NOBYPASSRLS` negative that must fail). Write the negative *fail-first*, same as a regression test.
- **Assert preconditions, don't print them.** A gate that *displays* the facts it depends on — a role's attributes, an object's owner, a tool version, the count of things it's checking — but never *asserts* them will sail green after a refactor silently invalidates one of them (e.g. a `SECURITY DEFINER` function that gets re-owned, so the suite passes for the wrong reason). Turn each load-bearing fact into a hard check that aborts the gate when it's wrong (a `DO $$ … RAISE EXCEPTION` / an `exit 1`), *before* the expensive assertions run. A printed precondition is documentation; an asserted one is a gate.
- **Trust the verdict, not just the exit code.** A non-zero exit can mean "the suite ran and failed" *or* "the harness never ran" (no test files, a parse error, a recreated container). If those must be distinguished — as in a negative scenario *required* to fail — assert on the tool's own verdict signal (e.g. `pg_prove`'s `Result: FAIL` line), not a bare non-zero exit, so an infrastructure failure can't masquerade as the proof you wanted.

---

## 4. Test data: factories, synthetic fixtures, zero real PII

- **NO real PII, evidence, or customer documents in tests — ever.** The corpus is synthetic. Real sensitive material in a test fixture is a data-protection violation (`data-protection.md`) that also leaks into CI logs and the git history. Generate plausible-but-fake data.
- **Factories, not literal dicts.** A wall of inline `{"id": ..., "company_id": ...}` dicts duplicated across 40 tests is unmaintainable and drifts from the schema. Use a factory (a builder function or `factory_boy`/`Hypothesis`-backed) that returns a valid object with sane defaults and per-test overrides. One schema change updates one factory.
- **Ephemeral DB, torn down every run.** `docker-compose` (OrbStack locally) or `testcontainers` spins a throwaway `postgres:16`, migrations apply via `dbmate`, the suite runs, the container dies. Never test against a shared/long-lived DB — state bleeds between runs and someone's stale row turns a real bug green.
- **Per-test transactional ROLLBACK for integration.** Each test opens a transaction, does its work, and rolls back — so tests are order-independent and leave no residue. The seed-as-superuser → `SET LOCAL ROLE` → GUCs → assert → `ROLLBACK` mechanics are in `databases.md`.
- **Malicious corpus is fixtures, not generated at runtime.** Check the truncated PDF, zip bomb, oversized-dimensions image, and XXE-payload docx into the test tree (clearly marked, never executed as real input outside the test). `secure-data-processing.md` §1 lists the classes.

---

## 5. Security testing (its own gate, not an afterthought)

Security tests are first-class CI gates, not a manual pre-release pass.

- **Auth bypass.** No token → 401; expired/garbage/wrong-issuer token → 401; valid token for tenant A on tenant B's resource → 403/404. Locally the dev HS256 verifier mints tokens; assert the **prod Firebase verifier rejects an HS256 token** so the dev shim can never satisfy prod (`python-web-apis.md`).
- **Injection.** Every query path has a parameterized-query test with a `'; DROP`/`%`/`\x00` payload that must be treated as a literal, not SQL. Path-traversal payloads (`../`, absolute paths, Zip-Slip archive entries) must be refused before any write.
- **Malicious-file corpus under resource limits.** Run the extractors against the bomb corpus inside a memory/CPU/wall-clock cap and assert they stay within budget — no OOM, no pinned CPU, no hang. The cost-as-security ceiling (capped `max_tokens`, bounded retry honoring `retry-after`, prompt-cache metering) is asserted too — an unbounded retry loop is a billing-DoS (`secure-data-processing.md` §2).
- **Indirect prompt injection.** A document body containing "ignore your instructions…" must leave the structured `AnalysisResult` shape intact and the verdict un-flipped — the injection is treated as evidence, not obeyed (`secure-data-processing.md` §2). DI a fake model client so this runs with no live API call.
- **Static gates run alongside:** `bandit` (HIGH/MEDIUM fail), dependency/secret scanning, CodeQL — these are CI gates in `github-actions.md`, not part of the pytest run, but they gate the same merge.

---

## 6. Property-based, mutation, and load testing

- **Property-based (Hypothesis) for parsers and regexes.** Example-based tests check the cases you thought of; the attacker supplies the ones you didn't. Drive parsers and field-extraction regexes with generated input and assert *invariants* (never crashes, never returns a half-parsed object, output stays within bounds) rather than exact values. Pin a seed for reproducibility (§7); when Hypothesis finds a failing case it persists it — **promote that minimized example into a permanent regression test**, do not just let the example DB hold it.
- **Mutation testing tests the tests.** High coverage with weak assertions still ships bugs. A mutation runner makes small breaking edits to the code and asserts the suite goes red; survivors are blind spots in your assertions. Run it **nightly/pre-release on the core/auth/RLS code**, not on every PR — it is slow. (Verify the exact mutation tool name and its current CLI against its own docs before pinning — do not assume invocation flags.)
- **Load/perf with a cost ceiling.** `locust` or `k6` drives the API for latency/throughput under concurrency. Uniquely for this product, **the load test also asserts an LLM token/cost ceiling per job** — a regression that doubles tokens per analysis is a margin and billing-integrity failure, caught here, not on the invoice. Run against a staging/local target, never production with real keys.

---

## 7. Determinism and the flaky-test policy (zero tolerance)

- **No wall-clock, no unseeded randomness in tests.** `datetime.now()`, `time.time()`, `random`, and `uuid4()` make tests non-reproducible and intermittently red. Inject a fixed clock/seed (freeze time, seed the RNG, pass a deterministic id factory). A test that passes or fails depending on when it runs is not a test.
- **Flaky tests are QUARANTINED and FIXED — never retried-to-green.** A `pytest-rerunfailures`/`--reruns`-style "just run it again" hides a real race or ordering bug and trains everyone to ignore reds. Move the flaky test out of the gating suite into an explicit quarantine, **file a ticket, and fix the root cause** (usually shared state, an unseeded clock, or a missing `ROLLBACK`). Quarantine is a holding cell with an exit date, not a graveyard.
- **When a test surfaces real behavior ≠ expectation: fix the test AND comment WHY** (the SKILL.md rule). Understand the behavior first; if it's correct, encode why in a comment so the next reader doesn't "fix" it back. Never delete a failing test to make the bar green.
- **Test names state the expected behavior**, not the input: `test_denies_cross_tenant_read_returns_404`, not `test_isolation_3`. The name is the spec.

---

## 8. The pre-merge checklist (Definition of Done for tests)

A change is not done until, against the **real package** (not the shim) on a fresh ephemeral DB:

- [ ] New endpoint → contract + authz/isolation tests, with a DENY assertion.
- [ ] New RLS policy → pgTAP test with a positive AND a cross-tenant deny assertion (`databases.md`).
- [ ] New parser → malicious-input test that rejects the bomb cleanly (`secure-data-processing.md` §1).
- [ ] Bugfix → a regression test seen to FAIL on the unfixed code, then pass.
- [ ] Branch coverage gate green, per-package floor met (high on core/auth/RLS).
- [ ] pgTAP RLS suite + HTTP isolation suite green (the un-skippable gate, §2).
- [ ] `bandit`/secret-scan/dependency-scan green (`github-actions.md`).
- [ ] No real PII/evidence in any fixture; no wall-clock/unseeded randomness; no quarantined test in the gating set.
- [ ] A human reviewed the PR (CODEOWNER on sensitive paths) — not a blind agent self-merge (`github-teams.md`).

If any box is unchecked, the work is not delivered — it is at risk.
