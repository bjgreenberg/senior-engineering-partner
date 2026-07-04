# Recorded baseline — 2026-07-04, Sonnet 5, 45-scenario suite (skill v1.15.0)

The Sonnet leg of the 2026-07-04 per-model portability sweeps (siblings:
[`2026-07-04-haiku/`](../2026-07-04-haiku/BASELINE.md), Fable same day; the Opus
reference is [`2026-07-02-opus/`](../2026-07-02-opus/BASELINE.md), on the
then-38-scenario suite — deltas against it are directional, not like-for-like).
Produced by `scripts/run-evals.py` at branch commit `7c859f8` (scenario runs
`--model sonnet`, judge runs `--judge-model opus`; `claude` CLI 2.1.201, jobs=4);
scenario responses are stripped from the committed JSONs (statuses + per-item
judgments + judge reasons kept — re-run the sweep to regenerate full transcripts
locally under the git-ignored `evals/results/`).

## Headline

| Run | pass | partial | fail | error |
|---|---|---|---|---|
| Bare model (`--mode baseline`) | 6 | 27 | 12 | 0 |
| With the skill (`--mode with-skill`) | **16** | 22 | **7** | 0 |

**Per-scenario: 14 improved with the skill, 31 unchanged, 0 regressed.**

## Gap table (baseline → with-skill)

**Improved (14):** adr-must-name-overridden-discipline (partial→pass) ·
apps-script-least-privilege-scope (fail→partial) · bash-strict-mode-pitfalls
(fail→pass) · environment-binding-not-mandate (partial→pass) ·
fail-closed-not-degraded-success (partial→pass) · fda-compiled-launcher
(fail→partial) · frontend-testing-behavior-not-implementation (partial→pass) ·
immutable-backup-not-just-versioning (partial→pass) · preserve-input-on-failed-submit
(fail→partial) · prompt-injection-structural-fence (partial→pass) ·
rag-vector-store-tenant-isolation (partial→pass) · scm-triage-reviews-before-merge
(partial→pass) · typecheck-gate-required (partial→pass) · typeddict-not-dict-any
(fail→partial)

**Unchanged, already pass at baseline (6):** badge-verify-claimed-level-not-just-200 ·
bash-injection-eval · csv-formula-injection-export ·
host-os-binding-logs-and-least-privilege · log-injection-sanitize ·
standards-authoring-timeless-enforceable.

**Unchanged, stuck at partial (18):** citation-cff-no-hand-maintained-version ·
crypto-agility-pqc-hndl · debug-false-negative-search · debug-root-cause-not-symptom ·
degrade-dont-crash-on-dependency-failure · dependency-currency-not-just-pinned ·
honest-badges-only · llm-loop-stopping-criteria · restore-drill-required ·
rls-cross-tenant-deny · rls-superuser-parity-gate · sbom-provenance-on-release ·
scalability-db-pool-ceiling · secrets-never-hardcoded · single-file-vs-package-decision ·
spec-first-gate · squash-not-rebase-merge · yagni-no-speculative-abstraction.

**Unchanged, stuck at fail (7):** adversarial-review-green-but-insufficient ·
badge-row-required-on-repo · dependency-manifest-drift · graceful-shutdown-sigterm ·
stale-diagram-on-behavior-change · stateless-for-horizontal-scale ·
tdd-regression-red-first.

## What this baseline says about cross-model portability

Sonnet sits cleanly between Haiku and Opus: with-skill fails land at 7 (Haiku 16,
Opus 4 on the older suite), with zero regressions. The sharper signal is in *which*
fails persist: **four of Sonnet's seven stuck-fails are the same durable fails the
Opus baseline recorded** (adversarial-review-green-but-insufficient ·
dependency-manifest-drift · stale-diagram-on-behavior-change ·
tdd-regression-red-first) — those are **content/harness gaps the skill hasn't closed
on any model**, and they remain the sharpening targets. The remaining three
(badge-row-required-on-repo · graceful-shutdown-sigterm ·
stateless-for-horizontal-scale) are **model-capability gaps**: Opus clears them with
the same skill text. Reading across the three same-day sweeps, the with-skill quality
gradient tracks model tier even though the loaded content is identical.

## Harness caveats

Same harness as the Opus baseline: scenarios run in a bare scratch cwd (scenarios that
presume an existing tree read worse than real use); the `Skill` tool is disallowed and
the body is injected via `--append-system-prompt`. See the Haiku sibling for the
spec-first-vs-single-shot caveat (a skill-prompted clarifying question scores as
non-delivery in a one-turn judge).
