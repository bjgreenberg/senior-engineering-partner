# Recorded baseline — 2026-07-02, Opus 4.8, 38-scenario suite (skill v1.12.0)

The post-A1 re-baseline: the reference measurement taken **after** the SKILL.md
token-mass reduction (tranches 1–3, v1.9.0–v1.12.0) and **before** the Phase-3
portability pass, replacing [`2026-07-01-opus/`](../2026-07-01-opus/BASELINE.md)
(31 scenarios @ v1.8.0 — 7 scenarios were unbaselined and 5 had post-baseline
edits). Produced by `scripts/run-evals.py` at main `15fa728` (scenario runs `--model opus`,
judge runs `--judge-model opus`; `claude` CLI 2.1.197, jobs=2); scenario responses are stripped from
the committed JSONs (statuses + per-item judgments + judge reasons kept — re-run the
sweep to regenerate full transcripts locally under the git-ignored `evals/results/`).

## Headline

| Run | pass | partial | fail | error |
|---|---|---|---|---|
| Bare model (`--mode baseline`) | 5 | 20 | 13 | 0 |
| With the skill (`--mode with-skill`) | **20** | 14 | **4** | 0 |

**Per-scenario: 20 improved with the skill, 18 unchanged, 0 regressed.**

## Gap table (baseline → with-skill)

**Improved (20):** adr-must-name-overridden-discipline (fail→pass) ·
apps-script-least-privilege-scope (fail→partial) · badge-row-required-on-repo
(partial→pass) · crypto-agility-pqc-hndl (fail→partial) ·
dependency-currency-not-just-pinned (partial→pass) · fda-compiled-launcher
(fail→partial) · graceful-shutdown-sigterm (fail→pass) · honest-badges-only
(partial→pass) · immutable-backup-not-just-versioning (partial→pass) ·
log-injection-sanitize (partial→pass) · preserve-input-on-failed-submit
(fail→partial) · scm-triage-reviews-before-merge (partial→pass) ·
secrets-never-hardcoded (partial→pass) · spec-first-gate (partial→pass) ·
squash-not-rebase-merge (fail→partial) · standards-authoring-timeless-enforceable
(partial→pass) · stateless-for-horizontal-scale (fail→pass) ·
typecheck-gate-required (partial→pass) · typeddict-not-dict-any (fail→pass) ·
yagni-no-speculative-abstraction (partial→pass)

**Unchanged, already pass at baseline (5):** badge-verify-claimed-level-not-just-200 ·
bash-injection-eval · csv-formula-injection-export · debug-false-negative-search ·
fail-closed-not-degraded-success — Opus 4.8 does these natively.

**Unchanged, stuck at partial (9):** debug-root-cause-not-symptom ·
degrade-dont-crash-on-dependency-failure · llm-loop-stopping-criteria ·
restore-drill-required · rls-cross-tenant-deny · rls-superuser-parity-gate ·
sbom-provenance-on-release · scalability-db-pool-ceiling ·
single-file-vs-package-decision — the skill adds detail but doesn't clear the bar;
sharpening targets.

**Unchanged, stuck at fail (4):** adversarial-review-green-but-insufficient ·
dependency-manifest-drift · stale-diagram-on-behavior-change ·
tdd-regression-red-first. Single-probe re-runs at the same commit:
adversarial-review came back **partial** (variance-prone — it has oscillated
fail↔partial across recorded sweeps; treat single flips as noise), the other three
failed again (durable at this harness). stale-diagram and tdd-regression carry the
bare-cwd harness caveat below; dependency-manifest-drift and stale-diagram are the
clearest content gaps this baseline surfaces.

## Delta vs the 2026-07-01 (v1.8.0) baseline — read with care

Not like-for-like: the suite grew 31→38 and several scenarios were edited after
that baseline was taken, which is why this re-baseline exists. Directionally,
with-skill pass 16→20 and improved-count 16→20 on a larger suite;
dependency-manifest-drift and tdd-regression-red-first recorded partial-with-skill
at v1.8.0 but fail here (both re-probed, both durable) — candidates for the next
sharpening pass, not regressions attributable to a specific edit.

## Known harness caveats (read before comparing)

- Runs execute in a **bare temp directory** with the `Skill` tool disallowed; the
  skill body is injected via `--append-system-prompt` with its base directory
  pinned. Several `expected_behavior` items assume a real-repo interactive session
  (e.g. "updates the diagram in the same commit", "runs the test and watches it fail
  red"), which a bare-cwd run can only *describe*, not *do* — some partials/fails are
  harness fit, not skill defects. Compare like-for-like: always judge a SKILL.md
  edit by re-running **both** modes under this same harness.
- LLM-judge verdicts have run-to-run variance; treat single-scenario flips as noise
  and multi-scenario shifts as signal (adversarial-review-green-but-insufficient is
  the documented variance-prone case).
- The bare sweep's two alphabetically-last scenarios errored on the first pass (a
  transient CLI outage cluster — the account session limit); both were re-run via
  `--filter` into rerun dirs and merged per-scenario, per the documented recovery.
- This baseline covers the **38 scenarios present at v1.12.0**. Scenarios added or
  edited after it (see the suite's git history) aren't comparable against these
  numbers — the next full sweep re-baselines.
