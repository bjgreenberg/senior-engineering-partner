# Recorded baseline — 2026-07-05, Opus, 45-scenario suite (skill v1.16.0, harness v2)

**The first baseline recorded under the fixture/tool-grant harness** (#81: fixture
workspaces, `Bash,Edit,Write` grants for claude-runner scenario runs, ordered tool-call
trail + workspace evidence to the judge, staged evals-free skill copy). **No earlier
baseline is comparable to this one** — including the four 2026-07-04 per-model sweeps —
because the earlier harness graded prose-only responses from a model that could not act
(the discontinuity note in [`../../README.md`](../../README.md) governs). The clearest
tell: the bare model now passes 11 scenarios where the 2026-07-02 prose-only bare run
passed 5 — a tool-granted bare model can do real work, so the skill is measured against
an honestly stronger floor.

Produced by `scripts/run-evals.py` at `main` commit `8d78511` (scenario + judge runs
`--model opus --judge-model opus`, `claude` CLI 2.1.197, `--jobs 2 --timeout 900`;
bare sweep first, then with-skill, sequentially). Committed JSONs are slim: statuses +
per-item judgments + judge reasons kept; `response`, `workspace_evidence`, and
`tool_trail` stripped — re-run the sweep to regenerate full transcripts under the
git-ignored `evals/results/`.

**One splice, disclosed:** `adr-must-name-overridden-discipline` errored in the
with-skill sweep — twice, reproducibly — on a judge-output *extraction* bug (the judge
appended prose containing a stray brace after its verdict JSON; the old greedy
first-`{`-to-last-`}` span failed to parse). The extraction was fixed to
`json.JSONDecoder().raw_decode` (first complete object wins; ships in the same PR as
this baseline), and the scenario was re-run once post-fix at the same skill content;
it judged **pass**, which is the entry recorded in `with-skill.json`. The fix touches
judge-output parsing only — no scenario behavior, no grading criteria.

## Headline

| Run | pass | partial | fail | error |
|---|---|---|---|---|
| Bare model (`--mode baseline`) | 11 | 22 | 12 | 0 |
| With the skill (`--mode with-skill`) | **29** | 16 | **0** | 0 |

**Per-scenario: 23 improved with the skill, 22 unchanged, 0 regressed — and the
with-skill fail column is zero for the first time on any recorded sweep.**

## The three sharpened scenarios (this session's targets)

| Scenario | Bare | With skill | Note |
|---|---|---|---|
| tdd-regression-red-first | partial | **pass** | the old durable fail; red-first now proven in the tool trail |
| dependency-manifest-drift | partial | **pass** | incl. the image-scan blind-spot item this sweep |
| stale-diagram-on-behavior-change | partial | partial | every representation updated; the unnamed render-check remains the one standing content target |

## Gap table (bare → with-skill)

| Scenario | Bare | With skill | Δ |
|---|---|---|---|
| adr-must-name-overridden-discipline | pass | pass | ＝ |
| adversarial-review-green-but-insufficient | partial | partial | ＝ |
| apps-script-least-privilege-scope | fail | partial | ⬆ |
| badge-row-required-on-repo | fail | partial | ⬆ |
| badge-verify-claimed-level-not-just-200 | pass | pass | ＝ |
| bash-injection-eval | pass | pass | ＝ |
| bash-strict-mode-pitfalls | partial | partial | ＝ |
| citation-cff-no-hand-maintained-version | partial | partial | ＝ |
| crypto-agility-pqc-hndl | fail | partial | ⬆ |
| csv-formula-injection-export | pass | pass | ＝ |
| debug-false-negative-search | pass | pass | ＝ |
| debug-root-cause-not-symptom | partial | partial | ＝ |
| degrade-dont-crash-on-dependency-failure | fail | partial | ⬆ |
| dependency-currency-not-just-pinned | partial | pass | ⬆ |
| dependency-manifest-drift | partial | pass | ⬆ |
| environment-binding-not-mandate | pass | pass | ＝ |
| fail-closed-not-degraded-success | pass | pass | ＝ |
| fda-compiled-launcher | fail | partial | ⬆ |
| frontend-testing-behavior-not-implementation | partial | pass | ⬆ |
| graceful-shutdown-sigterm | fail | pass | ⬆ |
| honest-badges-only | pass | pass | ＝ |
| host-os-binding-logs-and-least-privilege | fail | pass | ⬆ |
| immutable-backup-not-just-versioning | partial | pass | ⬆ |
| llm-loop-stopping-criteria | partial | partial | ＝ |
| log-injection-sanitize | partial | pass | ⬆ |
| preserve-input-on-failed-submit | fail | pass | ⬆ |
| prompt-injection-structural-fence | pass | pass | ＝ |
| rag-vector-store-tenant-isolation | partial | pass | ⬆ |
| restore-drill-required | partial | partial | ＝ |
| rls-cross-tenant-deny | partial | partial | ＝ |
| rls-superuser-parity-gate | partial | partial | ＝ |
| sbom-provenance-on-release | partial | pass | ⬆ |
| scalability-db-pool-ceiling | partial | partial | ＝ |
| scm-triage-reviews-before-merge | partial | pass | ⬆ |
| secrets-never-hardcoded | pass | pass | ＝ |
| single-file-vs-package-decision | partial | partial | ＝ |
| spec-first-gate | partial | pass | ⬆ |
| squash-not-rebase-merge | partial | pass | ⬆ |
| stale-diagram-on-behavior-change | partial | partial | ＝ |
| standards-authoring-timeless-enforceable | fail | pass | ⬆ |
| stateless-for-horizontal-scale | fail | pass | ⬆ |
| tdd-regression-red-first | partial | pass | ⬆ |
| typecheck-gate-required | fail | pass | ⬆ |
| typeddict-not-dict-any | fail | pass | ⬆ |
| yagni-no-speculative-abstraction | pass | pass | ＝ |

## Harness caveats

- Scenario runs execute with `Bash,Edit,Write` on the invoking host (see the security
  note in `evals/README.md`); runs inherit the invoking environment's global agent
  context (user-level memory/hooks) — an open harness-isolation decision, disclosed in
  #81 and #79.
- Judge-model self-family bias remains an uncontrolled variable (same instrument across
  both modes, so the *gap* is unaffected).
- With-skill partials cluster on narration-depth items (naming a blind spot, naming an
  unrun check) rather than action items — the standing Claude-A content targets.
