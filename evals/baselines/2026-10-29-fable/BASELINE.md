# Recorded baseline — 2026-10-29, Fable, 67-scenario suite (two-scenario increment)

**This is not a full re-sweep.** It is the 2026-09-14 Fable with-skill baseline (65 scenarios,
[`../2026-09-14-fable/`](../2026-09-14-fable/BASELINE.md)) plus **two** new scenarios run on
2026-10-29, so the baseline-coverage tripwire stays honest for the two new rules. Scenario model
`fable`, judge model `opus`, `--jobs 1 --timeout 1800`, `claude` CLI 2.1.312 on the sandboxed
harness, branched from the `v1.30.0` release commit.

## Headline

| Run | pass | partial | fail | error |
|---|---|---|---|---|
| With the skill, 67 scenarios (65 carried + 2 new) | **39** | **28** | **0** | 0 |

## The new scenarios

The recorded entries are the last with-skill run of each scenario on the final text of this
change (run r4 for the whole-tree scenario, run r5 for the re-scan scenario, whose text and
criteria changed once more after the security review). Earlier runs, on earlier drafts of the
same change, are disclosed below; one run is directional, not statistical (N=1, as every prior
baseline says).

| Scenario | Recorded verdict (with skill) | Bare model (no skill) |
|---|---|---|
| `whole-tree-gates-not-file-list` | partial, 3 of 4 expected; all 4 anti-behaviors clean | partial, 2 of 4 |
| `dependency-rescan-daily-with-sla` | partial, 5 of 6; all 5 anti-behaviors clean | partial, 1 of 6 |

**`whole-tree-gates-not-file-list`.** Recorded run r4: names the one-file gate as the defect,
whole-tree scope set in config, strict with per-module overrides, file-count check against
`git ls-files` — and never brings the test runner's discovery under the root-scoped rule, the
one item it misses. Run r3, on byte-identical type-check text (the drafts differed only in the
dependency-audit bullet and word-budget offsets elsewhere), passed 4 of 4; the pytest item is
the run-to-run variable. Runs r1 (2 of 5) and r2 (5 of 5) were on an earlier five-item version
of the scenario, before the second reader's review merged two overlapping items and corrected
the mypy claim (a named file also checks what it imports). **Bare model:** diagnoses the
one-file gate and widens strict to tests and scripts, but passes a hand-kept directory list
instead of the root with exclusions in config, omits pytest discovery, and never checks the
file count — the gap the rule closes.

**`dependency-rescan-daily-with-sla`.** Recorded run r5, after the security review added the
cooldown and provenance conditions to the merge path and a fifth anti-behavior: pushes back on
"nothing changed, nothing new", covers repos and hosts, sets the SLAs with the bounded
auto-merge path, states the blind spots — and never names OSV.dev/osv-scanner as a package feed
(GHSA, KEV, EPSS and NVD are named), the one item it misses; all five anti-behaviors clean.
Run r4, on the previous text (six items, four anti-behaviors), passed 6 of 6. Run r3, before the SKILL.md bullet named
OSV/GHSA, the vendor channel and NVD (that text lived only in the reference), was partial at
3 of 6 — it never named the GitHub Advisory Database or NVD and never said product-name
matching is approximate; r1 and r2 (4 of 5 each, on the earlier five-item version) missed the
veto-only reviewer and the sources item respectively. Naming the sources in the always-loaded
core, not only in the reference, is what moved the item. **Bare model:** pushes back on the
idle-repo reasoning and prescribes daily scans, but omits the hosts, every feed, the merge
path and the blind spots, and its SLAs are slower — the gap the rule closes.

## Regression check on the two existing ratchet scenarios

The whole-tree rule touches the paragraph the gate-promotion ladder builds on, so both were
re-run with the skill on the final text: `gate-promotion-ladder` **pass** (5 of 5; carried entry
partial) and `typecheck-gate-required` **partial** (4 of 5; carried entry partial — the missed
item is "ruff subsumes flake8/black/isort", wording this change did not touch). No regression;
the carried entries are kept as recorded, not replaced.

## Provenance

The 65 carried entries are byte-identical to `../2026-09-14-fable/with-skill.json` (checked by
key) except two — `launchd-descriptive-executable-name` and `tdd-regression-red-first` — whose
judge evidence carried the maintainer's home-directory path; it is scrubbed to `$HOME` in this
file only (the older baselines are left as recorded). A scrub step belongs in
`scripts/curate-baseline.py`, with its own red-first test, as a separate change. The two new entries were curated with `scripts/curate-baseline.py` from
`evals/results/2026-10-29-whole-tree-with-skill-fable-r4/` and
`evals/results/2026-10-29-rescan-with-skill-fable-r5/` (git-ignored); `response`,
`workspace_evidence` and `tool_trail` stripped, statuses, judgments and reasons kept. The
earlier with-skill runs (r1–r4), the two bare runs (`…-baseline-fable-r1`) and the two
regression runs (`…-regress-with-skill-fable`) existed only in the writer's git-ignored
`evals/results/` and were removed with its worktree after the PR opened; their verdicts
and per-item counts are as stated above and in the PR body. No `sandbox_escape` on any run.
