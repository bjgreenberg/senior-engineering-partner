# Recorded baseline — 2026-07-04, Fable 5, 45-scenario suite (skill v1.15.0)

The Fable leg of the 2026-07-04 per-model portability sweeps (siblings:
[`2026-07-04-sonnet/`](../2026-07-04-sonnet/BASELINE.md),
[`2026-07-04-haiku/`](../2026-07-04-haiku/BASELINE.md); the Opus reference is
[`2026-07-02-opus/`](../2026-07-02-opus/BASELINE.md), on the then-38-scenario suite —
deltas against it are directional, not like-for-like). Produced by
`scripts/run-evals.py` at branch commit `7c859f8` (scenario runs `--model fable`,
judge runs `--judge-model opus`; `claude` CLI 2.1.201, jobs=3); scenario responses are
stripped from the committed JSONs (statuses + per-item judgments + judge reasons kept —
re-run the sweep to regenerate full transcripts locally under the git-ignored
`evals/results/`).

**One splice, disclosed:** `rls-cross-tenant-deny` hit the harness's default 600s
timeout in the with-skill sweep (`TimeoutExpired`, not a model verdict) and was re-run
once at `--timeout 1200` at the same commit; it completed in 803s and judged
**partial**, which is the entry recorded in `with-skill.json`. The timeout is itself a
finding: with the full skill loaded, Fable routinely works much longer per task —
sweeps on deep-reasoning models should set `--timeout` above the 600s default.

## Headline

| Run | pass | partial | fail | error |
|---|---|---|---|---|
| Bare model (`--mode baseline`) | 8 | 28 | 9 | 0 |
| With the skill (`--mode with-skill`) | **28** | 14 | **3** | 0 |

**Per-scenario: 22 improved with the skill, 23 unchanged, 0 regressed.**

## Gap table (baseline → with-skill)

**Improved (22):** adr-must-name-overridden-discipline (fail→pass) ·
bash-strict-mode-pitfalls (partial→pass) · crypto-agility-pqc-hndl (partial→pass) ·
debug-false-negative-search (partial→pass) · degrade-dont-crash-on-dependency-failure
(partial→pass) · dependency-currency-not-just-pinned (partial→pass) ·
frontend-testing-behavior-not-implementation (partial→pass) · graceful-shutdown-sigterm
(fail→pass) · honest-badges-only (partial→pass) ·
host-os-binding-logs-and-least-privilege (partial→pass) ·
immutable-backup-not-just-versioning (partial→pass) · preserve-input-on-failed-submit
(fail→partial) · rag-vector-store-tenant-isolation (partial→pass) ·
restore-drill-required (partial→pass) · sbom-provenance-on-release (partial→pass) ·
scm-triage-reviews-before-merge (partial→pass) · secrets-never-hardcoded (partial→pass) ·
single-file-vs-package-decision (partial→pass) · squash-not-rebase-merge (partial→pass) ·
standards-authoring-timeless-enforceable (fail→pass) · stateless-for-horizontal-scale
(fail→pass) · typeddict-not-dict-any (fail→partial)

**Unchanged, already pass at baseline (8):** badge-verify-claimed-level-not-just-200 ·
bash-injection-eval · csv-formula-injection-export · environment-binding-not-mandate ·
fail-closed-not-degraded-success · log-injection-sanitize · typecheck-gate-required ·
yagni-no-speculative-abstraction.

**Unchanged, stuck at partial (12):** adversarial-review-green-but-insufficient ·
apps-script-least-privilege-scope · badge-row-required-on-repo ·
citation-cff-no-hand-maintained-version · debug-root-cause-not-symptom ·
fda-compiled-launcher · llm-loop-stopping-criteria · prompt-injection-structural-fence ·
rls-cross-tenant-deny (the 1200s re-run) · rls-superuser-parity-gate ·
scalability-db-pool-ceiling · spec-first-gate.

**Unchanged, stuck at fail (3):** dependency-manifest-drift ·
stale-diagram-on-behavior-change · tdd-regression-red-first.

## What this baseline says about cross-model portability

Fable records the strongest profile of any swept model on both curves: the best bare
baseline (fail 9) *and* the best with-skill result (pass 28, fail 3) — the skill's
value does not vanish up-model; it compounds (22 scenarios improved, the most of any
sweep, largely partial→pass sharpening rather than fail rescues). The three remaining
fails are precisely the **shared durable core** every model fails with the skill
loaded — dependency-manifest-drift, stale-diagram-on-behavior-change,
tdd-regression-red-first — which the Opus baseline already named as content/harness
gaps (two carry its bare-cwd caveat). Notably, adversarial-review-green-but-insufficient
— durably failed on Opus and Haiku — reaches partial here. Cross-model conclusion from
the four recorded sweeps: with identical skill text, with-skill fails run 16 (Haiku 4.5)
→ 7 (Sonnet 5) → 4 (Opus 4.8, older suite) → 3 (Fable 5) — the skill loads everywhere,
and how much of it gets *enforced* tracks model tier.

## Harness caveats

Same harness as the Opus baseline: scenarios run in a bare scratch cwd (scenarios that
presume an existing tree read worse than real use — stale-diagram and tdd-regression
carry this caveat); the `Skill` tool is disallowed and the body is injected via
`--append-system-prompt`. Fable-specific: with-skill runs are markedly slower (the 803s
scenario above; several others exceeded 300s) — budget `--timeout` accordingly. See the
Haiku sibling for the spec-first-vs-single-shot caveat.
