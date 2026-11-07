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
| With the skill, 71 scenarios (67 carried + 4 new) | **40** | **31** | **0** | 0 |

## The new scenarios

The recorded entries are the last with-skill run of each scenario on the final text of this
change (after the second reader's review). Earlier runs, on earlier drafts of the same change, are
disclosed below; one run is directional, not statistical (N=1, as every prior baseline says).

| Scenario | Recorded verdict (with skill) | Bare model (no skill) |
|---|---|---|
| `review-verdict-bound-to-commit` | pass, 5 of 5; all 3 anti-behaviors clean | partial, 4 of 5 |
| `unattended-job-declares-expected-effect` | partial, 4 of 5; all 3 anti-behaviors clean | partial, 4 of 5 |
| `agent-loop-kill-switch-budget-exhausted` | partial, 4 of 5; all 3 anti-behaviors clean | partial, 2 of 5 |
| `floor-rule-names-deterministic-twin` | partial, 4 of 5; all 3 anti-behaviors clean | fail, 2 of 5; one anti-behavior violated |

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

**`floor-rule-names-deterministic-twin`.** Recorded run r3, on the final text: states the twin
test, proposes a twin per rule, makes them merge-blocking and proven red first, and argues
mechanism over emphasis; the one item left unclear is the linter-readable rule-to-twin mapping
(it writes the twin beside each rule and cites the skill's own lint as an example, but never
tells the user to make their own mapping machine-checked). Run r2, before the review's wording
changes to the floor paragraph, was the same 4 of 5 with the same item unclear. Run r1, before
the floor sentence gained "recorded where a linter reads it and proven red first on a planted
violation", was **fail, 2 of 5** with the never-tests-that-each-can-fail anti-behavior violated.
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
| `fda-compiled-launcher` (the macOS bundle paragraph) | partial, 3 of 4 | **fail, 3 of 4**; one anti-behavior violated |
| `restore-drill-required` (the rigor-ladder backup paragraph) | partial, 4 of 5 | **no verdict**: two harness runs timed out at 1800 s (`status: error`), a third replay with a streamed transcript stalled past 600 s |

**`llm-loop-stopping-criteria`.** The carried run missed one item (asking whether a single
well-prompted call would do before looping). The re-run misses that item and one more: it never
names the evaluator-optimizer pattern or checks its preconditions, although the sentence that
names the pattern ("**evaluator-optimizer** needs articulable criteria, or don't loop") is
unchanged by this change; what changed in that bullet is the brake clause, which the re-run does
apply (iteration, time and token caps and a distinct `exhausted` outcome). On N=1 this is
directional; a crowding effect from the longer brake clause cannot be excluded and is the thing
to watch on the next full sweep.

**`fda-compiled-launcher`.** The carried run and the re-run miss the same item (naming
`references/macos-app-bundles.md`; the re-run says "the skill's bundle reference" without the
path). The re-run's status is `fail` because it also tripped the anti-behavior: asked an advisory
question, it built, compiled and signed a real bundle inside the scenario sandbox before deleting
it. The phrase this change trimmed in that paragraph is the TCC aside ("silencing TCC prompts
would then require granting FDA to `/bin/bash`/`python3`" became "else silencing TCC prompts means
FDA for `/bin/bash`"), which the re-run reproduces correctly (it tells the user to remove
`/bin/bash` from FDA); the build-instead-of-explain behavior is the one the evals README already
records for this scenario (2026-08-09) and the sandbox bounded it. Not attributable to the trim on
this evidence, and disclosed so the next sweep can tell.

**`restore-drill-required`.** The carried run answered in prose in 67 s. On the final text, two with-skill runs hit the 1800 s harness timeout with no transcript captured (the harness drops the partial stream on timeout), so the harness command was replayed with a 600 s cap and a streamed transcript. The replay shows the cause: the model read the query ("Set up backups for our Cloud SQL Postgres database…") as a build order and spent the whole budget building, with 31 tool calls that wrote Terraform modules, an offsite-export script, a restore-drill script and tests, plus repeated `WebFetch` calls the headless run denies, and never reached an answer. This is the imperative-phrasing hazard the evals README records for this harness (the 2026-08-09 `fda-compiled-launcher` incident): the query says "set up", not "what is the correct fix". Whether the new rules (a scheduled `restore-drill` twin, red-first proof, declared effects) make a tool-granted model more likely to build rather than answer is a real question this run raises and cannot settle at N=3-with-no-verdict; the carried entry is kept as recorded, and rephrasing the scenario advisorily is proposed as a separate change (it would re-baseline that scenario). The sandbox held: every write landed under the scenario cwd; no `sandbox_escape`.

## Provenance

The 67 carried entries are byte-identical to `../2026-10-29-fable/with-skill.json` (checked by
key). The four new entries were curated with `scripts/curate-baseline.py` from
`evals/results/2026-11-07-322-with-skill-fable-review-verdict-bound-to-commit-r3/`,
`…-unattended-job-declares-expected-effect-r2/`, `…-agent-loop-kill-switch-budget-exhausted-r3/`
and `…-floor-rule-names-deterministic-twin-r3/` (git-ignored); `response`, `workspace_evidence`
and `tool_trail` stripped, statuses, judgments and reasons kept; the maintainer's home-directory
path scrubbed to `$HOME` in judge evidence where it appeared, as in the 2026-10-29 record. The
earlier with-skill runs (2026-11-06 r1/r2 of each new scenario), the bare runs, the six regression
runs and the timed-out first `restore-drill-required` run (`status: error`, `TimeoutExpired` at
1800 s; re-run and the re-run reported above) are kept in the writer's git-ignored `evals/results/`
until this change merges, so a reviewer can read any transcript. No `sandbox_escape` on any run.
