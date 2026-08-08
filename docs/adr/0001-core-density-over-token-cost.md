# ADR 0001 — Keep the always-loaded core dense; compression must pay per section, in evals

- **Status:** Accepted (2026-07-27; recorded as an ADR 2026-08-08)
- **Deciders:** maintainer (Brian Greenberg), on the evidence of the tranche-5 experiment
- **Evidence of record:** [`evals/baselines/2026-07-27-postdiet-experiment/EXPERIMENT.md`](../../evals/baselines/2026-07-27-postdiet-experiment/EXPERIMENT.md); refuted change: PR #119 (`feat/core-diet-tranche5` @ `a8ae524`, closed unmerged)

## Context

`SKILL.md` is the always-loaded core: every session pays its token cost before any work
starts. A 2026-07-27 audit proposed compressing it 12,490 → 8,630 body words (−31%) by
relocating in-core mechanics to read-on-demand references, hypothesizing equal or better
eval performance (less salience dilution, especially down-model). The skill's own
progressive-disclosure design made this plausible: triggers in the core, detail in
references.

## Decision

**The core keeps its density.** The `CORE_WORD_BUDGET` ratchet stays at 12,700 words —
a ceiling against unbounded growth, not a target to diet toward. Any future compression
of the core must be proposed **section by section**, and each section's move is gated on
that section's **guarding eval scenarios holding** in a same-harness with-skill sweep —
never a wholesale diet justified by token savings alone.

## Consequences

- **Token cost is accepted as purchased behavior.** The trade was measured, not assumed:
  −31% tokens cost −4 pass / +2 fail on Opus (7 scenarios regressed) and −5 pass / +7
  fail on Haiku (16 regressed), same day, same harness, same judge. The regressions
  mapped directly onto the relocated content.
- **The mechanism is now a documented design premise:** in eval conditions the model
  frequently acts without first reading the reference a trigger points at, so a
  trigger-plus-pointer carries measurably less behavior than the inlined rule — and
  small models lean on in-core detail *more*, not less (the salience-dilution premise
  inverted).
- New core additions stay word-frugal (trigger sentences in the core, substance in
  references) because the budget ceiling is real — but frugality is enforced by the
  ratchet, not by dieting existing, eval-guarded text.
- The experiment record and its sweeps remain in `evals/baselines/` as the comparison
  control for any future core edit.

## Alternatives rejected

- **Wholesale compression (PR #119):** refuted by its own eval sweep; closed unmerged.
  The branch is retained locally for provenance (`EXPERIMENT.md` cites `a8ae524`).
- **Raising the word budget instead:** rejected — an unbounded core re-creates the
  context-tax failure mode the skill criticizes elsewhere (a catalog that costs more
  than it teaches). The ceiling stands; it just isn't a diet mandate.
- **Compressing only for small models (a Haiku-specific core):** rejected — forked cores
  drift, and the same experiment showed Haiku is *more* dependent on in-core detail.

## Supersession

Supersede with a new ADR only on new eval evidence (a section-by-section compression
whose guarding scenarios hold, or a harness/model change that re-opens the question).
Never edit this record.
