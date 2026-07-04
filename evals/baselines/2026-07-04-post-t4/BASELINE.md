# Validation record — 2026-07-04, tranche-4 compressed core, 45-scenario suite (skill v1.15.0 + tranche 4)

Not a fresh baseline pair: this directory records the **post-edit validation** of the
tranche-4 SKILL.md token-mass reduction (core ~23.7k → ~19.4k approx tokens, rules-lossless
by construction — see the tranche-4 commit) against the same-day **pre-edit** references in
[`2026-07-04-fable/`](../2026-07-04-fable/BASELINE.md),
[`2026-07-04-sonnet/`](../2026-07-04-sonnet/BASELINE.md), and
[`2026-07-04-haiku/`](../2026-07-04-haiku/BASELINE.md). Bare-model baselines are unchanged
by a skill edit, so only the with-skill mode was re-swept (opus judge, `claude` CLI 2.1.201;
fable at `--timeout 1200`). Every per-scenario drop was single-probe re-run at the same
commit before being adjudicated — the house method.

## Headline (with-skill, pre-edit → post-edit)

| Model | pre (pass/partial/fail) | post | improved | dropped | drops adjudicated as |
|---|---|---|---|---|---|
| Fable 5 | 28 / 14 / 3 | 26 / 15 / 4 | 3 | 6 | 4 variance (recovered on re-probe, incl. typeddict to its pre-level) · 1 near-pass boundary (restore-drill) · 1 pre-existing intra-skill tension (yagni, below) |
| Sonnet 5 | 16 / 22 / 7 | 18 / 18 / 9 | 8 | 7 | 4 variance (recovered) · 1 ask-first trait (typeddict) · 2 boundary partials on substantively-strong responses |
| Haiku 4.5 | 13 / 16 / 16 | 12 / 20 / 13 | 10 | 7 | 2 variance (recovered) · 2 ask-first trait (rule text verified intact) · 3 boundary partials |

**No drop, on any model, traces to lost or weakened skill text.** For every regressed
scenario the anchoring rule was located verbatim-or-stronger in the compressed core (e.g.
the CWE-117 bullet, the mypy-gate mandate and the "annotation you never check is a comment"
aphorism, the preserve-input rule); the failing transcripts show response-level omission or
ask-first behavior, not missing instruction. This matches the pre-merge adversarial review:
a cross-section double-cut hunt over the whole file found zero multi-stated rules lost, and
a displaced-content audit confirmed every cut detail lands in its named reference.

Notable gains from the compression itself: several long-stuck scenarios improved —
adversarial-review-green-but-insufficient reached partial on Haiku, badge-row-required
improved on Haiku AND Sonnet, honest-badges/restore-drill/degrade-dont-crash improved on
both smaller models, and spec-first-gate + citation-cff reached pass on Fable.

## Caveats this validation surfaced

- **Ask-first in a single-shot harness** (pre-existing; documented on the pre-edit Haiku
  baseline the same day): with the skill loaded, a model sometimes applies the spec-first
  gate and asks for missing context instead of building; a one-turn judge scores that as
  satisfying nothing. It accounts for the only fail-level reproduced drops (haiku
  log-injection + csv-formula, sonnet typeddict re-probe). The spec-first text is
  byte-identical pre/post tranche — this is a harness-vs-skill trait, not a tranche effect,
  though small-model frequency may drift run to run.
- **yagni-vs-MODULARIZATION.md tension** (pre-existing): the skill mandates a
  `MODULARIZATION.md` migration spec for single-file scripts, while the yagni scenario's
  anti_behavior treats shipping one (with named future extension points) as speculative
  design. Fable hit it once post-edit. Sharpening candidate: scope the scenario's
  anti_behavior, or scope the MODULARIZATION.md rule to "when packaging pressure exists."
- **Fable + full skill is slow**: keep `--timeout 1200` for fable sweeps (one pre-edit
  scenario ran 803s; the post-edit sweep completed within budget).

## Verdict

Tranche 4 ships: ~18% of the always-loaded core removed with zero confirmed rule loss,
net-positive or wash on every model's with-skill profile (haiku fails 16→13, sonnet passes
16→18, fable within noise of its ceiling), and the durable-fail core is unchanged
(dependency-manifest-drift · stale-diagram-on-behavior-change · tdd-regression-red-first) —
still the standing content gap, unrelated to size.
