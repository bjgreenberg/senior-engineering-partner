# Engineering Workflow (spec → plan → build → verify)

Companion reference for the senior-engineering-partner skill.

> **Rigor tier:** the *loop* below holds at every tier; its **depth is tier-aware** (SKILL.md *Project Phase & Rigor Ladder*). A Tier-0 spike gets a one-line spec and test-after; a Tier-2 commercial change gets a written mini-spec, a task plan, and iron-law TDD. What never scales down is the discipline of *deciding what you're building before you build it* and *proving it works before you call it done*.

The rest of this skill says **what good looks like** (the standards). This file says **how the work is driven** — the loop a senior engineer runs so the standards actually get met instead of admired. The failure mode it prevents: jumping straight to code, producing something plausible, and discovering only later that it solved the wrong problem or quietly broke a neighbour. Anchor every loop in the *Epistemic Discipline* (verify before asserting) and the *Definition of Done* in SKILL.md — this file is the connective tissue between them.

The four phases are **Spec → Plan → Build (TDD) → Verify**. They are not bureaucracy; each is a cheap gate that catches an expensive class of error early.

---

## 1. Spec-first gate — decide what you're building before you build it

Before any non-trivial change, **state the spec and get agreement** — don't infer it silently from a one-line prompt. The single highest-leverage move in the whole loop: a wrong line of code costs minutes; a wrong *understanding* costs the whole change.

- **Extract, don't assume.** When the request is ambiguous, ask the few questions that actually change the build (inputs/outputs, the trust boundary, the success criterion, what's explicitly out of scope) — then restate your understanding back. One round of "here's what I think you're asking" beats three rounds of rework. (This is the *don't widen scope silently* rule from Epistemic Discipline, applied at the start instead of mid-flight.)
- **Present it in digestible chunks.** For anything with real surface area, write the spec in short sections the user can actually read and sign off — not a wall of text, not a finished implementation presented as a fait accompli. Get a "yes" on the shape before writing the body.
- **Tier-aware depth:**
  - *Tier 0:* one sentence restating the goal + the success check. Often inline; no ceremony.
  - *Tier 1:* a short written spec — inputs, outputs, the one critical path, what's deferred.
  - *Tier 2:* a written mini-spec **plus** the threat-model lines for any high-risk surface (auth, multi-tenancy, file ingestion, billing, secrets) — see `threat-modeling-and-api-design.md`; the threat model is *part of* the spec, not a later pass. Record non-obvious decisions as an ADR (SKILL.md *Documentation*).
- **The spec is the rubric.** Everything downstream — the plan, the tests, the self-review — checks against this spec. If you can't write the success criterion, you can't test it, which means you don't yet understand the task. Stop and resolve that first.

## 2. Planning discipline — break it into verifiable steps

Once the spec is agreed, **plan before you code** for anything beyond a one-file change. The plan is a list of small, independently-verifiable steps, each with the exact file(s) it touches and the check that proves it done.

- **Small steps with a verification each.** A step you can't verify is a step you can't trust. "Add the `usage_events` insert + a test that asserts the row and the tenant scope" is a step; "implement billing" is a wish. Prefer steps small enough to land and verify in one sitting.
- **Name the files and the reuse.** State which existing functions/utilities the step reuses (the *don't reinvent* rule) and which files it creates or edits — so the diff is predictable and the review is bounded.
- **Sequence by risk and dependency.** Do the load-bearing/uncertain piece first (fail fast while it's cheap to change direction); leave mechanical follow-on for last.
- **For multi-step or parallel work, use a copy-into-response checklist** (Anthropic's workflow pattern) so progress is trackable and nothing is silently skipped:
  ```
  Plan:
  - [ ] Step 1: <change> in <path> — verified by <check>
  - [ ] Step 2: ...
  ```
- This phase composes with the harness's own plan mode and with `multi-agent-coordination.md` when more than one writer shares the tree. It does **not** replace the *Definition of Done* — it feeds it.

## 3. Build with tier-aware iron-law TDD

The skill already mandates tests (SKILL.md *Automated QA & Testing*, `testing.md`). This is the **loop** that produces them — **RED → GREEN → REFACTOR** — and it runs *test-first* with a strictness that scales by tier.

**The cycle:**
1. **RED — write the failing test first, and *watch it fail*.** A test you've never seen fail proves nothing — it may be asserting nothing, or passing for the wrong reason. Run it; confirm it fails for the *expected* reason (the assertion, not an import error).
2. **GREEN — write the minimum code to make it pass.** No more. Resist building ahead of a test.
3. **REFACTOR — clean it up with the test as your safety net.** Tests stay green throughout.

**Tier-aware strictness (this is the differentiator — a blanket iron law over-taxes a throwaway spike):**

| Tier | TDD posture |
|---|---|
| **Tier 2 — production/commercial** | **Iron law.** Test-first, no exceptions, for all logic on the auth/RLS/parser/billing paths. Code written before its test is suspect — prefer to delete it and re-derive it test-first rather than retrofit a test to code you've already convinced yourself is right (a retrofitted test tends to assert what the code *does*, not what it *should*). Every bugfix starts with a regression test seen to fail red (the *per-change-class merge contract* in `testing.md`). |
| **Tier 1 — MVP / early product** | **Test-first strongly preferred** on the critical path; pragmatic test-after acceptable for peripheral glue, but the critical path is never shipped untested. |
| **Tier 0 — prototype / spike** | **Test-after acceptable**; at minimum a smoke test that the thing runs. Don't let TDD ceremony kill a time-boxed spike — but the security floor (no hardcoded secrets, input validation, isolation) still holds. |

**Non-negotiable at every tier (from `testing.md`, restated because it's load-bearing here):** when a test reveals real behaviour differing from your expectation, **fix the test AND comment WHY** — never delete a failing test, retry it to green, or `xfail` it to unblock a merge. A green suite you reached by deleting the red is a lie you're telling future-you.

Mechanize the loop where you can: a failing repro is often a deterministic script (the *deterministic-first* rule) — write it once, keep it as the regression test. For single-file scripts, the RED test uses the `conftest.py` argv-patch harness in `testing-single-file.md`.

## 4. Verify before done — the self-review gate

Before declaring a change complete, run a **structured self-review** over the diff and **record that you did**. This generalizes the v5.9 rule ("when the automated reviewer is unavailable, do a documented self-review in its place") into an always-on gate: the bot reviewer (where present) is a *second* opinion, never a substitute for your own pass. CI proves the gates pass; it does not prove the change is *correct, secure, and tenant-isolated*.

**Review your own diff against these dimensions** (use `scripts/self-review.md` as the copy-into-response checklist):

- **Correctness & edge cases** — does it meet the *spec's* success criterion (not just "runs")? Empty input, boundary values, the error path, idempotency for anything re-runnable.
- **Security floor** — no hardcoded secrets, inputs validated at the boundary, no command/SQL injection, least privilege. (SKILL.md *Strict Security Protocols*.)
- **Tenant isolation** (Tier 2) — every new query/endpoint/cache key is tenant-scoped; the DENY is tested, not just the allow (`testing.md` §2, `caching.md`).
- **Blast radius** — what *else* touches this code path? Did a behaviour change leave a neighbour, a diagram, or a numbered step-list stale? (SKILL.md *Documentation* — hunt down every representation.)
- **The diff's own risk areas** — whatever is genuinely novel or fragile *in this change* gets extra scrutiny; you know where the bodies are buried.

Then close out the real *Definition of Done* (SKILL.md): docs/CHANGELOG in the same commit, tests + linters green (quote the actual output — never claim a result you didn't observe), working tree clean, `HEAD == origin`. **State the self-review outcome explicitly** ("self-reviewed against correctness/security/isolation; no findings" or the findings + fixes) so the gate is visible, not silently skipped — exactly as you'd record an unavailable bot reviewer.

## 5. Changing legacy / untested code — pin it before you touch it

The loop above assumes you *can* write the RED test first. Legacy code often won't let you — no seam to inject a test, behaviour nobody can fully state. The senior move is to make it testable *before* you change it, not to edit blind and hope (the *deterministic-first* / verify-before-asserting discipline applied to inherited code). Lineage: Feathers, *Working Effectively with Legacy Code*.

- **Characterization test first — pin what it *does*, not what it *should*.** Before changing behaviour you don't fully understand, write a test that captures the *current* output for representative (and edge) inputs — even if that output looks wrong. The point isn't correctness; it's a tripwire: now any behaviour change you didn't intend turns the suite red. *Then* you change it — and if a characterization test flips, that's the load-bearing moment: decide whether the old behaviour was a bug to fix (update the test **and comment WHY**, §3's non-negotiable) or a contract to preserve. Never silently re-baseline.
- **Find the seam to break the dependency.** A seam is a place you can substitute behaviour for testing without rewriting the unit — inject the collaborator, pass a fake clock/HTTP client, extract the hard-wired global to a parameter. The smallest seam that lets a characterization test run beats a heroic refactor you can't yet verify. (This is `foss-adoption.md`'s thin-contract-test seam, turned inward on your own legacy.)
- **Strangler-fig for replacing a whole legacy path — never a big-bang rewrite.** Stand the new implementation up *beside* the old one behind a flag/router; move callers over incrementally, with the characterization tests proving each slice is behaviour-equivalent; delete the old path only once nothing routes to it. Incremental + reversible + observable beats a cut-over rewrite (Fowler, *Strangler Fig*) — the flag is your rollback. For Tier 2, run new-and-old in parallel and diff outputs before flipping the default.
- **Fix it at the source the moment you trip over it — that's the default; deferring is the exception.** When work surfaces a *different*, small, fixable problem — a latent bug, a stale comment, a false-positive in a guard, a wrong assumption — the cheap-and-correct move is usually to fix it **now, at its root**, while the context is loaded and the cause is in view, rather than papering over it locally (a workaround you then have to remember and unwind) or filing it for a "later" that compounds. Fixing the *cause* once is cheaper than the symptom-patch **plus** the eventual root-cause hunt **plus** everything else that breaks on the same root in between; small unaddressed issues don't stay small, they accrete until the workarounds are load-bearing. This is the proactive twin of `debugging.md`'s *fix the root cause, not the symptom* — don't wait for a bug report to apply it. Two guardrails: (a) keep the fix in its own commit so it doesn't bloat or obscure the change you came to make; (b) in a shared tree, a problem that belongs to *someone else's* in-flight work is **flagged to its owner, not absorbed into yours** (`multi-agent-coordination.md`). When you genuinely *can't* fix it in-flight — out of scope, needs a decision, would balloon the diff — that's when you reach for the register:
- **Record the debt you defer — a tracked item with a promotion trigger, not a silent `# FIXME`.** Same pattern as the MVP *defer-with-`TODO`* rule (SKILL.md): when you knowingly leave a seam uncut, a path uncharacterized, or a legacy branch un-strangled, log it as a real tracked item — what's owed, the risk if left, and the **promotion trigger** that forces payback ("when this parser next takes untrusted input" · "before a second caller depends on it" · "the moment it touches tenant data"). A bare TODO with no trigger and no owner is how debt compounds — the bar quietly lowers until the shortcut is the norm. The register makes the debt visible and re-rateable, exactly like a Tier-0 spike that crosses a promotion trigger and re-enters the loop at depth.

---

## The loop, end to end

```
Spec (agree what)  →  Plan (verifiable steps)  →  Build (RED→GREEN→REFACTOR, tier-aware)  →  Verify (self-review + Definition of Done)
        ↑                                                                                              │
        └────────────────────── new understanding re-opens the spec ───────────────────────────────────┘
```

Skipping a phase doesn't save time — it moves the cost downstream, where it's larger. The spike that "doesn't need a plan" is exactly the one that quietly grows past Tier 0 (a *promotion trigger*) and now carries untested commercial logic. Re-rate it and re-enter the loop at the right depth. This is the same posture as the rest of the skill: **match effort to phase, never relax the floor.**
