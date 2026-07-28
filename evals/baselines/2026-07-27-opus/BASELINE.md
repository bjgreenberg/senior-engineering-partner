# Recorded baseline — 2026-07-27, Opus, 56-scenario suite (skill v1.23.1, harness v2)

The first baseline to cover the full 56-scenario suite — the 2026-07-05 Opus baseline
(45 scenarios) predates the 11 scenarios added for the Swift, agentic-AI,
appearance-control, credential-provisioning, TOC-anchor, self-improvement, and
always-check-the-logs disciplines, which had never been baselined until this sweep (the
gap the 2026-07-27 audit flagged as HIGH-2, now enforced by the baseline-coverage
tripwire in `scripts/tests/test-scripts.sh`).

Produced by `scripts/run-evals.py` against the **pre-diet** core (skill content as of
v1.23.1; tree between `6ced7f4` and `bff910b`, whose SKILL.md/references are identical —
`bff910b` changed CI scripts only). `claude` CLI 2.1.220, scenario + judge model `opus`,
`--timeout 900`, bare sweep first, then with-skill. **Execution shape disclosed:** the
first ~30 scenarios of each sweep ran `--jobs 2` in one process; the background runner
was repeatedly killed at its ~55-minute cap, so the remainder ran resumably — one
scenario per invocation (`--filter <name> --jobs 1`) into the same results dir, with
`summary.json` rebuilt from the per-scenario files. Same recipe, same staging per run;
only the process boundaries differ.

**Splices, disclosed (per the curate-baseline.py contract):**

- `csv-formula-injection-export` (bare sweep) errored on a harness-side
  `ValueError: embedded null byte` while collecting workspace evidence; re-run once at
  the same skill content, judged **pass**, spliced.
- `rls-cross-tenant-deny` (with-skill sweep) errored at the 900s timeout; re-run once at
  the same skill content, judged **partial**, spliced.
- `environment-binding-not-mandate` (with-skill sweep) hit `TimeoutExpired` at 900s
  **twice, reproducibly** — the scenario legitimately runs long under tool grants, not a
  flake. Re-run once with `--timeout 1800` (a harness-config change, not a grading
  change; completed in 1,189s), judged **pass**, spliced.

## Headline

| Run | pass | partial | fail | error |
|---|---|---|---|---|
| Bare model (`--mode baseline`) | 15 | 28 | 13 | 0 |
| With the skill (`--mode with-skill`) | **42** | **13** | **1** | 0 |

*(Table recomputed after splices; see the JSONs for per-scenario verdicts.)*

**Not comparable to the 2026-07-05 baseline as a time series** — different suite size
(56 vs 45), different CLI (2.1.220 vs 2.1.197), and a newer default `opus` snapshot; the
07-05 discontinuity rule applies. This baseline is the new comparison anchor, recorded
immediately **before** the tranche-5 core diet so the post-diet sweep has a same-day,
same-harness, same-model "before" leg.
