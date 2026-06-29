# GitHub Team Workflows (solo + agents -> human team)

Companion reference for the senior-engineering-partner skill.


Adopt **team-grade repo hygiene NOW**, while the team is still one human plus AI agents. The thesis: discipline that makes agent work safe today (PRs, required checks, CODEOWNERS, reviewed merges) is exactly what makes onboarding a human a no-op tomorrow — flip one toggle from "1 approval optional" to "1+ approvals required" and nothing else changes. The example multi-tenant SaaS is the proving ground. This file is the **mechanism layer** under two policies stated elsewhere: SKILL.md *Source Code Management* (PR-flow default, squash-merge, signing) and `multi-agent-coordination.md` (one worktree/branch per agent, integrate via PR+CI). It does not duplicate them — it configures the platform that enforces them.

Two modes, one config. Where a rule differs, it is tagged **[SOLO+AGENTS]** (current reality) or **[TEAM]** (the moment a human writer joins). The branch/CODEOWNERS/permissions skeleton is identical in both; only the approval count and self-merge rule change.

---

## 1. Branch protection — protect the *security* gates, not just `test`

**Require a PR to `main`. No direct push, no force-push, no branch deletion, linear history, enforced for admins — from day one, on every remote-backed repo** (SKILL.md: the documented single-writer exemptions — a config-sync tool, bot-auto-commit, local-only data — are the only opt-outs, and each is stated in its README).

**The make-or-break detail: the required status checks must be the SECURITY + integration gates, not only the unit-test job.** A common trap — only the `test` job is marked required, so a PR could go red on `migrations` (RLS) or `api-test` (tenant isolation) and still be mergeable. A green-optional security check is decoration. Require **every** gate that proves a tenant-isolation or auth claim:

| CI job (`github-actions.md`) | Proves | Required? |
|---|---|---|
| `test` | pytest + `bandit` over package/shim/API | **required** |
| `docker` | compose valid + image builds, deps resolve | **required** |
| `migrations` | dbmate applies + **pgTAP RLS suite** passes | **required (the trap)** |
| `api-test` | HTTP auth→session-GUC→RLS isolates tenants end-to-end | **required (the trap)** |

Rule of thumb: **if a job can go red on a cross-tenant leak, an auth bypass, a failed migration, or a file-parser regression, it is a required check.** Adding a new gate to CI is not done until it is also added to the required-checks list.

Other protections to set:
- **Block force-push and branch deletion** on `main`; **linear history** (pairs with squash-merge — SKILL.md).
- **Enforce for admins / include administrators.** A protection an admin can click past is advisory. [SOLO+AGENTS] this also stops *you* from a tired late-night direct push.
- **Required conversation resolution** — every review thread resolved before merge (forces an answer to each agent/human comment, not a silent override).
- **Require branches up to date before merge** *only if* CI is fast; on a slow pipeline it serializes merges. Prefer this on sensitive repos, skip it where merge throughput matters — `git pull --rebase` before push (`multi-agent-coordination.md`) covers most of the need.
- **Do NOT yet require signed commits** in protection — see §6.

### Rulesets vs. classic branch protection (verification gotcha)

GitHub now has two systems: **classic branch protection** and the newer **repository rulesets**. They coexist and a branch can be governed by either or both. **When you audit "is `main` protected?", a ruleset does NOT show up in the classic branch-protection API** (`GET /repos/{o}/{r}/branches/main/protection` can 404 "Branch not protected" while a ruleset is fully enforcing it). Check both surfaces:

```bash
# classic protection (may 404 even when a ruleset protects the branch)
gh api repos/OWNER/REPO/branches/main/protection 2>/dev/null

# rulesets — the surface the classic call misses
gh api repos/OWNER/REPO/rulesets
gh api repos/OWNER/REPO/rules/branches/main   # effective rules on the branch
```

An audit that only queries classic protection will report a properly-protected repo as unprotected (false positive) — and, worse, can report a repo protected *only* by a ruleset you forgot to configure as unprotected when it truly is. **Verify against current `gh`/REST docs** for exact ruleset field names before scripting changes; the durable principle is *check both systems, trust the effective-rules view.* Pick one system per org and apply it consistently — mixing them per-repo makes the fleet un-auditable.

---

## 2. CODEOWNERS — document ownership now, route review later

**Add `.github/CODEOWNERS` even as a solo author.** It is not just team routing — it documents who owns what, and (when paired with branch protection's "require review from Code Owners") it **auto-requests review on the paths that can break tenant isolation**, so a PR touching `db/migrations/` cannot be merged without the owner of that path having been on the hook.

```
# .github/CODEOWNERS — sensitive paths require the owner's review
# Default owner for everything
*                       @your-username

# Tenant-isolation & security-critical — never merge without owner review
/db/migrations/         @your-username
/auth/                  @your-username
/scripts/db-test.sh     @your-username
/scripts/api-test.sh    @your-username
/.github/workflows/     @your-username
/infra/                 @your-username   # Terraform — cross-ref iac-terraform.md
```

- **Sensitive paths = require CODEOWNER review** in branch protection: `auth/`, `db/migrations/` + RLS policies, IaC/Terraform, CI workflows, anything touching `tenant_api_keys`/KMS or the evidence/audit tables. These are the paths where a bad diff is a breach, not a bug (`secure-data-processing.md`).
- [SOLO+AGENTS] CODEOWNERS still earns its place: it makes "who must look at this" explicit to *you* and to a reviewing agent, and it's already correct the day a human joins.
- [TEAM] it routes review automatically — the right person is requested without anyone remembering to add them.
- **A path in CODEOWNERS must resolve to a real user/team with repo access**, or GitHub silently skips the owner (the rule looks enforced but isn't). Verify owners exist after editing.

---

## 3. Review model — a human reviews every agent PR; never blind self-merge

This is the rule that makes "an agent is a developer" (`multi-agent-coordination.md`) actually safe.

**[SOLO+AGENTS] — current reality.** Agents author the work; **a human reviews every agent-authored PR before merge — read the diff like a junior developer's, then merge.** Specifically:
- **Do NOT blind self-merge an agent's PR.** "An agent opened it, CI is green, click merge" is exactly the failure mode branch protection exists to prevent. Green CI proves the gates passed; it does not prove the change is *correct, in-scope, and free of a subtle RLS or injection regression a test didn't cover.* A human reads it.
- **Read the automated review too, before merging.** If the repo has GitHub's Copilot PR reviewer (or any bot reviewer) enabled, its comments are part of the review surface — fetch and triage them (`gh api …/pulls/<n>/comments` + `…/reviews`) the same way as a human's, addressing or dismissing-with-reason each finding. An unread Copilot review is a known-flagged bug merged anyway; in practice it catches real factual errors and latent bugs the gates don't. See SKILL.md *Source Code Management* for the canonical rule.
- Agents follow the isolation rules: one `git worktree`/branch per agent, one task per branch, stage by explicit path (never `git add -A` in a shared tree), `git pull --rebase` before push (`multi-agent-coordination.md`).
- Self-merge of your *own* hand-written change, once required checks are green, remains the SKILL.md solo default (approvals at 0). The line is: **agent-authored ⇒ a human reviews; human-authored ⇒ green checks suffice.**

**[TEAM] — when a human writer joins.** Tighten to true four-eyes:
- **≥1 human approval required; ≥2 for sensitive paths** (auth, migrations/RLS, IaC, KMS/key handling).
- **No self-approval** — the author cannot approve their own PR (GitHub enforces this when approvals are required).
- **Required CODEOWNER review** on the sensitive paths from §2.
- **Dismiss stale approvals on new commits** — an approval is for the diff that was reviewed, not whatever lands after.

The transition is one settings change: bump required approvals 0→1 (1→2 on sensitive paths), enable "require Code Owner review." Every other mechanism is already in place — that's the whole point of doing this now.

---

## 4. PR discipline — small, single-purpose, well-described

The platform enforces the gate; discipline keeps the gate cheap to pass.

- **Small, single-purpose PRs.** One change per PR — a reviewer (human or agent) can hold the whole diff in their head, and CI catches problems early. A sprawling branch that diverges for hours is a merge-conflict and review-fatigue generator (`multi-agent-coordination.md`).
- **Draft PRs for WIP.** Open as draft while building so CI runs and the work is visible, but it can't be merged prematurely; mark ready only when it is.
- **The What changed / Why it changed / Testing instructions description, every time** (SKILL.md). A PR template (`.github/pull_request_template.md`) makes this the default and gives a reviewing agent full context without reading the diff cold.
- **Conventional Commits** for titles/commits (`feat:`, `fix:`, `chore:`…) — the squash-merge commit subject is the PR title, so the title *is* the permanent history entry.
- **Squash-merge + delete branch** — `gh pr merge --squash --delete-branch`, never `--rebase` (SKILL.md: rebase merges strip signatures / are refused on signature-required branches).
- **Link the issue** (`Closes #N`) so merge closes it and history is traceable.
- **Required conversation resolution** (§1) — no merge with an open review thread.

---

## 5. Teams & least-privilege access (the SOC 2 CC6 surface)

[TEAM] the moment a human joins, model access through **GitHub Teams + least-privilege repo roles** — and design it now so adding a person is "add to team," not "grant on N repos."

- **Devs get `write`, not `admin`.** `write` lets them push branches and open PRs; branch protection still forces them through review. `admin` lets them edit protection rules and delete the repo — reserve it for the owner. `maintain` is the middle role (manage issues/PRs, no protection-rule edits) for trusted leads. **Never `admin` as the default dev role** — it lets a writer disable the very gates this file sets up.
- **Grant via teams, not per-user.** A `@org/engineers` team with `write` on the repo set; membership is the access-review unit. Per-user grants rot and become the thing a SOC 2 access review flags.
- **Protected environments for prod deploys.** Gate deploys behind a GitHub **Environment** (e.g. `production`) with **required reviewers** and (optionally) a wait timer — a human approves the deploy after CI is green, separate from PR review. The deploy job authenticates via OIDC→Workload Identity, never a stored SA key (cross-ref `github-actions.md` deploy stage, `gcp.md` IAM, `iac-terraform.md` for what it deploys).
- **Access reviews on onboarding/offboarding.** Adding/removing a person is a team-membership change *plus* a check of their lingering grants (org role, PATs, deploy-key access). This is the auditable evidence for SOC 2 **CC6** (logical access) — cross-ref `compliance.md`. Off-boarding that leaves a PAT or a personal fork with push access is the classic finding.
- **Outside collaborators get the narrowest role on the narrowest repo set**, time-boxed, reviewed.

[SOLO+AGENTS] you are the only human, so this is latent — but structure the org now (a team exists, the repo grants are *to the team*) so the first hire is one membership add.

**Conway's Law — the team structure you set up here becomes the architecture.** A system's structure tends to mirror the communication structure of the org that builds it (Conway, 1968): split ownership along the wrong boundaries and the modules calcify along them too. So apply the **inverse-Conway nudge** — shape teams/CODEOWNERS boundaries around the architecture you *want* (one owner per cohesive capability), not the org chart you inherited. *Read [Conway's Law](https://martinfowler.com/bliki/ConwaysLaw.html).*

---

## 6. Repo hygiene — templates, labels, tags, signed commits

- **Issue & PR templates** (`.github/ISSUE_TEMPLATE/`, `.github/pull_request_template.md`) make the structured description and bug-report fields the default. Cheap, and immediately useful to a reviewing agent.
- **A small, consistent label set** (`bug`, `security`, `rls`, `parser`, `infra`, `breaking`) — drives triage and lets you filter the things that demand a CODEOWNER's eyes.
- **Protect tags/releases.** Use a **tag protection rule / ruleset** so release tags (`v*`) can't be force-moved or deleted — a moved release tag silently changes what a pinned deploy resolves to. (Verify the exact ruleset target syntax against current docs before scripting.)
- **Required signed commits — defer until every writer can sign.** SKILL.md's SSH-signing standard (a signer like 1Password `op-ssh-sign` with an ed25519 signing key) means *your* interactive commits are Verified, and squash-merge commits are web-flow-signed by GitHub → Verified. But **do NOT enable branch-protection "require signed commits" until every writer in that repo has signing configured** — turning it on early hard-blocks a writer (or an unattended bot that commits with `commit.gpgsign=false` per SKILL.md) from merging at all. Sequence: get all writers signing → verify recent commits show Verified → *then* require it. [TEAM] make "signing configured" part of onboarding (your team handbook's git-workflow doc is the setup) so this requirement can be switched on fleet-wide.

---

## Quick reference — the two modes

| Control | [SOLO+AGENTS] (now) | [TEAM] (human joins) |
|---|---|---|
| PR required to `main` | yes | yes |
| Required checks | all security+integration gates (not just `test`) | same |
| Force-push / delete / admin-enforced | blocked / blocked / yes | same |
| Required approvals | 0 (but **human reviews every agent PR**) | **≥1**, sensitive paths **≥2** |
| Self-merge | own hand-written change OK; **never blind-merge an agent PR** | no self-approval |
| CODEOWNER review | defined; required on sensitive paths | required on sensitive paths |
| Repo role for devs | n/a (solo) | `write` via team, never `admin` |
| Prod deploy | protected env, you approve | protected env, required reviewer |
| Require signed commits | not yet (defer) | once all writers sign |

The migration from left column to right is intentionally a settings change, not a re-architecture. Build the left column correctly and the team-ready state is already there.
