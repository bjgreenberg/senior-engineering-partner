# Recorded baseline — 2026-11-06, Fable, 71-scenario suite (four-scenario increment)

**This is not a full re-sweep.** It is the 2026-10-29 Fable with-skill baseline (67 scenarios,
[`../2026-10-29-fable/`](../2026-10-29-fable/BASELINE.md)) plus **four** new scenarios run on
2026-11-06, so the baseline-coverage tripwire stays honest for the four new rules (a review
verdict bound to its commit, an unattended job's declared expected effect, the leveled kill switch
and `exhausted` outcome, and floor rules that name their deterministic twin). Scenario model
`fable`, judge model `opus`, `--jobs 1 --timeout 1800`, `claude` CLI 2.1.318 on the sandboxed
harness, branched from the `v1.32.0` release commit.

## Headline

| Run | pass | partial | fail | error |
|---|---|---|---|---|
| With the skill, 71 scenarios (67 carried + 4 new) | **41** | **30** | **0** | 0 |

## The new scenarios

The recorded entries are the last with-skill run of each scenario on the final text of this
change. Earlier runs, on earlier drafts of the same change, are disclosed below; one run is
directional, not statistical (N=1, as every prior baseline says).

| Scenario | Recorded verdict (with skill) | Bare model (no skill) |
|---|---|---|
| `review-verdict-bound-to-commit` | pass, 4 of 4; all 3 anti-behaviors clean | partial, 3 of 4 |
| `unattended-job-declares-expected-effect` | pass, 5 of 5; all 3 anti-behaviors clean | partial, 4 of 5 |
| `agent-loop-kill-switch-budget-exhausted` | partial, 4 of 5; all 3 anti-behaviors clean | partial, 2 of 5 |
| `floor-rule-names-deterministic-twin` | partial, 4 of 5; all 3 anti-behaviors clean | fail, 2 of 5; one anti-behavior violated |

**`review-verdict-bound-to-commit`.** Recorded run r1 (the only with-skill run): binds the verdict
to the head SHA, has reviewers emit structured findings and a check compute the merge decision,
refuses to let low confidence waive a blocker, and names the fix-or-dismiss-with-reason path.
**Bare model:** binds the verdict to the commit and keeps the blocker, but leaves the readiness
decision with the orchestrator agent ("a structured verdict, not yes or no") and never has a script
or check compute it from findings, the gap the rule closes.

**`unattended-job-declares-expected-effect`.** Recorded run r1 (the only with-skill run): names
"a check with no input passes", requires the declaration in the job's config or header, compares
the observed effect to it as structured fields, keeps the dead-man's switch for the did-it-run
question, and fails the job when the glob matches nothing. **Bare model:** gets everything except
the up-front, machine-readable declaration; it computes the expected count during the run instead,
so the declaration cannot be read before the job acts.

**`agent-loop-kill-switch-budget-exhausted`.** Recorded run r2, on the final text: makes exhaustion a distinct outcome that is never auto-retried, widens the budget to turns, time and cost, gives the kill switch two levels, and labels work salvaged from an exhausted run unreviewed, so every item this change's rule introduces passes; the one miss is the pre-existing agentic item (it leaves closing duplicates unattended and gives a per-run declared effect rather than a per-issue done-condition). Run r1, on the same text for
every sentence this scenario grades (the two drafts differed only in the floor sentence and two
trims elsewhere in the core), was **partial, 3 of 5**: it made exhaustion a distinct outcome,
widened the budget to time and cost, and gave the kill switch levels, but never said that work
salvaged from an exhausted run is labeled unreviewed (it stated the general draft-PRs-only rule
instead), and gave no explicit per-issue done-condition. **Bare model:** rejects the restart and
requires human review of the PRs, but caps only actions per run (no time or cost budget), has one
switch with no levels, and never addresses salvaged work.

**`floor-rule-names-deterministic-twin`.** Recorded run r2, after the floor sentence in SKILL.md
gained "recorded where a linter reads it and proven red first on a planted violation": states the
twin test, proposes a twin per rule, makes them merge-blocking and proven red first, and argues
mechanism over emphasis; the one item left unclear is the linter-readable rule-to-twin mapping.
Run r1, before that clause, was **fail, 2 of 5** with the never-tests-that-each-can-fail
anti-behavior violated: it proposed the twins and made them required checks but never said to
prove each on a planted violation, and recorded nothing a linter could read. The recorded run also
follows a wording change to the fifth criterion (from "makes the emphasis-escalation argument" to
"explains why a mechanism beats emphasis"), made because r1's answer argued exactly that in other
words and the criterion was grading a phrasing, not the behavior. **Bare model:** same shape as r1
with the skill: twins named, only one of them a required check, nothing proven red first, nothing a
linter can read, and it recommends adding exception paths to the non-negotiables.

## Provenance

The 67 carried entries are byte-identical to `../2026-10-29-fable/with-skill.json` (checked by
key). The four new entries were curated with `scripts/curate-baseline.py` from
`evals/results/2026-11-06-322-with-skill-fable-review-verdict-bound-to-commit/`,
`…-unattended-job-declares-expected-effect/`, `…-agent-loop-kill-switch-budget-exhausted-r2/` and
`…-floor-rule-names-deterministic-twin-r2/` (git-ignored); `response`, `workspace_evidence` and
`tool_trail` stripped, statuses, judgments and reasons kept; the maintainer's home-directory path
scrubbed to `$HOME` in judge evidence where it appeared, as in the 2026-10-29 record. The two
superseded with-skill runs (r1 of the agent-loop and floor-rule scenarios) and the four bare runs
(`…-baseline-fable-<scenario>/`) existed only in the writer's git-ignored `evals/results/` and
were removed with its clone after the PR opened; their verdicts and per-item counts are as stated
above and in the PR body. No `sandbox_escape` on any run.
