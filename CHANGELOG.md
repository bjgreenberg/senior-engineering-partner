# Changelog

All notable changes to the **senior-engineering-partner** skill are recorded here. The format
is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Releases are automated with [release-please](https://github.com/googleapis/release-please): it
reads the [Conventional Commits](https://www.conventionalcommits.org/) on `main`, opens a release
PR that bumps the `Version` in [`SKILL.md`](SKILL.md) and prepends the section below, and a
maintainer enriches that section's narrative before cutting the **signed** tag + GitHub Release
(see [`MAINTAINERS.md`](MAINTAINERS.md) → *Cutting a release*). The earlier entries were curated by
hand; the same "what changed and **why**" narrative is the goal going forward.

This skill was developed and battle-tested in real production work across many internal
revisions before its public release. The history below is the **public** changelog; earlier
internal-version specifics (private project names, hosts, and work history) are intentionally
omitted, and the universal core carries **zero** environment-specific detail — all of that lives
in your own `references/my-environment.md`.

## [1.7.0](https://github.com/bjgreenberg/senior-engineering-partner/compare/v1.6.0...v1.7.0) (2026-07-01)

A dogfooding release: the repo adopts the supply-chain + documentation disciplines the skill
teaches, then folds the lessons back in as new rules. It now runs **OpenSSF Scorecard** on
*itself* — the skill already told you to check a *dependency's* Scorecard; now it checks its own,
scoring **7/10** after a least-privilege fix — carries an honest, live badge row, and gained a
**required-badges** standard in `SKILL.md`. Every badge is true and live; no hardcoded "passing" shipped.

### Features

* **A live badge row is now required on every remote-backed repo — and only honest badges** ([#36](https://github.com/bjgreenberg/senior-engineering-partner/issues/36), [9fc2fcb](https://github.com/bjgreenberg/senior-engineering-partner/commit/9fc2fcb3f1580d141e77ce85afa1b2b93aab228b); discipline [#33](https://github.com/bjgreenberg/senior-engineering-partner/issues/33); repo's own row [#29](https://github.com/bjgreenberg/senior-engineering-partner/issues/29)). Every repo with a remote gets a badge row from day one — the same "standard, not a flourish" posture as branch protection: a **live** CI-status `badge.svg`, license, latest release, and (public repos) an OpenSSF Scorecard posture badge. The honesty rule rides with it — a badge is a *claim*, so never a hardcoded `passing`, a coverage badge with no coverage, an SLSA/SBOM badge with no provenance, or a drifting version; a false badge is the same stale-claim failure as a wrong diagram. Every badge URL is verified live before it ships.
* **OpenSSF Scorecard, run on our own repo — not just our dependencies** ([#30](https://github.com/bjgreenberg/senior-engineering-partner/issues/30), [9edc4e0](https://github.com/bjgreenberg/senior-engineering-partner/commit/9edc4e0969c32052a70de10db5ee27c9cb7b46b2); docs [#33](https://github.com/bjgreenberg/senior-engineering-partner/issues/33)). `foss-adoption.md` used Scorecard to vet an *inbound* dependency; `compliance.md` now documents it as **bidirectional** — the same tool run on your own repo is a supply-chain posture self-assessment, published as a public score the badge reads. Captures the gotchas learned firsthand: keep the workflow minimal (`checkout` + `scorecard-action`), SHA-pin the actions, and skip the optional SARIF upload whose codeql-action pin scorecard's publish verification rejects as an "imposter commit."

### Bug Fixes

* **Least-privilege release-please permissions** ([#34](https://github.com/bjgreenberg/senior-engineering-partner/issues/34), [836d0f4](https://github.com/bjgreenberg/senior-engineering-partner/commit/836d0f4a5014b5dcb09d220412018f520ee40b75)). Moved `contents`/`pull-requests` write from the workflow top level to the job — the skill's own `github-actions.md` rule, and a self-inconsistency it fixes. Lifted Scorecard's Token-Permissions check from **0 to 10** (7/10 overall).
* **Minimal Scorecard workflow — fix the broken publish** ([#32](https://github.com/bjgreenberg/senior-engineering-partner/issues/32), [933473e](https://github.com/bjgreenberg/senior-engineering-partner/commit/933473ee8fd256799231e393320fc2a8e4460a72)). The first run analyzed fine but failed to publish; dropping the optional SARIF→code-scanning step (the "imposter commit" above) fixed it and shrank the third-party action surface.

## [1.6.0](https://github.com/bjgreenberg/senior-engineering-partner/compare/v1.5.0...v1.6.0) (2026-07-01)

A comparative-analysis release. After a deep read of an external multi-agent coding-standards
system, this pulls in the disciplines that genuinely sharpen a **prose, advisory** skill — and
deliberately leaves out what doesn't fit one: a machine-readable standards *format* that is inert
without an orchestrator to enforce it, and a full product-lifecycle. Five load-bearing additions,
each guarded by an eval; an independent baseline-vs-with-skill run confirmed two close a real gap a
strong model misses (the CSV-injection framing and the ADR-floor line) while the rest hold as
regression guards. (Plus a documentation-accuracy sweep — the review-model note, the
architecture-diagram counts, and the reference catalog — in #23–#25.)

### Features

* **Reuse-first, rule-of-three, and YAGNI, named in the modular-code discipline** ([#18](https://github.com/bjgreenberg/senior-engineering-partner/issues/18), [54bdfb3](https://github.com/bjgreenberg/senior-engineering-partner/commit/54bdfb3943680ad2b330ef958c0783ebe3fa42ad)). The section had a "don't reinvent" nudge but never named the three bedrock rules a senior reviewer applies at code-time: reuse before writing new, abstract only at the second-or-third concrete caller (not the first), and no speculative generality — no parameters/hooks/extension points for features nobody has asked for. Unused flexibility is dead code; this is *don't widen scope silently* applied to design.
* **ADRs name the discipline they waive; the floor is never ADR-overridable** ([#21](https://github.com/bjgreenberg/senior-engineering-partner/issues/21), [6525714](https://github.com/bjgreenberg/senior-engineering-partner/commit/65257146de8f2dd5854594fcaa1ff7388aed3306)). An ADR that deviates from a standing discipline must cite the *specific* rule it overrides — an exception becomes auditable, not silent drift — and the security/CIA floor (secrets, input validation, injection prevention, isolation, authn, tenant RLS) can never be waived by one; only tier-scaled rigor can. "Internal / behind auth / just an MVP" does not move the floor. Also adds the human-review hard-block (an unresolved `CHANGES_REQUESTED` outranks green CI and a bot `APPROVE`) and a CONTRIBUTING "authoring a discipline" convention (binary / diff-checkable / timeless — the skill's falsifiability standard applied to rule-writing).
* **New `standards-authoring.md` reference — distill sprawling conventions into checkable rules** ([#22](https://github.com/bjgreenberg/senior-engineering-partner/issues/22), [5eff0a5](https://github.com/bjgreenberg/senior-engineering-partner/commit/5eff0a590c70cb16dd49cb9a48316065bf64dc5e)). The inverse of the rest of the skill: instead of *applying* standards, a guided procedure to turn a project's scattered conventions (a 2,000-line `CLAUDE.md`, `.cursorrules`, `*_guidelines.md`) into an enforceable set — discover sources (prose *and* ground-truth artifacts), filter (timeless / enforceable / dedup), take per-rule human approval (write nothing unapproved), classify floor-vs-overridable. Prose-first and format-agnostic: a machine-checkable JSON+validator set only where CI will actually enforce it.


### Bug Fixes

* **Spreadsheet/CSV formula injection on export, and SSRF as a first-class API7** ([#19](https://github.com/bjgreenberg/senior-engineering-partner/issues/19), [8f887b0](https://github.com/bjgreenberg/senior-engineering-partner/commit/8f887b0adc9b1a85b7b9f9cccd5be83f97df4dfb)). Two output/boundary gaps the skill left implicit outside the Apps Script context. CSV formula injection (CWE-1236) is a *distinct output sink* from HTML escaping — a cell beginning `=`/`+`/`-`/`@` executes as a formula in Excel/Sheets/LibreOffice — now covered in `frontend-web-security.md` §3 as the export context of encode-per-context. And a general user-supplied-URL SSRF (allowlist the destination, block link-local/metadata + private ranges, re-validate after redirects) now has its own row in the OWASP API Top-10 map as **API7:2023**.
* **Fail closed — never return a swallowed error as a success-shaped empty/default** ([#20](https://github.com/bjgreenberg/senior-engineering-partner/issues/20), [fbb9b70](https://github.com/bjgreenberg/senior-engineering-partner/commit/fbb9b70d7de7f0a5562d4d0e5e3eda86209b7953)). `resilience-engineering.md` already had "fail clear, never silent" and safe-labeled fallbacks; the subtle gap was the *success-shaped* failure — an `except: return []` / `return None` that makes a *failed* call read as a legitimately-empty one, so bad data flows on unnoticed. Sharpens the existing rule (rather than adding a redundant one) to fail closed by default, degrading only through a deliberate, labeled fallback — reconciling "degrade, don't die" with "fail closed."

## [1.5.0](https://github.com/bjgreenberg/senior-engineering-partner/compare/v1.4.0...v1.5.0) (2026-06-30)

Dogfooding again: two PRs' worth of lessons from a real build session where a **fully green test
suite still shipped a broken integration**, plus an escalation of the verification step itself.

### Features

* **Consumer-side contract testing — and "test the decision, not the component it renders"** ([#16](https://github.com/bjgreenberg/senior-engineering-partner/issues/16), [aeee0e5](https://github.com/bjgreenberg/senior-engineering-partner/commit/aeee0e506f9e5eb662104cb66325239ed969e01f)). A new-user flow shipped broken past a green suite: the UI was coded and mocked against an *assumed* response (`200`-with-empty) while the server correctly returned `403` — a false green no unit test caught. `references/testing.md` now requires a consumer's mock to encode the producer's **real** responses (status codes *and* error bodies), or a thin integration test across the seam — contract drift cuts both ways. And it calls out the sibling miss: a "thin" route/handler still owns the branch *decision* (which state to show, how to classify an error), so that logic must be extracted and tested — "the components are tested" is not "the orchestration is tested."
* **The runnable setup is documentation too** ([#16](https://github.com/bjgreenberg/senior-engineering-partner/issues/16), [aeee0e5](https://github.com/bjgreenberg/senior-engineering-partner/commit/aeee0e506f9e5eb662104cb66325239ed969e01f)). A required config var that never reached the dev compose crashed `docker compose up` at boot, long after the test suite was green. The documentation discipline (SKILL.md) now treats **every launch surface** — compose files, env templates, deploy manifests, the README quickstart — as documentation that must move in lockstep when a new required var is added, and treats the quickstart as a *verifiable* artifact you actually run before claiming it works.
* **Adversarial multi-lens verification for high-stakes diffs** ([#15](https://github.com/bjgreenberg/senior-engineering-partner/issues/15), [bf9f7db](https://github.com/bjgreenberg/senior-engineering-partner/commit/bf9f7db9cabbb92a995282d25a27a7e7edea866a)). The "verify before done" step now escalates a Tier-2 / security- or isolation-sensitive change to several independent, refute-first lenses — then re-reviews whatever folding the findings introduced. That loop is what catches a *green-but-insufficient* change (passes every gate, reads as correct, yet misses its scoped goal) that a single confirmatory read sails past. A multi-lens panel on a trivial diff is review-theater — match the breadth to the stakes.

## [1.4.0] - 2026-06-29 — Dogfooding: file-sync repo corruption, scheduled-job catch-up, infra-doc discipline

Three generalizable lessons that surfaced running the skill against a real multi-machine fleet migration:
- **`dev-environment-isolation.md` (new §2 subsection) + ENVIRONMENT ISOLATION floor — never host a live `.git` in a file-sync tree.** A file-syncer (iCloud "Desktop & Documents", Dropbox, OneDrive) replicating a live repo *corrupts* it — concurrent `.git` writes, half-synced pack/ref/lock files, online-only eviction of `.git` objects, conflict copies — a **distinct** failure from "sync ≠ backup" (which is about a sync propagating a bad change). Fix: repos in a non-synced path, synced via git push/pull; if a sync tree must contain one, relocate it out and leave a symlink (verify the sync tool's symlink behavior with a scratch test first).
- **`resilience-engineering.md` (new §5) — scheduled work must catch up after downtime.** Wall-clock schedulers (`cron`, launchd `StartCalendarInterval`, systemd calendar timers) silently **skip** runs missed while the host was off/asleep, not defer them. Pair the wall-clock trigger with an elapsed-time catch-up trigger + an **idempotent due-gate**, and compute "is a run outstanding?" the same way in the gate and in whatever heartbeat monitors the job (a no-op catch-up run must write nothing, so it can't reset the monitor's signal).
- **SKILL.md DOCUMENTATION — "every representation" now names infra/environment/layout docs.** A doc you *read* to understand a change is one you must update — including the environment/host profiles and directory-layout indexes that describe *how things are wired*, not just code-level docs.

## [1.3.1] - 2026-06-29 — Fix-at-source discipline + a portability correction

Small follow-on, itself an instance of the discipline it adds — issues caught while shipping v1.3.0, fixed at the source instead of deferred:
- **"Fix it at the source the moment you trip over it" (`engineering-workflow.md` §5).** Names the default that pairs with the existing defer-register: when work surfaces a *different* small fixable problem (a latent bug, a stale comment, a guard false-positive), fix it **now at its root** while the context is loaded, rather than papering over it locally or filing it for a "later" that compounds — the proactive twin of `debugging.md`'s fix-the-cause-not-the-symptom. Guardrails: keep it in its own commit; in a shared tree, flag a problem belonging to *another's* in-flight work to its owner rather than absorbing it (`multi-agent-coordination.md`). Deferral (with a tracked trigger) is the exception, for what genuinely can't be fixed in-flight.
- **Portability correction (`debugging.md`).** The v1.3.0 non-ASCII-byte tell suggested `grep -nP` unqualified; `-P` is GNU/ripgrep-only (not stock macOS/BSD grep), so it's now labelled as such with `cat -v`/`hexdump -C` as the portable primaries — honoring the skill's own "don't suggest a flag that may not exist" rule.

## [1.3.0] - 2026-06-29 — Dogfooding: test/prod privilege-parity + gate-construction lessons

Additions from building an **RLS production-parity gate** for the multi-tenant codebase — lessons that only surface when you write a security gate end-to-end, including a blind spot in the skill's *own* RLS-testing guidance:
- **Test/prod privilege parity (`databases.md`, the headline).** The skill mandated pgTAP RLS testing but its documented pattern *seeds/migrates as the superuser* — which silently can't verify the production invariant, because a superuser bypasses RLS unconditionally while production (Cloud SQL/RDS, no true superuser) relies on a **non-superuser owner's `BYPASSRLS`** attribute. Generalized: *a test harness running with more privilege than production cannot verify a security invariant that depends on the privilege difference.* Fix = a **production-parity gate** that re-runs the suite under the prod privilege model (non-superuser `BYPASSRLS` owner), with the `CREATE EXTENSION`-needs-superuser pre-create gotcha called out. Cross-referenced from `testing.md` §2 and the `audit-report-format.md` test/prod-parity flag (now with the privilege sub-case + remediation).
- **Gate-construction principles (`testing.md` §3c).** Three rules that generalize "red-first" from a single test to a whole gate: **(1)** a gate must be able to *fail* — build a fail-first negative and invert the assertion so a passing negative fails the gate (a green that can't go red proves nothing); **(2)** a gate must **assert** its preconditions (role attributes, object ownership, versions), not just print them, or a refactor passes it for the wrong reason; **(3)** trust the tool's own *verdict* signal, not a bare non-zero exit, so an infra failure can't masquerade as the proof you wanted.
- **`docker compose run` recreates a `depends_on` service — CI-only (`containers-and-orchestration.md`).** An ephemeral gate that bootstraps a dependency out of band (`up -d db` → seed → `compose run migrator`) can have that dependency **recreated** by `compose run` on the CI runner (not on local Docker Desktop/OrbStack — a works-on-my-machine trap), wiping the bootstrap. Use **`--no-deps`** when you own the dependency's lifecycle.
- **Suspect the bytes when a symbol is unimpeachable (`debugging.md`).** A bash `unbound variable` on a variable you clearly set can be a non-ASCII character (smart quote, em-dash, ellipsis) adjacent to `$var` whose leading UTF-8 byte folds into the name; keep shell scripts ASCII, and `cat -v`/`hexdump` reveals it.
- **New eval** `evals/scenarios/rls-superuser-parity-gate.json` encoding the headline lesson so it can't silently regress.

## [1.2.0] - 2026-06-29 — Dogfooding: `AUDIT:` mode + lessons from a real codebase audit

Additions from applying the skill to a full senior audit of a real multi-tenant codebase — gaps the prior evaluation didn't surface because they only appear when the skill drives an actual end-to-end audit-and-remediate workstream:
- **New `AUDIT:` mode** — a sixth trigger for a **report-first, whole-codebase audit**. `REVIEW:` mandates "a senior engineer who spots a fix delivers it," which actively fights a repo-wide audit where the deliverable is a severity-ranked report and the user picks what to fix; conflating the two buried findings in unrequested diffs. `AUDIT:` is report-only, mechanize-the-checkable, `file:line`-evidenced, strengths-included, then drop into `REVIEW:`/`DEBUG:` to implement. Added to the `description` triggers.
- **New `references/audit-report-format.md`** — the finding schema, the CRITICAL/HIGH/MEDIUM/LOW severity taxonomy (with the *test/prod-parity* and *deferred-but-gating* cross-cutting flags), and the report structure, so audits are comparable and every finding is falsifiable. Closes the "no findings-report template / severity taxonomy" gap.
- **Push-only CI steps can red-fail `main` invisibly** (`github-actions.md`) — a step gated `if: github.event_name == 'push'` (attestation, deploy, release-cut) is never exercised by a PR run, so a structurally-broken one (e.g. build-provenance attestation on a user-owned **private** repo) keeps every PR green and red-fails every merge. Make such steps non-blocking / condition-gated, and verify them once via `workflow_dispatch`.
- **Prefer `git grep` for tree sweeps** (EPISTEMIC DISCIPLINE) — an unquoted `grep -r --include=*.py` is glob-expanded by zsh and silently matches nothing (a false "verified absent"); quote the pattern or use `git grep`.

## [1.1.0] - 2026-06-28 — Evaluation follow-ups

Fixes from a full skill self-evaluation. Privacy & authoring correctness first:
- **Two-tier `leakage-guard`.** Generic class-patterns (a CGNAT/Tailscale IP range, Obsidian-style
  wiki-links) stay in the public `scripts/leakage-guard.sh` and run in CI; your *literal* identifiers now live in
  an un-committed `references/leakage-denylist.local` (from a new `.template`), so the public repo no
  longer has to publish hostnames/employer/repo names in order to block them.
- **Frontmatter `description` trimmed to ≤1024 chars** (was ~1.6k, over Anthropic's hard limit) — kept
  the role, languages, `Use when`, and the mode triggers; moved the framework enumeration to the body.
- **Fixed the `render-diagrams.sh` digest comment** (it claimed to ship no digest while pinning one; the
  pinned digest is published — the comment was wrong, not the pin).
- Noted that eval `source` version tokens (`v2.x–v6.x`) are pre-release provenance, not public versions.

Content additions (from the evaluation's scope/security-framework findings):
- **New `references/google-apps-script.md`** — `clasp`+git, minimal `oauthScopes`, `PropertiesService` secrets/limits, `LockService`, trigger quotas + the 6-min wall, pure-logic isolation for testing (+ a guarding eval). GAS is a headline language that lacked a reference.
- **New `references/javascript-and-typescript.md`** — TS strict mode (the `mypy --strict` analog), runtime-validated typed boundaries (the Pydantic analog), Node `SIGTERM`/no-floating-promises patterns. Closes the TS-typing gap.
- **Named the framework mappings** the skill already implements: **OWASP LLM Top 10 (2025)** in `secure-data-processing.md` and **OWASP API Security Top 10 (2023)** (API1 BOLA ≠ web A01) in `threat-modeling-and-api-design.md`.
- **Profile-before-you-optimize** discipline (`debugging.md`); **legacy-refactor + tech-debt register** (`engineering-workflow.md`); **systems-theory naming** — feedback loops, Senge archetypes, iceberg/Cynefin, Conway's Law, Safety-II — across the relevant references.
- **Compliance one-liners**: PCI-DSS scope posture (`compliance.md`), NIST AI RMF / ISO 42001 pointers, and an explicit i18n non-goal (`ui-design-and-accessibility.md`).
- **Repo/community:** README "What it governs" coverage section, a `MAINTAINERS.md`, and CODEOWNERS updated for a second maintainer (two-tier leakage model + admin-bypass review flow documented).

## [1.0.0] - 2026-06-25 — Initial public release

- First public, sanitized release: a **stack-agnostic universal core** (`SKILL.md`, always
  loaded) + a **swappable environment profile** (`references/my-environment.md`, copied from the
  shipped template) + a library of read-on-demand `references/`. Re-home the skill by editing one
  file.
- Ships `scripts/` (dependency-audit, Mermaid render-check, self-review checklist), an `evals/`
  regression suite (each scenario encodes a checkable engineering lesson), and CI that
  render-checks diagrams and guards against environment-specific leakage.

## Pre-release evolution (sanitized summary)

The skill grew from a focused reviewer / pair-programmer / mentor into a full engineering-discipline
system. The arc, with all specifics removed:

- **Foundations** — the mode triggers (`REVIEW:`/`EXPLAIN:`/`MVP:`/`DEBUG:` + default pair
  programmer); a secrets-manager security floor (no hardcoded secrets); PEP 8 + type hints;
  pytest/Jest/BATS; `bandit`/ShellCheck; pinned dependencies; modular code; README + CHANGELOG
  standards; Conventional Commits.
- **Typing & architecture** — a `TypedDict` mandate (no `dict[str, Any]` black holes), the
  single-file-vs-package decision framework, and a testing pattern for single-file scripts.
- **macOS & ops hardening** — LaunchAgent `.app`-bundle / TCC standards (least-privilege Full Disk
  Access, the compiled-launcher requirement), Bash command-injection prevention, structured-logging
  location/rotation, and unattended-job monitoring with a dead-man's-switch.
- **Epistemic discipline** — verify-before-asserting (anti-hallucination) and deterministic-first
  (mechanize anything checkable rather than reasoning it out token-by-token).
- **Process layer** — the spec → plan → tier-aware iron-law TDD → verify-before-done self-review
  workflow, plus the `DEBUG:` root-cause method (reproduce → hypothesize → isolate → fix cause →
  red-first regression test).
- **Phase-aware rigor ladder** — Prototype → MVP → Production, with a security/CIA floor (and a
  backup/continuity floor) that holds at every tier; only verification depth scales.
- **Toolchain depth** — Docker/Kubernetes, GCP/Cloud Run, databases (Postgres/Supabase RLS,
  BigQuery, SQLite), FastAPI, GitHub Actions, and compliance mappings (NIST CSF 2.0 + SSDF, OWASP,
  SOC 2, Well-Architected).
- **Supply-chain & security gates** — SAST + secret-scanning + manifest-level dependency-audit +
  type-check gates as merge blockers; pin **and** hash-lock fetched inputs; emit an SBOM + SLSA
  build provenance on outputs.
- **Reliability & continuity** — disaster recovery (3-2-1-1-0 immutable backups, scheduled restore
  drills), business continuity (BIA-justified RTO/RPO, provider-outage and bus-factor planning),
  resilience engineering (timeouts, circuit breaker, bulkhead, load-shed, designed degraded modes),
  and scalability/system design (statelessness, queues + DLQ, the transactional outbox).
- **Privacy, threat modeling & API design** — GDPR/CCPA-as-code (DSAR, erasure cascade, retention),
  in-PR STRIDE threat models, and attack-surface-shrinking API design.
- **UI & docs** — responsive, light/dark, **WCAG 2.2 AA** accessibility; diagrams-as-code
  (Mermaid-first, render-checked before commit) kept in lockstep with the code they depict.
- **Self-tests** — an `evals/` suite that encodes each hard-won lesson as a checkable scenario, so a
  discipline can't silently regress.
- **Portability** — restructured into a universal core + a swappable environment profile; this
  public release completes that separation so the core is fully reusable by anyone.
