# Evals for senior-engineering-partner

Last updated: 2026-07-04 05:00 PM CDT

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

**`files` — fixture workspaces.** A scenario whose query demands work on real code (an edit, a
red-first regression test, a doc sweep) lists workspace-relative paths in `files`; the runner
materializes each from `evals/fixtures/<scenario>/<path>.fixture` into the scratch cwd (suffix
stripped) before the run. Without a fixture, an act-on-the-workspace scenario doesn't test its
discipline at all — the model (correctly, per the skill's own never-fabricate floor) refuses to
invent code against an empty directory, and the judge grades the refusal. Two rules keep this
honest:

- **Scanner neutrality: every fixture file on disk carries the `.fixture` suffix** (enforced by
  the runner). Fixtures deliberately depict imperfect repos — stale drifted pins, an unpinned
  base image — and under their real names GitHub's dependency graph, Dependabot, and Scorecard
  would read them as *this repo's own* manifests and flood the alert wall the repo keeps at
  zero. For the same reason `evals/fixtures/**` is exempt from the repo's quality gates by
  design: fixtures are scenario *inputs*, sometimes deliberately imperfect, not shipped code.
- **Drift fails loudly, at two levels.** Per scenario: every listed file must exist under the
  fixture dir and every fixture file must be listed. Per suite (checked at startup, regardless
  of `--filter`): every fixture dir must belong to a scenario that declares a non-empty `files`
  list, and vice versa — otherwise a forgotten/mistyped `files` list would silently put that
  scenario back to grading inaction against an empty workspace.

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

Scenario runs in **both** modes are granted `Bash,Edit,Write` (the judge gets no tool grants) —
headless `claude -p` denies those tools by default, which silently converted every
act-on-the-workspace expectation into "described a plan, did nothing." **Know what that grant
means:** a scenario run executes model-chosen shell commands as *your user, with no sandbox* —
the throwaway temp cwd bounds the default working directory, not what Bash can reach. Scenario
`query`s are first-party fixtures, but run sweeps only on a machine and account you trust with
that. With-skill runs read a **staged copy** of the skill tree that excludes `evals/` (a run
must never be able to read its own grading criteria) and the private, uncommitted files.

The judge receives two pieces of **harness-collected evidence** alongside the response text:
the post-run **workspace evidence** (unified diffs vs the fixtures first, then new files —
per-file capped, 60 KB total) and the **ordered tool-call trail** (commands and edits in
execution order with truncated outputs) — order properties like "regression test seen to fail
red *before* the fix" need sequencing, which a final diff can't prove. A tool-granted model
does the work in the workspace and its prose under-credits it, so judging the response text
alone misgrades exactly the behaviors the fixtures exist to test. Both blocks are boundary-
neutralized and the judge is told they are data, never instructions.

Results land in `evals/results/<UTC-stamp>-<mode>-<model>/` (git-ignored): one JSON per
scenario plus `summary.md`/`summary.json`. Curate a run worth keeping (e.g. the pre-edit
baseline before a large `SKILL.md` restructuring) into `evals/baselines/`. Exit code is `0`
only when every scenario passes, so the runner can gate.

## Recorded baselines (`baselines/`)

A committed baseline is a *slim* copy of a full sweep — statuses, per-item judgments, and
judge reasons, with the response transcripts stripped — plus a `BASELINE.md` stating the
headline numbers, the per-scenario gap table, and the harness caveats. Record one **before
any large core edit** and validate the edit by re-running **both** modes under the same
harness afterward; a baseline only covers the scenarios that existed when it was taken
(added/edited scenarios re-baseline on the next sweep). Current:
[`baselines/2026-07-02-opus/`](baselines/2026-07-02-opus/BASELINE.md) — the skill improves
20 of 38 scenarios over the bare model with zero regressions (fails 13→4). Superseded:
[`baselines/2026-07-01-opus/`](baselines/2026-07-01-opus/BASELINE.md) (31 scenarios @ v1.8.0).

> **Harness discontinuity (2026-07-04).** Baselines recorded before the tool-grant +
> fixture-workspace + evidence-to-the-judge harness change measure a different thing (prose-only
> responses, no ability to act) and are **not comparable** to sweeps run after it. Re-record
> both modes under the new harness before reading any gap against them.

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
