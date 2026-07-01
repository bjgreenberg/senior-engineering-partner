# Standards Authoring: distill sprawling conventions into checkable rules

Companion reference for the senior-engineering-partner skill.

Most of this skill *applies* standards to code you write or review. This reference is the inverse:
turning a project's accumulated, scattered conventions — a 2,000-line `CLAUDE.md`, a `.cursorrules`
file, a pile of `*_guidelines.md`, tribal knowledge — into an **enforceable, checkable standards
set**. It is a **guided, interactive procedure you run *with* the user**, never an automated rewrite:
the user owns which conventions become binding rules. And it is **format-agnostic** — prose in the
project's convention doc by default; a machine-checkable set (ids + acceptance criteria + a validator)
only when a gate will actually consume it (see *Prose-first* below).

---

### When this earns its keep

Reach for it when the conventions are **scattered, duplicated, or contradictory** across many files,
when nobody can tell a hard rule from a suggestion, or when you want new code checked against a
canonical set (in review, in CI, or by this skill). **Skip it** when a short `CLAUDE.md` already says
what matters — a standards system on a small or throwaway project is overhead you don't need (YAGNI;
SKILL.md *MODULAR & REUSABLE CODE*). State the tier; a Tier-0 spike doesn't get a standards set.

## The method

**0. Orient before extracting.** Read whatever standards/ADRs already exist so you don't propose
duplicates or re-litigate a settled decision. Note the tier and the stack.

**1. Discover sources — prose AND ground truth.**
- *Prose (stated intent):* `CLAUDE.md`/`AGENTS.md`, `.cursorrules`/`.windsurfrules`, READMEs, and
  `*_guidelines`/`*_conventions`/`*_rules` docs.
- *Ground truth (actual practice — authoritative for structural rules):* the schema/migrations, the
  lint/format/type config (`.eslintrc*`, `ruff`/`pyproject.toml`, `tsconfig*.json`), the CI workflows.
- **Where prose and ground truth disagree, ground truth wins** — and the disagreement is itself a
  finding to surface (the doc says one thing, the code enforces another).

**2. Extract candidates, then run three filters** (the heart of it):
- **Timeless, not a status report.** Strip *currently / legacy / not-yet / tracked / TODO / we're
  migrating* framing — that describes a moment, and a standard outlives the moment. A candidate that's
  really a complaint about the present goes on a **discovered-issues** list (file it as an issue), not
  into the standards.
- **Enforceable, not a vibe.** Reshape into a **binary imperative** with an **observable acceptance
  criterion** a reviewer, a `grep`, or a test can check pass/fail. If a rule is genuinely a judgment
  call ("domains model subjects, not roles"), *say so* and keep it as guidance with the closest
  observable proxy — never dress a vague rule as a deterministic gate. (Same falsifiability standard as
  `audit-report-format.md` — every finding falsifiable — applied to rule-writing.)
- **Dedup / resolve conflict.** Already covered by an existing standard → drop it. Several candidates
  about one policy → **one canonical rule + cross-references**, not duplicated gates (the reuse /
  rule-of-three discipline, SKILL.md *MODULAR & REUSABLE CODE*).

**3. Present for approval — write nothing unapproved.** Show a summary (counts, conflicts) and each
proposed rule, and take an explicit **yes / no / edit** per rule. This is the skill's spec-first +
*don't widen scope silently* discipline: the user decides which conventions become binding. Offer to
file the discovered-issues separately, with their go-ahead.

**4. Classify floor-vs-overridable, then write + validate.**
- **Floor (never overridable):** the absolute invariants — no hardcoded secrets, input validation at
  boundaries, injection prevention, environment isolation, authentication, tenant isolation. Word them
  with **no exception clause**.
- **Overridable:** everything else — a tier-scaled or stylistic rule a documented ADR can waive *by
  naming it* (SKILL.md *DOCUMENTATION* → the ADR-override rule).
- Give each rule a **stable id you never reuse or renumber** (gaps are fine — a retired rule's id stays
  retired). If the output is machine-checkable, add a **validator** that fails the build on a
  malformed, duplicate-id, or broken-cross-reference rule — the deterministic-first discipline applied
  to the standards set itself.

## Prose-first — earn the JSON

A structured, schema-validated standards set (stable ids + `acceptance_criteria` + a validator) is
powerful *when an automated reviewer or a CI gate consumes it* — and inert overhead when nothing
mechanically reads it. **Default to prose** in the project's convention doc; graduate to a
machine-checkable format only when a gate (a review bot, a CI check, a linter config) will actually
enforce it. Match the format to the enforcement, not to the ambition — a JSON standards set no tool
reads is just a less-readable `CLAUDE.md`.

## Tie the rigor to phase (Rigor Ladder)

- **Tier 0–1:** capture the handful of rules that actually bite in a short prose doc; don't build a
  standards *system*.
- **Tier 2 / multi-contributor:** run the full extract → filter → approve → classify pass, and produce
  a machine-checkable set + validator **where CI can enforce it** — so a rule violation fails a PR at
  the source, the same posture as the skill's other required gates.

Cross-references: SKILL.md *MODULAR & REUSABLE CODE* (reuse / rule-of-three / YAGNI — don't over-build
the standards system), *DOCUMENTATION* (ADRs and the ADR-override / floor-never-overridable rule),
*PROJECT PHASE & RIGOR LADDER* (match depth to tier); `references/audit-report-format.md` (the
falsifiability standard the enforceability filter borrows).
