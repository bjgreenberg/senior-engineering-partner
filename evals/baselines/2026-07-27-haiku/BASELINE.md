# Recorded baseline — 2026-07-27, Haiku, 56-scenario suite (skill v1.23.1, harness v2)

The first **harness-v2** small-model baseline — the 2026-07-04 per-model sweeps
(including Haiku) predate the fixture/tool-grant harness and are not comparable (the
discontinuity note in the 2026-07-05 Opus BASELINE.md governs). This is the "before" leg
of the MEDIUM-4 experiment from the 2026-07-27 audit: measure Haiku against the
**pre-diet** 12,490-word core, then re-measure after the tranche-5 core diet to test
whether a smaller always-loaded core improves small-model rule-following.

Produced by `scripts/run-evals.py` at the same content and recipe as the same-day Opus
baseline (skill v1.23.1; `claude` CLI 2.1.220; scenario model `haiku`, judge model
`opus`; `--timeout 900`; bare then with-skill; the same disclosed resumable execution
shape — see `../2026-07-27-opus/BASELINE.md`). No splices: zero harness errors in either
Haiku sweep.

## Headline

| Run | pass | partial | fail | error |
|---|---|---|---|---|
| Bare model (`--mode baseline`) | 1 | 21 | 34 | 0 |
| With the skill (`--mode with-skill`) | **13** | **28** | **15** | 0 |

The skill moves Haiku strongly (fail 34 → 15, pass 1 → 13) but leaves a large gap to
Opus with-skill on the identical suite — the small-model salience problem the core diet
targets. The post-diet Haiku sweep recorded alongside the tranche-5 PR is the other half
of this measurement.
