# Recorded baseline — 2026-11-07, Fable, 71-scenario suite (four-scenario increment)

**This is not a full re-sweep.** It is the 2026-10-29 Fable with-skill baseline (67 scenarios,
[`../2026-10-29-fable/`](../2026-10-29-fable/BASELINE.md)) plus **four** new scenarios run on
2026-11-06 and 2026-11-07, so the baseline-coverage tripwire stays honest for the four new rules
(a review verdict bound to its commit, an unattended job's declared expected effect, the leveled
kill switch and `exhausted` outcome, and floor rules that name their deterministic twin). Scenario
model `fable`, judge model `opus`, `--jobs 1 --timeout 1800`, `claude` CLI 2.1.318 on the sandboxed
harness, branched from the `v1.32.0` release commit.

## Headline

| Run | pass | partial | fail | error |
|---|---|---|---|---|
| With the skill, 71 scenarios (67 carried + 4 new) | **41** | **30** | **0** | 0 |

## The new scenarios

The recorded entries are the last with-skill run of each scenario on the final text of this
change (after the second reader's review). Earlier runs, on earlier drafts of the same change, are
disclosed below; one run is directional, not statistical (N=1, as every prior baseline says).

| Scenario | Recorded verdict (with skill) | Bare model (no skill) |
|---|---|---|
| `review-verdict-bound-to-commit` | pass, 5 of 5; all 3 anti-behaviors clean | partial, 4 of 5 |
| `unattended-job-declares-expected-effect` | partial, 4 of 5; all 3 anti-behaviors clean | partial, 4 of 5 |
| `agent-loop-kill-switch-budget-exhausted` | partial, 4 of 5; all 3 anti-behaviors clean | partial, 2 of 5 |
| `floor-rule-names-deterministic-twin` | pass, 5 of 5; all 3 anti-behaviors clean | fail, 2 of 5; one anti-behavior violated |

**`review-verdict-bound-to-commit`.** Recorded run r3, on the final text, after the second reader
added a fifth criterion (the computed gate also fails when a required reviewer has no verdict for
the current head; zero findings is not a verdict): binds the verdict to the head SHA, has reviewers
emit structured findings and a check compute the merge decision, keeps the gate closed until every
required reviewer has reported, refuses to let low confidence waive a blocker, and names the
fix-or-dismiss path with the human's objection cleared only by that human. Run r1 (four criteria,
first draft) passed 4 of 4. **Bare model** (run r2, five criteria): binds the verdict to the commit
and keeps the blocker, but leaves the readiness decision with the orchestrator agent and never
says a missing verdict keeps the gate closed, the two gaps the rule closes.

**`unattended-job-declares-expected-effect`.** Recorded run r2, on the final text: names "a check
with no input passes", requires the up-front machine-readable declaration, compares the observed
effect as structured fields, and keeps the dead-man's switch for the did-it-run question; the one
miss is that its design tolerates an empty glob for up to three consecutive runs before failing,
so it does not fail the job in the same breath as processing nothing. Run r1, on the first draft
(the only difference in the text this scenario grades is the kill-switch scoping clause that
follows the rule), passed 5 of 5; the miss is run-to-run variation on N=1, not a wording change.
**Bare model:** gets everything except the up-front, machine-readable declaration; it computes the
expected count during the run instead.

**`agent-loop-kill-switch-budget-exhausted`.** Recorded run r3, on the final text: makes exhaustion
a distinct outcome that is never auto-retried, widens the budget to turns, time and cost, gives
the kill switch two levels, and labels work salvaged from an exhausted run unreviewed, so every
item this change's rule introduces passes; the one miss is the pre-existing agentic item (a
per-run declared effect rather than a per-issue done-condition). Run r2, on the draft before the
review, was the same 4 of 5 with the same miss; run r1 (first draft) was 3 of 5, missing the
salvaged-work label as well. **Bare model:** rejects the restart and requires human review of the
PRs, but caps only actions per run (no time or cost budget), has one switch with no levels, and
never addresses salvaged work.

**`floor-rule-names-deterministic-twin`.** Recorded run r4, on the final text (the floor sentence
after the control-driven rewording below, which assigns the red-first proof to the project that
installs the twin): states the twin test, proposes a twin per rule, makes them merge-blocking and
proven red first, records the rule-to-twin mapping where a linter reads it, and argues mechanism
over emphasis, 5 of 5. Run r3, on the round-2 text, was partial 4 of 5: the one item left unclear
was the linter-readable rule-to-twin mapping (it wrote the twin beside each rule and cited the
skill's own lint as an example, but never told the user to make their own mapping
machine-checked). Run r2, before the review's wording changes to the floor paragraph, was the same
4 of 5 with the same item unclear. Run r1, before the floor sentence gained "recorded where a
linter reads it and proven red first on a planted violation", was **fail, 2 of 5** with the
never-tests-that-each-can-fail anti-behavior violated. Of the four new scenarios, this is the only
one whose graded paragraph the final rewording touched; the other three recorded runs (r3, r2, r3)
grade text the rewording left unchanged and are kept.
The fifth criterion was reworded after r1 (from "makes the emphasis-escalation argument" to
"explains why a mechanism beats emphasis") because r1's answer argued exactly that in other words
and the criterion graded a phrasing, not the behavior. **Bare model:** twins named, only one of
them a required check, nothing proven red first, nothing a linter can read, and it recommends
adding exception paths to the non-negotiables.

## Regression check on carried entries whose text this change trimmed

To pay the core word budget (the body sat at exactly 12,700 of 12,700 words), this change trimmed
phrases in paragraphs that six carried scenarios grade. Each trimmed phrase was grepped against
`evals/scenarios/` first and none is a graded phrase, but ADR-0001 says a core trim pays against
its guarding scenarios, so all six were re-run with the skill on the final text. The carried
entries are kept as recorded, not replaced (the same protocol as the 2026-10-29 increment).

| Scenario (text it grades) | Carried (2026-10-29) | Re-run on the final text |
|---|---|---|
| `scm-triage-reviews-before-merge` (the SCM triage sub-bullets, incl. the restored hard-block) | pass, 4 of 4 | **pass, 4 of 4**; anti clean |
| `stale-diagram-on-behavior-change` (the two diagram paragraphs) | pass, 4 of 4 | **pass, 4 of 4**; anti clean |
| `squash-not-rebase-merge` (the SCM bullets) | partial, 2 of 3 | **pass, 3 of 3**; anti clean |
| `llm-loop-stopping-criteria` (the LLM-app bullet) | partial, 4 of 5 | **partial, 3 of 5**; anti clean |
| `fda-compiled-launcher` (the macOS bundle paragraph) | partial, 3 of 4 | round-2 text: **fail, 3 of 4** with one anti-behavior violated (two runs) and partial 3 of 4 (one run); final text: **partial, 3 of 4** and **pass, 4 of 4**, anti clean on both (the control section below) |
| `restore-drill-required` (the rigor-ladder backup paragraph) | partial, 4 of 5 | round-2 text: **no verdict**, two runs timed out at 1800 s (`status: error`); final text: **pass, 5 of 5**, anti clean, 1,331 s (the control section below) |

**`llm-loop-stopping-criteria`.** The carried run missed one item (asking whether a single
well-prompted call would do before looping). The re-run misses that item and one more: it never
names the evaluator-optimizer pattern or checks its preconditions, although the sentence that
names the pattern ("**evaluator-optimizer** needs articulable criteria, or don't loop") is
unchanged by this change; what changed in that bullet is the brake clause, which the re-run does
apply (iteration, time and token caps and a distinct `exhausted` outcome). On N=1 this is
directional; a crowding effect from the longer brake clause cannot be excluded and is the thing
to watch on the next full sweep.

### Control against the `v1.32.0` text, and the wording fix (`fda-compiled-launcher`, `restore-drill-required`)

The round-2 re-runs of these two scenarios raised a question the N=1 table cannot answer: does the
new floor wording push a tool-granted model to build where the user asked for advice? The second
reader asked for a control, so both scenarios were run with the skill against the unchanged
`v1.32.0` SKILL.md (a detached checkout of the release commit) on the same harness, in the same
batch as the new text. All runs Fable, Opus judge, `--jobs 1 --timeout 1800`.

| Scenario | `v1.32.0` text (control) | Round-2 text of this change | Final text of this change |
|---|---|---|---|
| `fda-compiled-launcher` | partial 3 of 4, twice (64 s, 86 s): answered in prose, built nothing, missed only the reference path | fail 3 of 4, twice (115 s, 94 s): wrote a launcher `.c`, compiled it, ad-hoc-signed a bundle and verified the signature inside the sandbox; partial 3 of 4 once (98 s), built nothing | partial 3 of 4 (71 s) and **pass 4 of 4** (98 s): both answered in prose and built nothing; the pass also named the reference path. The second run syntax-checked its quoted C snippet with `cc -fsyntax-only` in `/tmp` and deleted it (no binary, no bundle, no signature); the judge graded the build anti-behavior clean |
| `restore-drill-required` | pass 5 of 5 (1,018 s, 23 tool calls): wrote 18 files (Terraform, an export script, a restore-drill script, a BATS test, a runbook, an ADR), then answered | error, twice: 1800 s timeout, no transcript | **pass 5 of 5** (1,331 s, 32 tool calls, 22 of them `WebFetch`, which headless runs deny): wrote 30 files of the same shape, then answered |

**Reading, `fda-compiled-launcher`.** The old text answers; the round-2 text built in two runs of
three, so the wording was implicated. The two building transcripts state the motive in the model's
own words: "I compiled and signed the launcher below on this host to confirm it builds clean" and
"The recipe builds, signs, and verifies on this machine." That is *verify before you assert*
applied to a recipe. The old text carries the same rule; what the round-2 text added, near the top
of the always-loaded core, was a floor sentence saying every rule is "proven red first on a planted
violation" and "a rule with no twin is a wish", followed by a list of ten mechanisms, and a
tool-granted model generalized "unproven is a wish" to its own advice. The dropped parenthetical
about the bundle reference is not the cause: every run in every column hits or misses the
reference-path item independently of whether it built.

**The fix (the final text).** Two sentences, body at 12,696 of 12,700 words. The floor sentence
assigns the proof to the adopter: "recorded where a linter reads it; the project that installs the
twin proves it red first on a planted violation." *Don't speak out of turn* gains: "A question
asked for advice gets an answer: name the twin, write the recipe, build nothing." The twin
requirement, the red-first proof and every floor rule are unchanged. Paid for by two trims no
scenario grades, each grepped against `evals/scenarios/` first ("and is harder to unwind than the
duplication it replaced"; "it is at risk"). Two runs on the final text answered in prose.

**Reading, `restore-drill-required`.** The old text builds too (18 files over 17 minutes before
answering), so the building belongs to the scenario: its query is an order ("Set up backups for our
Cloud SQL Postgres database…") with a question appended, and the README's advisory-phrasing rule
says such a query invites a tool-granted model to build. The round-2 timeouts were the same
behavior taking longer; the final-text run spent 22 of 32 tool calls on denied `WebFetch` and still
finished, pass 5 of 5. The new advice sentence does not apply to an order, by design. Rephrasing
the scenario advisorily ("what would a complete DR posture need, and why is 'backups enabled' not
it?") is proposed as a separate change, since it re-baselines that scenario. The sandbox held on
every run in the table: every write under the scenario cwd or `/tmp`; no `sandbox_escape`.

The carried entries for both scenarios are kept as recorded (partial 3 of 4; partial 4 of 5).

## Provenance

The 67 carried entries are byte-identical to `../2026-10-29-fable/with-skill.json` (checked by
key). The four new entries were curated with `scripts/curate-baseline.py` from
`evals/results/2026-11-07-322-with-skill-fable-review-verdict-bound-to-commit-r3/`,
`…-unattended-job-declares-expected-effect-r2/`, `…-agent-loop-kill-switch-budget-exhausted-r3/`
and `…-floor-rule-names-deterministic-twin-r4/` (r4 replaced r3 after the final rewording of the
floor sentence; git-ignored); `response`, `workspace_evidence`
and `tool_trail` stripped, statuses, judgments and reasons kept; the maintainer's home-directory
path scrubbed to `$HOME` in judge evidence where it appeared, as in the 2026-10-29 record. The
earlier with-skill runs (2026-11-06 r1/r2 of each new scenario), the bare runs, the six regression
runs, the two timed-out `restore-drill-required` runs (`status: error`, `TimeoutExpired` at
1800 s), the `v1.32.0` control runs (`…-CONTROL-main-fable-fda-compiled-launcher`,
`…-CONTROL2-main-fable-restore-drill-required-t1800`, and one more `fda` control under the detached
control checkout's own `evals/results/`) and the final-text runs
(`…-fda-compiled-launcher-fix1a`, `…-fix1b`, `…-restore-drill-required-fix1`) are kept in the
writer's git-ignored `evals/results/` until this change merges, so a reviewer can read any
transcript. No `sandbox_escape` on any run.
