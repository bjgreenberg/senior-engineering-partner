# Recorded baseline — 2026-07-01, Opus 4.8, 31-scenario suite (skill v1.8.0)

The reference measurement taken **before** the planned SKILL.md restructuring (the
"token-mass reduction" phase), so that edit can be validated against a recorded bar
instead of hoped about. Produced by `scripts/run-evals.py` (runner and judge both
`--model opus`, `claude` CLI 2.1.197, jobs=2); scenario responses are stripped from the
committed JSONs (statuses + per-item judgments + judge reasons kept — re-run the sweep to
regenerate full transcripts locally under the git-ignored `evals/results/`).

## Headline

| Run | pass | partial | fail | error |
|---|---|---|---|---|
| Bare model (`--mode baseline`) | 6 | 16 | 9 | 0 |
| With the skill (`--mode with-skill`) | **16** | 14 | **1** | 0 |

**Per-scenario: 16 improved with the skill, 15 unchanged, 0 regressed.**

## Gap table (baseline → with-skill)

**Improved (16):** adr-must-name-overridden-discipline (partial→pass) ·
adversarial-review-green-but-insufficient (fail→partial) ·
apps-script-least-privilege-scope (fail→partial) · badge-row-required-on-repo
(fail→partial) · degrade-dont-crash-on-dependency-failure (partial→pass) ·
dependency-currency-not-just-pinned (partial→pass) · dependency-manifest-drift
(fail→partial) · fda-compiled-launcher (fail→partial) ·
immutable-backup-not-just-versioning (partial→pass) · restore-drill-required
(partial→pass) · secrets-never-hardcoded (partial→pass) · spec-first-gate (partial→pass) ·
standards-authoring-timeless-enforceable (fail→pass) · stateless-for-horizontal-scale
(fail→pass) · tdd-regression-red-first (fail→partial) · typecheck-gate-required
(partial→pass)

**Unchanged, already pass at baseline (6):** badge-verify-claimed-level-not-just-200 ·
bash-injection-eval · csv-formula-injection-export · fail-closed-not-degraded-success ·
log-injection-sanitize · yagni-no-speculative-abstraction — Opus 4.8 does these natively;
candidates for lighter treatment in the core.

**Unchanged, stuck at partial (8):** debug-root-cause-not-symptom ·
graceful-shutdown-sigterm · honest-badges-only · preserve-input-on-failed-submit ·
rls-cross-tenant-deny · rls-superuser-parity-gate · sbom-provenance-on-release ·
squash-not-rebase-merge — the skill adds detail but doesn't clear the bar; sharpening
targets.

**Unchanged, stuck at fail (1):** stale-diagram-on-behavior-change — the same-commit
docs-update discipline does not land even with the skill injected. The clearest single
content gap this baseline surfaced.

## Known harness caveats (read before comparing)

- Runs execute in a **bare temp directory** with the `Skill` tool disallowed; the skill
  body is injected via `--append-system-prompt` with its base directory pinned. Several
  `expected_behavior` items assume a real-repo interactive session (e.g. "updates the
  diagram in the same commit"), which a bare-cwd run can only *describe*, not *do* — some
  partials are harness fit, not skill defects. Compare like-for-like: always judge a
  SKILL.md edit by re-running **both** modes under this same harness.
- LLM-judge verdicts have run-to-run variance; treat single-scenario flips as noise and
  multi-scenario shifts as signal.
- This baseline covers the **31 scenarios present at v1.8.0**. Scenarios added or edited
  after it (see the suite's git history) aren't comparable against these numbers — the
  next full sweep re-baselines.
