# Self-Review Checklist (verify before done)

The copy-into-response checklist for the **verify-before-done gate** (`references/engineering-workflow.md` §4).
Run it over your own diff *before* declaring a change complete, and **record the outcome** in the PR/handoff —
the bot reviewer (where present) is a second opinion, never a substitute. CI proves the gates pass; it does not
prove the change is correct, secure, and tenant-isolated.

Copy this into your response and check each box (tier-aware: isolation/Tier-2 rows are N/A below Tier 2):

```
Self-review (vs. the agreed spec):
- [ ] Correctness — meets the spec's success criterion, not just "runs"
- [ ] Edge cases — empty/boundary input, the error path, idempotency for anything re-runnable
- [ ] Security floor — no hardcoded secrets, inputs validated at the boundary, no command/SQL injection, least privilege
- [ ] Tenant isolation (Tier 2) — every new query/endpoint/cache key tenant-scoped; the DENY is tested, not just the allow
- [ ] Blast radius — neighbours, diagrams, and numbered step-lists touched by a behaviour change are updated (same commit)
- [ ] This diff's own risk areas — whatever is novel/fragile here got extra scrutiny
- [ ] Tests — new/changed logic has tests; bugfix has a regression test seen to fail red first; suite + linters green
- [ ] Docs — README (+ Last updated stamp), CHANGELOG, ADR for non-obvious decisions, in the SAME commit
- [ ] Definition of Done — working tree clean, HEAD == origin, results quoted from actual command output (not memory)
```

**Then state the result explicitly**, e.g.:
> Self-reviewed against correctness / security / tenant-isolation / blast-radius — no findings. Tests green
> (quote the run). [If the automated reviewer was unavailable: say so and that this self-review stands in its place.]

A finding is not a failure — it's the gate working. Fix it (or, if out of scope, flag it; never silently absorb
unrelated changes), re-run the relevant checks, and re-state the outcome.
