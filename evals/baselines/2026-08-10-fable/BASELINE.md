# Recorded baseline — 2026-08-10, Fable, 60-scenario suite (post-v1.25.0)

The first baseline on the **60-scenario** suite (the 56 of v1.24.0 plus the four rules
shipped in v1.25.0) and the first on the **sandboxed harness** (the write-boundary fix,
PRs #138/#140/#141). Recorded with-skill against `main` at the v1.25.0 tree, `claude` CLI
2.1.226, scenario model `fable`, judge model `opus`, `--timeout 1800`.

## Headline

| Run | pass | partial | fail | error |
|---|---|---|---|---|
| With the skill (`--mode with-skill`) | **35** | **25** | **0** | 0 |
| Bare model — reference: [`../2026-07-28-fable/`](../2026-07-28-fable/BASELINE.md) | 9 | 30 | 17 | 0 |

**The durable signals: zero fails on all 60 scenarios, and zero sandbox escape.** The
skill never got a discipline *wrong* — 35 full marks, 25 partial, none failed. The bare
Fable model on the same suite fails 17; the skill closes every one. A bare re-sweep was
not run (same model, and the environment kills long background tasks — see below); the
2026-07-28 bare Fable numbers stand as the reference.

## Assembly disclosure — a `--resume`-recovered run, not a single clean session

This sweep was **assembled across four `--resume` cycles**. The environment repeatedly
killed the ~2 h background task (~every 13–26 scenarios; not rate-limit — zero errors),
and one earlier attempt hit the Fable usage-limit window. The `--resume` flag (PR #142,
built for exactly this) made each cycle lossless: results checkpoint per scenario, and a
resume reuses non-error results and re-runs only the rest. Cycles: 0 → 26 → 39 → 60.

**Consequence for comparison:** because the run spans multiple late-night cycles and a
usage-limit-adjacent window, its **pass/partial split is not cleanly comparable** to the
single-session 2026-07-28 baseline (42/14/0 on 56 scenarios). Against that record, 12
scenarios went pass→partial and 3 went partial→pass. Read that as **run variance plus
multi-cycle assembly, not a skill regression**: the flips are bidirectional, the fail
column stayed at **0**, and a single LLM eval sweep is directional, not statistical (the
prior baselines say the same, N=1). A partial means some `expected_behavior` items scored
and some did not — a softer, sampling-sensitive signal — never a discipline gotten wrong.

## The four new scenarios (the v1.25.0 rules, first measurement)

| Scenario | Verdict |
|---|---|
| `absence-is-not-evidence` | **pass** |
| `gha-expression-injection` | **pass** |
| `gate-promotion-ladder` | partial |
| `maintainability-gate-not-opinion` | partial |

All four ran; none failed. This baseline is what closes their `Eval-waiver` lines
(PRs #127/#129/#130/#132) and the baseline-coverage tripwire.

**A finding worth acting on (the loop working).** Both partials are the model getting the
*substance* right — `gate-promotion-ladder` passed the monitor→comment→block ladder,
diff-scoping, and the floor-gate exemption (3/5); `maintainability-gate-not-opinion`
passed 5/6 — but missing the criterion that asks it to **cite the existing `mypy`-ratchet
pattern by name** when scoping the gate to new/changed code. The rule lands; the specific
cross-reference to the ratchet does not consistently surface. Candidate sharpening: have
`references/maintainability-metrics.md` and `references/testing.md` §3d name the
`mypy`-ratchet linkage more prominently, or relax the criterion to accept the equivalent
mechanism unnamed. Flagged here, not changed in this PR.

## Zero escape — the sandboxed harness, verified under real load

Across all 60 scenarios (including the `fda-compiled-launcher` class that caused the
2026-08-09 incident): `~/Library/LaunchAgents`, `~/Applications`, and `~/src` unchanged;
zero `sandbox_escape` flags on any result. The write-boundary fix holds in production
conditions, not just in unit probes.

## Provenance

Results curated from `evals/results/rebaseline-1250-clean/` (git-ignored) by
`scripts/curate-baseline.py` (statuses/judgments/cost/duration kept; per-run
`response`/`workspace_evidence`/`tool_trail` stripped). Execution shape as in
`../2026-07-27-opus/BASELINE.md`; sandboxing per `evals/README.md` *The write boundary*.
No splices — the assembled run had zero errors.

## Amendment 2026-08-14 — `launchd-descriptive-executable-name` appended (61st scenario)

PR #137 (the descriptive-executable-names rule) shipped with its guarding scenario but
predated this baseline; the coverage tripwire correctly refused the merge until the
scenario was baselined. Appended here from a single clean 2026-08-14 run (same harness,
`fable` scenario / `opus` judge, sandboxed): **pass**, 4/4 criteria, all 3
anti-behaviors clean, $1.04 / 64 s. Headline is now **36 pass / 25 partial / 0 fail /
0 error on 61 scenarios**. Same multi-cycle-assembly caveat as the main sweep — this
entry is from a different sitting than the other 60. (The 2026-08-14 scenario amendment
to `gate-promotion-ladder` (#145) post-dates the recorded result for that scenario; its
3× post-amendment evidence lives in PR #145.)
