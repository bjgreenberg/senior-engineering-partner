# Evals for senior-engineering-partner

Last updated: 2026-08-13 11:24 PM CDT

A regression suite for the skill itself. Each scenario encodes a **real miss** the skill exists to
prevent — most are drawn straight from the SKILL.md changelog — so the suite is the executable form of
"this must never happen again." Anthropic's own most-emphasized authoring practice is *build evaluations
first*; this brings the skill into line with it (the changelog was the spec; these are the tests).

**The suite is gate-enforced, not aspirational:** the `eval-guard` CI check
(`scripts/eval-guard.py`) fails any PR that makes a substantive SKILL.md change without touching
`evals/scenarios/` — a rule change must ship its guarding eval, or the PR body must carry an
explicit `Eval-waiver: <reason>` line (metadata-only diffs, e.g. release-please version bumps,
pass automatically). Fixture-tested in `scripts/tests/test-scripts.sh` like every other gate.

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

> **Phrase system-touching scenarios advisorily, not imperatively.** A scenario about
> launchd, app bundles, installs, or any real machine mutation must ask *"what's the correct
> fix / why is this wrong?"* — never *"fix it."* The checklist grades the model's *prose*, so
> advisory phrasing costs zero grading signal; imperative phrasing invites the model to
> actually perform the mutation, which the 2026-08-09 `fda-compiled-launcher` run did (it built
> a real LaunchAgent + app bundle on the maintainer's Mac). The sandbox now bounds the blast
> radius, but the phrasing is the first line: don't ask a shell-granted model to do a thing you
> only want it to *explain*. Pair such scenarios with an `anti_behavior` that fails a candidate
> which builds/installs instead of explaining.

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
- **Drift fails loudly, at two levels.** Per scenario run: every listed file must exist under
  the fixture dir and every fixture file must be listed. Per suite (checked at startup on
  every invocation, regardless of `--filter`): every fixture dir must belong to a scenario
  that declares a non-empty `files` list and vice versa — otherwise a forgotten/mistyped
  `files` list would silently put that scenario back to grading inaction against an empty
  workspace — **and** the suffix + listed↔on-disk rules are enforced file-by-file across
  every fixture dir, because an unsuffixed manifest is a scanner-visible harm on disk whether
  or not its owning scenario ever runs.

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

Claude-runner scenario runs in **both** modes are granted `Bash,Edit,Write` (the judge gets no
tool grants) — headless `claude -p` denies those tools by default, which silently converted
every act-on-the-workspace expectation into "described a plan, did nothing." **The write
boundary:** every scenario child (and generic-runner child) runs under a macOS `sandbox-exec`
seatbelt profile that **denies all file writes outside the scenario workspace** (+ system
temp) — the temp cwd bounds only the *default* directory, so a Bash call using `~` or an
absolute path would otherwise write to the real home, and once did (a "fix this LaunchAgent"
scenario built a real `~/Library/LaunchAgents` agent + `~/Applications` bundle on the
maintainer's Mac, 2026-08-09). The seatbelt is the enforcement layer; a workspace
`.claude/settings.json` additionally denies system-mutating exec (`launchctl`, `osascript`,
`sudo`, …) that a file-write boundary can't express, and a pre/post persistence-surface
snapshot is the detection backstop. **Reads stay open** so the CLI reads its own auth from
`~/.claude`; the residual — a Bash call *reading* the session token — cannot be closed at the
sandbox layer (the reader is the CLI itself), so scenario `query`s remain first-party fixtures
and sweeps still run only on an account you trust. On a platform without `sandbox-exec` the
harness **fails closed** (refuses shell-granted scenarios) unless `EVAL_ALLOW_UNSANDBOXED=1`
is set — an explicit override for a throwaway VM/account only. With-skill runs read a
**staged copy** of the skill tree that excludes `evals/` (a run must never be able to read its
own grading criteria) and the private, uncommitted files.

Claude-runner scenario **and judge** runs are isolated from the invoking user's global agent
context (`--setting-sources project`): user-level memory, hooks, and settings never load, so
a sweep's "bare" responses can't absorb the operator's environment — the root cause of an
identifier once leaking into a committed baseline. (Generic runners: the `--runner-cmd`
template author owns the foreign CLI's equivalent isolation.)

**Resuming an interrupted sweep.** Results checkpoint per scenario as they finish, so an
interrupted run loses nothing already done. A full Fable sweep spans a usage-limit window
(scenarios past it error `claude exited 1` in ~3 s) and can be externally killed. Re-invoke
with the **same `--out` dir** plus **`--resume`**: scenarios with a non-error result are
reused, only errored/missing ones re-run — recovering the sweep without re-spending on
completed scenarios. (Errored and malformed checkpoints are always re-run, never trusted.)

The judge receives two pieces of **harness-collected evidence** alongside the response text:
the post-run **workspace evidence** (unified diffs vs the fixtures first, then new files —
per-file capped, 60 KB total) and, on the claude runner, the **ordered tool-call trail**
(commands and edits in execution order with truncated outputs) — order properties like
"regression test seen to fail red *before* the fix" need sequencing, which a final diff can't
prove. A tool-granted model does the work in the workspace and its prose under-credits it, so
judging the response text alone misgrades exactly the behaviors the fixtures exist to test.
Both blocks are boundary-neutralized and the judge is told they are data, never instructions.

Results land in `evals/results/<UTC-stamp>-<mode>-<model>/` (git-ignored): one JSON per
scenario plus `summary.md`/`summary.json`. Curate a run worth keeping (e.g. the pre-edit
baseline before a large `SKILL.md` restructuring) into `evals/baselines/`. Exit code is `0`
only when every scenario passes, so the runner can gate.

### Recording a baseline (cadence + procedure)

**Cadence: a baseline is DUE the moment any scenario exists that the newest committed
baseline never measured** — enforced by the baseline-coverage tripwire in
`scripts/tests/test-scripts.sh` (the `script-tests` CI gate fails with a "re-baseline due"
message naming the missing scenarios). In practice that means: batch new scenarios freely
within a PR, but a release that ships new scenarios ships their baseline too. A **model
change** (new CLI default, new model family) also warrants a re-baseline even though the
tripwire can't see it — the 2026-07-05 discontinuity note shows why cross-harness numbers
must never be compared silently.

**Procedure** (the documented recipe — keep it stable so runs stay comparable; the
per-scenario timeout is **1800s**: two scenarios reproducibly need 20+ minutes under tool
grants, and the 2026-07-27 sweeps showed a 900s budget manufactures error-splices rather
than tolerating flakes):

```bash
# bare first, then with-skill, sequentially; judge stays opus
scripts/run-evals.py --mode baseline   --model <m> --judge-model opus --jobs 2 --timeout 1800
scripts/run-evals.py --mode with-skill --model <m> --judge-model opus --jobs 2 --timeout 1800

# slim each results dir into the committable shape (strips response/evidence/trail;
# refuses status=error entries — re-run the scenario and splice, disclosing it):
scripts/curate-baseline.py <results-dir> evals/baselines/<date>-<model>/baseline.json \
  [--splice <scenario>=<rerun-results-dir>]
```

Each baseline dir carries `baseline.json`, `with-skill.json`, and a `BASELINE.md` recording
provenance (harness commit, CLI version, exact flags, splices disclosed) and the headline
table — see any existing baseline for the shape.

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
  each scenario's scratch cwd, since foreign CLIs have no `--append-system-prompt`. A **bare
  filename only** — paths/traversal are rejected at argparse so the write can't escape the
  scratch dir. This tests
  the skill's *content* on that harness; it does not exercise that platform's own skill-loading
  mechanics.
- **The judge always runs on the `claude` CLI** (so verdicts stay comparable across runners —
  one grading instrument); `claude` must still be on PATH. Judge-model bias toward its own
  family is an uncontrolled variable — note it when comparing cross-vendor numbers.
- Output dirs gain a `-generic` tag so a foreign-CLI sweep can't be mistaken for a claude one.
  A `pass`/`fail` from a generic sweep grades the *response text plus workspace evidence* —
  a CLI that emits progress noise into stdout will read worse than it is; check a transcript
  before trusting a surprising number.
- Generic runs get fixture materialization and workspace evidence (both runner-agnostic) but
  **no tool-call trail** (there is no cross-CLI transcript envelope to parse — order
  properties like red-first grade from the response and final diffs only, a disclosed
  degradation) and **no tool grants from this runner** — the foreign CLI's own permission
  model governs what it may execute; configure that in the `--runner-cmd` template. The
  harness-written instructions file is excluded from workspace evidence in with-skill mode
  (it is not the assistant's work), and no scenario may list that filename as a fixture —
  the startup check rejects the collision.

## Recorded baselines (`baselines/`)

A committed baseline is a *slim* copy of a full sweep — statuses, per-item judgments, and
judge reasons, with the response transcripts stripped — plus a `BASELINE.md` stating the
headline numbers, the per-scenario gap table, and the harness caveats. Record one **before
any large core edit** and validate the edit by re-running **both** modes under the same
harness afterward; a baseline only covers the scenarios that existed when it was taken
(added/edited scenarios re-baseline on the next sweep). **Current (sandboxed harness v3,
recorded 2026-08-10, amended 2026-08-14):**
[`baselines/2026-08-10-fable/`](baselines/2026-08-10-fable/BASELINE.md) — with-skill
**36/25/0/0 on 61 scenarios**, zero fails and zero sandbox escape; the first baseline on
the sandboxed harness and the record that closed the four v1.25.0 `Eval-waiver`s (bare
reference remains the 2026-07-28 run — same model, no bare re-sweep). The 2026-08-14
amendment appended `launchd-descriptive-executable-name` (pass) per the coverage
tripwire; details and the multi-cycle-assembly caveat in its `BASELINE.md`.
**Prior (harness v2, 56-scenario suite, recorded 2026-07-27/28):**
[`baselines/2026-07-27-opus/`](baselines/2026-07-27-opus/BASELINE.md) — bare 15/28/13/0 vs
with-skill **42/13/1/0**;
[`baselines/2026-07-28-fable/`](baselines/2026-07-28-fable/BASELINE.md) — bare 9/30/17/0 vs
with-skill **42/14/0/0**, the first zero-fail with-skill sweep on the full suite;
[`baselines/2026-07-27-haiku/`](baselines/2026-07-27-haiku/BASELINE.md) — bare 1/21/34/0 vs
with-skill 13/28/15/0 (content transfers down-model; enforcement reliability does not).
[`baselines/2026-07-27-postdiet-experiment/`](baselines/2026-07-27-postdiet-experiment/EXPERIMENT.md)
is the core-density control record — future core-compression edits compare against it, not
against post-t4. **The current sharpening picture (read from these records, not the older
narrative):** no scenario fails on all three models any more. Opus's single with-skill fail
is `adversarial-review-green-but-insufficient`; Fable's fail column is zero; Haiku's 15
fails are an enforcement-reliability gap, not content gaps — the old durable-fail trio
(dependency-manifest-drift · stale-diagram-on-behavior-change · tdd-regression-red-first)
now passes on Opus, and of that trio only `dependency-manifest-drift` still runs partial
on Fable/Haiku (`stale-diagram-on-behavior-change` also fails on Haiku, inside Haiku's
broader enforcement gap). Sharpening effort goes to the adversarial-review scenario and
Haiku enforcement, not the solved trio. Prior harness-v2 record (45-scenario era, superseded as
"current"): [`baselines/2026-07-05-opus/`](baselines/2026-07-05-opus/BASELINE.md) —
bare 11/22/12/0 vs with-skill 29/16/0/0. Historical
(pre-discontinuity, not comparable — see the note below):
[`baselines/2026-07-02-opus/`](baselines/2026-07-02-opus/BASELINE.md) — the skill improves
20 of 38 scenarios over the bare model with zero regressions (fails 13→4) — plus the
per-model portability sweeps of 2026-07-04:
[`baselines/2026-07-04-fable/`](baselines/2026-07-04-fable/BASELINE.md) — 22 of 45
improved, 0 regressed (fails 9→3, pass 8→28: the skill's value compounds up-model) —
[`baselines/2026-07-04-sonnet/`](baselines/2026-07-04-sonnet/BASELINE.md) — 14 of 45
improved, 0 regressed (fails 12→7; four of the seven remaining fails were the same durable
fails Opus recorded then, i.e. content gaps, not model gaps) — and
[`baselines/2026-07-04-haiku/`](baselines/2026-07-04-haiku/BASELINE.md) — the skill improves
15 of 45 scenarios on Haiku 4.5 (fails 23→16), but 15 scenarios stay failed with the skill
loaded, where Opus left 4: the content transfers down-model, the enforcement reliability
does not. (The durable-fail trio those sweeps identified was closed by later releases —
see the current sharpening picture above.) The tranche-4 core compression (~18% of
SKILL.md, rules-lossless) was validated against those pre-edit references the same day —
[`baselines/2026-07-04-post-t4/`](baselines/2026-07-04-post-t4/BASELINE.md): no drop on any
model traces to lost text; post-t4 served as the core-edit comparison record until the
2026-07-27 postdiet-experiment control superseded it. Superseded:
[`baselines/2026-07-01-opus/`](baselines/2026-07-01-opus/BASELINE.md) (31 scenarios @ v1.8.0).

> **Harness discontinuity (2026-07-04, the fixture/tool-grant change).** Every baseline above —
> including the four 2026-07-04 per-model sweeps — was recorded under the prose-only harness
> (no tool grants, no fixture workspaces, judge sees response text only). Sweeps run after the
> fixture + tool-grant + evidence-to-the-judge change measure a different thing and are **not
> comparable** to them. Re-record both modes under the new harness before reading any gap
> against a recorded baseline.

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
