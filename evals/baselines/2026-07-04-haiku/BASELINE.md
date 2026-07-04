# Recorded baseline — 2026-07-04, Haiku 4.5, 45-scenario suite (skill v1.15.0)

The first non-Opus model sweep: the reference measurement for how the skill performs on
**Haiku 4.5** — taken to answer "does the skill work equally well across Claude models?"
with numbers instead of assumption (its Sonnet and Fable siblings were swept the same
day; the Opus reference is [`2026-07-02-opus/`](../2026-07-02-opus/BASELINE.md), on the
then-38-scenario suite — deltas against it are directional, not like-for-like). Produced
by `scripts/run-evals.py` at branch commit `7c859f8` (scenario runs `--model haiku`,
judge runs `--judge-model opus`; `claude` CLI 2.1.201, jobs=4); scenario responses are
stripped from the committed JSONs (statuses + per-item judgments + judge reasons kept —
re-run the sweep to regenerate full transcripts locally under the git-ignored
`evals/results/`).

## Headline

| Run | pass | partial | fail | error |
|---|---|---|---|---|
| Bare model (`--mode baseline`) | 3 | 19 | 23 | 0 |
| With the skill (`--mode with-skill`) | **13** | 16 | **16** | 0 |

**Per-scenario: 15 improved with the skill, 29 unchanged, 1 regressed (re-probed as
variance — see below).**

## Gap table (baseline → with-skill)

**Improved (15):** adr-must-name-overridden-discipline (partial→pass) ·
badge-verify-claimed-level-not-just-200 (partial→pass) ·
citation-cff-no-hand-maintained-version (fail→partial) · debug-false-negative-search
(fail→pass) · dependency-currency-not-just-pinned (partial→pass) · fda-compiled-launcher
(fail→partial) · immutable-backup-not-just-versioning (partial→pass) ·
log-injection-sanitize (partial→pass) · preserve-input-on-failed-submit (fail→partial) ·
prompt-injection-structural-fence (fail→partial) · scalability-db-pool-ceiling
(partial→pass) · scm-triage-reviews-before-merge (partial→pass) · secrets-never-hardcoded
(fail→pass) · standards-authoring-timeless-enforceable (fail→pass) ·
typecheck-gate-required (fail→partial)

**Regressed (1):** rls-cross-tenant-deny (partial→fail). A single-probe re-run at the
same commit came back **partial** — treat the flip as variance, not a durable regression.
The failing transcript is still instructive: with the skill loaded, Haiku applied the
spec-first gate and *asked for the codebase* instead of implementing, which a single-shot
judge scores as satisfying nothing. A discipline written for interactive sessions can
read as non-delivery in a one-turn harness — a caveat of this suite, same family as the
bare-cwd caveat in the Opus baseline.

**Unchanged, already pass at baseline (3):** bash-injection-eval ·
environment-binding-not-mandate · fail-closed-not-degraded-success.

**Unchanged, stuck at partial (11):** csv-formula-injection-export ·
debug-root-cause-not-symptom · frontend-testing-behavior-not-implementation ·
honest-badges-only · llm-loop-stopping-criteria · rag-vector-store-tenant-isolation ·
restore-drill-required · sbom-provenance-on-release · single-file-vs-package-decision ·
spec-first-gate · squash-not-rebase-merge.

**Unchanged, stuck at fail (15):** adversarial-review-green-but-insufficient ·
apps-script-least-privilege-scope · badge-row-required-on-repo ·
bash-strict-mode-pitfalls · crypto-agility-pqc-hndl ·
degrade-dont-crash-on-dependency-failure · dependency-manifest-drift ·
graceful-shutdown-sigterm · host-os-binding-logs-and-least-privilege ·
rls-superuser-parity-gate · stale-diagram-on-behavior-change ·
stateless-for-horizontal-scale · tdd-regression-red-first · typeddict-not-dict-any ·
yagni-no-speculative-abstraction.

## What this baseline says about cross-model portability

The skill helps Haiku a lot (pass 3→13, fail 23→16) — the *relative* lift is larger than
on Opus, because the bare baseline is much weaker. But the with-skill ceiling is far
lower: **15 scenarios stay failed on Haiku with the skill loaded** where the Opus
with-skill run left only 4 (older suite; directional). The instruction mass appears to
exceed what Haiku reliably executes in one turn — several stuck-fails (typeddict,
graceful-shutdown, stateless-scale, yagni) are disciplines Opus clears *with the same
skill text*. Conclusion the numbers support: the skill's content transfers down-model,
its enforcement reliability does not — "works on every Claude model" is true for loading
and false as an equal-quality claim.

## Harness caveats

Same harness as the Opus baseline: scenarios run in a bare scratch cwd (scenarios that
presume an existing tree read worse than real use); the `Skill` tool is disallowed and
the body is injected via `--append-system-prompt`. Separately verified this same day (not
part of this sweep): the real Claude Code skill loader delivers the full SKILL.md body
un-truncated on `claude` CLI 2.1.201, confirmed by verbatim quoting of the file's final
sentences from a live session.
