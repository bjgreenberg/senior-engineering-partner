# Maintainability Metrics — complexity & duplication as gates

Companion reference for the senior-engineering-partner skill. Read when wiring quality
gates for a Tier-2 codebase, when a review keeps saying "this function is too complex"
without a number, or when introducing any maintainability tooling.

The core's *MODULAR & REUSABLE CODE* section mandates single-responsibility functions and
no monolithic scripts — but a mandate without a checker that runs is unenforced (the
skill's own type-annotation rule, applied to structure). This reference supplies the
observable: **at Tier 2, maintainability is a gate, not an opinion** — pick an analyzer,
commit its thresholds to a config file in the repo, and fail the build when new or
changed code exceeds them.

## The two metrics that matter (and which variant)

- **Cognitive complexity, not cyclomatic, for "hard to understand".** Cyclomatic
  complexity counts branch paths — it measures how hard code is to *test*. Cognitive
  complexity weights nesting and control-flow breaks and discounts readable shorthand —
  it measures how hard code is to *read*. When a gate exists to keep functions
  comprehensible, gate the cognitive variant where the tool offers it, and say which one
  your threshold means (a "complexity 10" rule is ambiguous across tools).
- **Structural duplication, not textual.** A copy-paste with renamed variables defeats a
  line-based diff but not an AST-fingerprint detector (parse → fingerprint nodes with
  literals/identifiers discarded → match). The core's *reuse before you write* rule
  describes exactly this near-duplicate; structural detection is what finds it
  mechanically. Filter import/use declarations and set a minimum-node floor, or every
  file header becomes a "duplicate".

## Reference thresholds (a vetted starting point)

Verified defaults from qlty's analyzer (`qlty-config/default.toml`, v0.641.0) — a
reasonable, battle-tested starting posture; commit whatever you choose to the repo:

| Check | Default |
|---|---|
| Boolean operators in one expression | 4 |
| Nested control-flow depth | 5 |
| Function parameters | 6 |
| Return statements | 6 |
| File complexity (cognitive, whole file) | 50 |
| Function complexity (cognitive) | 18 |
| Identical / structurally-similar code (lines) | 15 |

Thresholds are a *policy decision recorded in config*, not tool trivia: **raising a
threshold to make a build pass is an ADR-worthy decision** (name the rule it relaxes),
never a quiet config tweak in a feature PR.

## Tool bindings (examples, not mandates — environment-binding rule)

| Scope | Binding | Gate invocation |
|---|---|---|
| Multi-language, one tool | **qlty** (`qlty smells`, tree-sitter engine) | `qlty check` (diff-scoped by default; `--all` for sweeps) |
| Python | **radon** (metrics) + **xenon** (CI enforcement) | `xenon --max-absolute B --max-average A src/` — non-zero exit on breach |
| Multi-language CCN + params | **lizard** (~15 languages incl. Swift) | `lizard -C 18 -a 6 --warnings_only` (exit non-zero via `-E ns` options per docs) |
| JS/TS | ESLint core rules | `complexity`, `max-depth`, `max-params`, `max-lines-per-function` as `error` |
| Duplication | **jscpd** (many languages) or PMD/CPD | `jscpd --threshold <pct> --exitCode 1` |
| Rust | clippy | `#![warn(clippy::cognitive_complexity)]` + `-D warnings` in CI |

**License note on qlty:** BUSL-1.1 (Fair Source, *not* open source; converts to GPL-3.0
in 2028). Running it on your own repos — including commercially — is permitted; building
it into a product that offers code review/generation to third parties is not. Read the
license before binding it into anything shipped (the FOSS-adoption checklist's first
line, which its own "open-source" README does not satisfy). The other bindings above are
standard OSS licenses.

*Verify flags against each tool's current docs before wiring a gate — several (lizard's
exit-code options, jscpd's threshold semantics) change between versions.*

## Legacy code: ratchet, don't blanket-disable

The same posture as the core's `mypy --strict` ratchet, generalized: on an existing
codebase the gate applies to **new and changed code** (diff-scoped runs — e.g.
`qlty check` against the merge base, or a wrapper that lints only files touched by the
PR); the legacy tail is monitored, not gated, and the gated set widens over time. A
blanket exclusion that never shrinks is a disabled gate wearing a config file.

## Tier scaling

- **Tier 0:** skip entirely — structure churn is the point of a spike.
- **Tier 1:** run the analyzer in report-only mode if it's cheap; defer the gate with a
  `TODO(promotion: Tier 2)`.
- **Tier 2:** the gate is merge-blocking, thresholds committed, exceptions carry an
  inline suppression comment with a written reason (the `# nosemgrep`-style discipline —
  never a blanket disable).
