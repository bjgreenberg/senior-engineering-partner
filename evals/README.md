# Evals for senior-engineering-partner

Last updated: 2026-07-04 01:11 PM CDT

A regression suite for the skill itself. Each scenario encodes a **real miss** the skill exists to
prevent — most are drawn straight from the SKILL.md changelog — so the suite is the executable form of
"this must never happen again." Anthropic's own most-emphasized authoring practice is *build evaluations
first*; this brings the skill into line with it (the changelog was the spec; these are the tests).

## Why this exists

The changelog is a list of lessons in prose. Prose doesn't fail a build. An eval scenario is the same
lesson as a **checkable expectation**: run the query against a fresh Claude with the skill loaded, and
confirm the `expected_behavior` holds. When a future skill edit (or a model change) regresses a discipline,
the matching scenario catches it instead of a production incident re-teaching the lesson.

## Structure

`scenarios/*.json` — one scenario per file, in Anthropic's evaluation shape:

```json
{
  "skills": ["senior-engineering-partner"],
  "query": "the user prompt to run",
  "files": [],
  "expected_behavior": [
    "an observable, checkable thing the response must do",
    "..."
  ],
  "anti_behavior": ["things the response must NOT do"],
  "source": "changelog vX.Y / discipline it guards"
}
```

`anti_behavior` and `source` are local extensions (Anthropic's base shape is `skills`/`query`/`files`/
`expected_behavior`); they make the "never do this again" framing explicit and trace each scenario to its
origin.

> **Note on the `source` version tokens.** Some `source` fields cite internal pre-release revisions
> (e.g. `v4.0`, `v5.4`) that predate the public `v1.0.0` release and intentionally do **not** appear in
> the SKILL.md changelog — treat them as provenance notes, not resolvable versions.

## How to run

**`scripts/run-evals.py` executes the suite.** It needs only the `claude` CLI on PATH
(authenticated — no API key, no third-party deps): each scenario's `query` runs headlessly
(`claude -p`), an LLM judge grades the response against every `expected_behavior` and
`anti_behavior` item, and the overall pass/partial/fail verdict is computed
**deterministically** from the per-item judgments (any `anti_behavior` violation fails the
scenario; the judge grades items, it does not decide verdicts).

```bash
# One scenario, quick check
scripts/run-evals.py --filter spec-first-gate

# Full baseline sweep (bare model, no skill) — record what the skill must close
scripts/run-evals.py --mode baseline --model opus

# Full with-skill sweep
scripts/run-evals.py --model opus --judge-model opus
```

Two run modes, both deterministic about activation (the `Skill` tool is disallowed in every
run, so a user-level install can't auto-activate and contaminate either mode):

- **`--mode with-skill`** (default) injects the `SKILL.md` body via `--append-system-prompt`,
  with the skill's base directory pinned so read-on-demand references still resolve.
- **`--mode baseline`** runs the bare model. The baseline-vs-with-skill gap is what the skill
  must close (Anthropic: measure the baseline before writing/justifying content).

Results land in `evals/results/<UTC-stamp>-<mode>-<model>/` (git-ignored): one JSON per
scenario plus `summary.md`/`summary.json`. Curate a run worth keeping (e.g. the pre-edit
baseline before a large `SKILL.md` restructuring) into `evals/baselines/`. Exit code is `0`
only when every scenario passes, so the runner can gate.

### Cross-CLI runs (`--runner generic`)

The **scenario runner is pluggable; the judge is not.** `--runner generic` produces each
scenario's response through any other agent CLI (Codex, Gemini CLI, …) so the same suite can
measure the skill's content on a non-Claude harness:

```bash
scripts/run-evals.py --runner generic \
  --runner-cmd 'codex exec --model {model} {prompt}' \
  --runner-instructions-file AGENTS.md \
  --model <that-cli's-model-name>
```

- **`--runner-cmd`** is a shell-style template; `{prompt}`/`{model}` are substituted **after**
  tokenization, so a hostile prompt stays one argv token (no shell, no injection). The response
  is the command's raw stdout. **Verify the template against your installed CLI's `--help`
  first** — flags drift across versions, and this repo deliberately hardcodes no foreign-CLI
  flags it cannot test.
- **`--runner-instructions-file`** (required in with-skill mode) names the instruction file —
  `AGENTS.md` for Codex, `GEMINI.md` for Gemini CLI — that the `SKILL.md` body is written to in
  each scenario's scratch cwd, since foreign CLIs have no `--append-system-prompt`. This tests
  the skill's *content* on that harness; it does not exercise that platform's own skill-loading
  mechanics.
- **The judge always runs on the `claude` CLI** (so verdicts stay comparable across runners —
  one grading instrument); `claude` must still be on PATH. Judge-model bias toward its own
  family is an uncontrolled variable — note it when comparing cross-vendor numbers.
- Output dirs gain a `-generic` tag so a foreign-CLI sweep can't be mistaken for a claude one.
  A `pass`/`fail` from a generic sweep grades the *response text* only — a CLI that emits
  progress noise into stdout will read worse than it is; check a transcript before trusting a
  surprising number.

## Recorded baselines (`baselines/`)

A committed baseline is a *slim* copy of a full sweep — statuses, per-item judgments, and
judge reasons, with the response transcripts stripped — plus a `BASELINE.md` stating the
headline numbers, the per-scenario gap table, and the harness caveats. Record one **before
any large core edit** and validate the edit by re-running **both** modes under the same
harness afterward; a baseline only covers the scenarios that existed when it was taken
(added/edited scenarios re-baseline on the next sweep). Current:
[`baselines/2026-07-02-opus/`](baselines/2026-07-02-opus/BASELINE.md) — the skill improves
20 of 38 scenarios over the bare model with zero regressions (fails 13→4) — plus the
per-model portability sweeps of 2026-07-04:
[`baselines/2026-07-04-fable/`](baselines/2026-07-04-fable/BASELINE.md) — 22 of 45
improved, 0 regressed (fails 9→3, pass 8→28: the skill's value compounds up-model) —
[`baselines/2026-07-04-sonnet/`](baselines/2026-07-04-sonnet/BASELINE.md) — 14 of 45
improved, 0 regressed (fails 12→7; four of the seven remaining fails are the same durable
fails Opus records, i.e. content gaps, not model gaps) — and
[`baselines/2026-07-04-haiku/`](baselines/2026-07-04-haiku/BASELINE.md) — the skill improves
15 of 45 scenarios on Haiku 4.5 (fails 23→16), but 15 scenarios stay failed with the skill
loaded, where Opus left 4: the content transfers down-model, the enforcement reliability
does not. Across the four recorded sweeps, with-skill fails run 16 (Haiku) → 7 (Sonnet) →
4 (Opus, older suite) → 3 (Fable) with identical skill text — the shared durable-fail core
(dependency-manifest-drift · stale-diagram-on-behavior-change · tdd-regression-red-first)
is the standing sharpening target. Superseded:
[`baselines/2026-07-01-opus/`](baselines/2026-07-01-opus/BASELINE.md) (31 scenarios @ v1.8.0).

The loop around the runner is unchanged:

1. **Baseline first**, then **with the skill** — the gap is the skill's measured value.
2. **Iterate (Claude-A / Claude-B).** When a scenario fails or a real new miss appears: bring the specifics
   back to the skill (Claude-A), strengthen the relevant rule/reference, add or sharpen the scenario, re-run.
   This is the observe→refine→test loop from Anthropic's best-practices guide.
3. **Test across models** you actually use (`--model opus|sonnet|haiku`) — a rule that's obvious to Opus may
   need to be more prominent for a smaller model, and the per-model summaries make that visible.

## Maintenance

**Every new changelog entry written from a real miss should add (or extend) a scenario here, in the same
spirit as the same-commit docs rule.** A lesson without a guarding eval is a lesson that can silently
regress. Keep ≥3 scenarios per major discipline as coverage grows.
