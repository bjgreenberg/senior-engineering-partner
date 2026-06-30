# Audit Report Format (the `AUDIT:` mode deliverable)

A whole-codebase audit (SKILL.md `AUDIT:` mode) produces a **severity-ranked findings
report, not a refactor**. This file is the shape of that report and the rules for getting it
right. The point of a fixed format is comparability (two audits read the same way) and
honesty (every finding carries evidence, every claim was verified).

## The cardinal rules

1. **Report first, change nothing.** Do not deliver fixed code until the user has read the
   findings and chosen what to fix — the deliberate inverse of `REVIEW:`. A repo-wide sweep
   that ships diffs buries the findings and pre-empts the user's prioritization.
2. **Mechanize the checkable; don't grade from the docs.** Run the gates yourself, `git grep`
   the tree, and read the **live** config (CI required-checks, branch-protection/rulesets,
   dependency manifests). A README/ADR/CHANGELOG describes *intended* posture, which drifts
   from reality — verify the real state. Quote the command output you observed.
3. **Every finding is falsifiable.** `file:line` evidence, a concrete impact, and a concrete
   fix. No "consider improving error handling" — name the file, the line, the failure mode,
   and the change. If you couldn't verify it, say so and rank it lower.
4. **Lead with what's already strong.** An audit that only lists problems is not trustworthy —
   it reads as nitpicking and hides whether you understood the system. Name the controls that
   are genuinely good (with the same evidence standard), so the reader can tell a real risk
   from a quibble.
5. **Scope discipline.** Audit code/config/tests. Never read, move, or exfiltrate real
   secrets/PII/evidence — note that a sensitive store is out of scope and move on.

## Severity scale

Rank by **impact × likelihood × exposure**, not by how interesting the finding is.

| Severity | Meaning | Examples |
|---|---|---|
| **CRITICAL** | Exploitable now; data loss / breach / RCE on a reachable path | hardcoded prod secret; auth bypass; cross-tenant read in prod; unsandboxed `eval` of user input |
| **HIGH** | Serious, but gated by a precondition / mitigated by isolation; or a make-or-break control left unverified | a known-CVE pattern on an untrusted path inside a sandbox; the tenant-isolation invariant proven only in a non-prod config; no fuzzing on a hostile-input parser |
| **MEDIUM** | Real weakness, bounded blast radius or needs another factor | missing rate limiting; unbounded resource use; observability/audit-trail gap; an abuse vector behind auth |
| **LOW / DEFERRED** | Minor, or correctly deferred to a later milestone — but *track it with the trigger that re-rates it* | a DSAR/erasure cascade deferred pre-customer; dead-but-latent policy; missing ADR for a real decision |

Two cross-cutting flags worth their own callout: **test/prod parity gaps** (a control the CI
proves under a config that isn't production's — false confidence) and **deferred-but-gating**
items (fine to defer now, becomes a hard blocker the moment a promotion trigger fires — name
the trigger). The sharpest parity gap is a **privilege** mismatch: when the test harness runs
with *more* privilege than production (migrating/seeding as a DB **superuser**), a security
invariant that depends on the privilege difference — e.g. RLS bypass coming from a non-superuser
owner's `BYPASSRLS` attribute, not from superuser status — is silently unverified. The fix is a
**parity gate** that re-runs the suite under the production privilege model, not a prose caveat
(the remediation pattern is in `databases.md`).

## Report structure

```markdown
# AUDIT: <repo> @ <sha>

**Verdict.** 1–3 sentences: overall posture, and whether anything is a live emergency.

## What I mechanically verified (not eyeballed)
<a table of the gates you ran + their result, and the live config you checked
 (required-checks list, ruleset) — this is what separates an audit from a vibe>

## Findings — severity ranked
### CRITICAL / HIGH / MEDIUM / LOW
**<ID> — <one-line title>.** `file:line` — what's wrong + why it's reachable.
**Impact:** … **Fix:** <the concrete change>. (severity rationale if non-obvious)

## Strengths (verified)
<the controls that are genuinely good, same evidence standard — so the report is honest>

## Recommended remediation order
<cheapest-high-value first; group the quick wins; flag what needs its own design/decision>
```

Give each finding a stable **ID** (`H1`, `M3`, `L2`) and reuse it everywhere — the PRs that
fix them, the CHANGELOG, the commit messages — so the trail from audit → fix is traceable.

## After the report

Once the user picks what to fix, **drop into the implementing mode** (`REVIEW:`/`DEBUG:`/
default) and ship each fix the normal way: branch → red-first regression test → minimal fix →
local gates → `/code-review` → PR → required CI → squash-merge, one finding (or one coherent
bucket) per PR, docs/ADR/CHANGELOG in the same commit (SKILL.md *Engineering Workflow* +
*Source Code Management*). Reference the finding ID in the PR so the fix is auditable back to
the report.
