# Experiment record — tranche-5 core diet, REFUTED (2026-07-27)

**Hypothesis (2026-07-27 audit, HIGH-1 + MEDIUM-4):** compressing the always-loaded
SKILL.md core (12,490 → 8,630 body words, −31%, mechanics relocated to references) would
preserve with-skill eval performance — and might *improve* small-model rule-following by
reducing salience dilution.

**Result: refuted, on both models.** Same-day, same-harness, same-CLI (2.1.220),
same-judge (opus) with-skill sweeps, pre-diet core (v1.23.1 @ `6ced7f4`) vs post-diet
core (PR #119 branch `feat/core-diet-tranche5` @ `a8ae524`):

| Model | Pre-diet (baseline) | Post-diet (this dir) | Per-scenario |
|---|---|---|---|
| Opus | 42 / 13 / 1 | 38 / 15 / 3 | 4 improved, **7 regressed** |
| Haiku | 13 / 28 / 15 | 8 / 26 / 22 | 6 improved, **16 regressed** |

Opus regressions: `graceful-shutdown-sigterm`, `honest-badges-only`,
`readme-toc-anchor-validation`, `scm-triage-reviews-before-merge`,
`squash-not-rebase-merge`, `stateless-for-horizontal-scale`, `typecheck-gate-required`.

The post-diet sweeps ran with the *more generous* `--timeout 1800` (vs 900 pre-diet), so
timeouts cannot explain the drop — the bias runs the other way. The regressed scenarios
map directly onto the relocated content (honest-badges, readme-toc-anchor,
scm-triage-reviews, squash-not-rebase, citation-cff, preserve-input-on-failed-submit,
graceful-shutdown-sigterm, …): **the in-core mechanics were doing real work. In eval
conditions the model frequently acts without first reading the reference a trigger
points to, so a trigger-plus-pointer carries measurably less behavior than the inlined
rule.** MEDIUM-4's premise inverts for small models: Haiku leans on in-core detail
*more*, not less.

**Consequences:**

- PR #119 (the diet) stays unmerged; the core keeps its pre-diet density and the
  `CORE_WORD_BUDGET` ratchet stays at 12,700 (the diet branch's 8,900 ratchet dies with
  it). Token cost vs. behavior is now a *measured* trade: −31% tokens bought −5 pass on
  Opus and −5 pass on Haiku — a bad trade for a rigor skill.
- Any future compression must go through this same gate scenario-by-scenario (the
  candidate section's guarding scenarios must hold), not wholesale.
- Splice disclosed: `preserve-input-on-failed-submit` (opus) errored twice on
  `ValueError: embedded null byte` — model-produced NUL bytes riding into the judge's
  argv, a harness defect fixed at `_run_cli` (NUL → visible `\x00` escape; red/green
  proven, regression test in `scripts/tests/test-scripts.sh`). Re-run once on the fixed
  runner at the same skill content: **pass** (1,336s), spliced. The same defect explains
  the `csv-formula-injection-export` error in the pre-diet bare sweep.

Provenance: sweeps staged from the PR #119 worktree; results curated by
`scripts/curate-baseline.py`; execution shape as in `../2026-07-27-opus/BASELINE.md`.
This directory is an **experiment record, not a baseline** — the tripwire keys on
`with-skill.json`, which this dir deliberately does not contain.
