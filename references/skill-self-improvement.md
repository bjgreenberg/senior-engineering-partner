# Skill Self-Improvement Loop

Companion reference for the senior-engineering-partner skill.

The core (SKILL.md → *Skill Self-Improvement Loop*) carries the always-loaded trigger:
check **actively** at natural closure points — task complete, session ending, after any
gate failure or human correction — whether the session taught something the skill should
encode, and act on either signal: **(a)** a rule-miss with real cost (the skill was
silent or wrong about something that cost time, money, or data), or **(b)** the human
corrected or extended a discipline. Plus the two invariants that never leave the core:
**consent-gated** (propose, never silently edit) and **add or sharpen only, never
relax**. This file is the procedure to run once a trigger fires.

When the answer at a closure point is "nothing to encode", say nothing — active
detection, quiet output. The check itself is never narrated on routine sessions.

---

## 1. Classify before proposing

| Case | Action |
|---|---|
| **Second instance of a rule class** — the same *kind* of miss has now happened twice (even in different tools/services) | Propose codification now. Two instances is the pattern bar: one miss is an anecdote, two is a rule the skill is missing. |
| **Genuine one-off** | Record it in session memory / the environment profile with enough context to recognize a recurrence; do not propose yet. A skill that codifies every anecdote bloats its core and dilutes its floors. |
| **First instance with *irreversible* cost** — data loss, permanently unattributable history, a leaked secret, an unrecoverable deletion | Propose immediately. Waiting for instance two pays the permanent cost twice; irreversibility substitutes for recurrence. |

Classifying honestly matters more than proposing eagerly: the loop's credibility with
the human depends on proposals being rare and load-bearing.

## 2. Assemble the proposal package

Present all three parts — the human's yes/no gates everything that follows:

1. **The rule**, worded to pass the authoring tests in `CONTRIBUTING.md`:
   *binary imperative* (a gate, not a preference), *diff-checkable observable* (name
   the thing a reviewer or grep can see pass/fail), *timeless* (the durable invariant,
   not a status report). Name where it lands — which SKILL.md section or reference —
   and, if it generalizes an existing rule, cite the rule it generalizes.
2. **The guarding eval** — a new or extended `evals/` scenario whose
   `expected_behavior` / `anti_behavior` would have caught the original miss. A lesson
   without a guarding eval can silently regress; the scenario's `source` field records
   the provenance.
3. **The origin story** — what happened, what it cost, and why the existing rules
   didn't cover it. This becomes the PR body's "why" and, at release time, changelog
   narrative material.

If the human declines, record the lesson and the decline in session memory and stop —
a declined proposal is not re-raised unless new instances change the classification.

## 3. Ship through the repo's own discipline

Branch → local gates (`leakage-guard`, `skill-lint`, render-check if a diagram was
touched) → PR with the what/why/testing shape → **human approval** → squash-merge.
Consent is structural, not prose: the ruleset requires an approval the proposing agent
cannot give itself, so an unapproved self-improvement cannot merge. Word the rule
stack-agnostically — personal hosts, repos, and identifiers stay in the (un-committed)
environment profile, and `leakage-guard` enforces it.

## 4. What the loop may never do

- **Relax, soften, or delete a discipline.** Loosening is human-initiated by
  definition. A self-improvement channel that can weaken rules is a drift vector, not
  evolution — and the temptation is highest exactly when a rule was inconvenient in the
  triggering session.
- **Edit the skill silently**, even when offered blanket trust ("just fix it, don't
  bother me"). The concrete proposal still goes to the human; trust changes the tone of
  the exchange, not the gate.
- **Bundle.** One rule per PR — the human approves each discipline on its own merits.

## 5. Not the repo maintainer?

Same loop, different sink: record the lesson in your own memory /
`references/my-environment.md`, and offer to upstream it to the skill's repo as an
issue or PR. The classification bar and the proposal package are identical — an
upstream maintainer needs the same three parts to evaluate it.

---

## Worked example (the loop's own origin)

The first run of this loop happened by hand, before it was a rule — and produced both
the rule it proposed *and* this loop:

1. **Miss with irreversible cost:** four fleet automations shared two org API keys.
   When per-app cost attribution was requested, the billing surface (which groups by
   credential scope and nothing else) had nothing to attribute — all pre-migration
   spend permanently unattributable. The skill mandated per-repo *deploy keys* but had
   never generalized the principle to other external-service credentials.
2. **Classification:** second instance of the rule class (per-repo deploy keys were
   the first) *and* irreversible cost — qualified twice over.
3. **Proposal with consent:** the rule (*one credential per app/workload, provisioned
   at creation* — SKILL.md → Secrets Management), its guarding eval
   (`per-workload-credential-provisioning.json`), and the origin story; the human
   approved.
4. **Shipped through the discipline:** PR → gates → human approval → merge; the human
   then asked for the loop itself to become a standing capability, choosing **active**
   detection — codified with its own guarding eval
   (`self-improvement-consent-gated.json`), which tests the blanket-trust case.
