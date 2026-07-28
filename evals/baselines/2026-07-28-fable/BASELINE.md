# Recorded baseline — 2026-07-28, Fable, 56-scenario suite (post-#120 main, harness v2)

The first **harness-v2** Fable baseline — the 2026-07-04 Fable sweep predates the
fixture/tool-grant harness and is not comparable (the 2026-07-05 discontinuity note
governs). Recorded against the full 56-scenario suite at the post-#120 tree (`a1ca858`:
skill content unchanged since v1.23.1; runner carries the NUL-argv fix), `claude` CLI
2.1.220, scenario model `fable`, judge model `opus`, `--timeout 1800` (the updated
recipe in this same PR), resumable per-scenario execution as disclosed in
`../2026-07-27-opus/BASELINE.md`.

**Disclosure — 21 usage-limit re-runs, not splices.** The first with-skill pass hit a
usage-limit window mid-sweep: 21 consecutive scenarios errored `claude exited 1` with no
CLI output. After the window rolled over (verified with a live probe), the 21 errored
results were deleted and re-run by the same driver into the same sweep dir — full
re-runs under identical flags, not curation-time splices; the bare sweep had zero
errors.

## Headline

| Run | pass | partial | fail | error |
|---|---|---|---|---|
| Bare model (`--mode baseline`) | 9 | 30 | 17 | 0 |
| With the skill (`--mode with-skill`) | **42** | **14** | **0** | 0 |

**The strongest with-skill result of any model on this suite — zero failures** —
alongside same-harness Opus (42/13/1) and Haiku (13/28/15) from 2026-07-27. Bare Fable
(9/30/17) sits between bare Haiku and bare Opus on pass count but carries more fails
than bare Opus: the skill closes all of them.
