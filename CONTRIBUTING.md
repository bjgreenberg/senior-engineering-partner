# Contributing

Thanks for helping improve **senior-engineering-partner**. This skill is maintained the way it
teaches: contributions follow the same disciplines the skill itself prescribes (see
[`SKILL.md`](SKILL.md) — *Source Code Management*, the engineering workflow, and
`references/multi-agent-coordination.md` / `references/github-teams.md`). Those rules aren't
bureaucracy here; they're the product. This guide distils them for contributors.

It's deliberately scaled for a small project — one maintainer plus the occasional contributor.
None of it is heavy.

**Sending a one-line fix?** Just open the PR. The eval, changelog, and version-bump steps below
only apply when you change a *discipline* or behavior — not for a typo or a small doc tweak.

## Where things go

| You have… | Put it in… |
|---|---|
| A **bug** — something in the skill is wrong, broken, or unclear | an **Issue** (use the bug-report form) |
| A **question, idea, or feedback** | **[Discussions](https://github.com/bjgreenberg/senior-engineering-partner/discussions)** (Q&A / Ideas) |
| A **security** concern or a way the skill could be misused | **privately** — see [`SECURITY.md`](SECURITY.md) (never a public issue) |

Keeping bugs in Issues and everything open-ended in Discussions is what keeps both useful.

## The contribution workflow

This is GitHub Flow with the skill's guardrails. Outside contributors work from a **fork**;
regular collaborators use a branch on the repo. Either way:

1. **One short-lived branch per change** — `feat/…`, `fix/…`, `docs/…`. Never work on `main`;
   `main` is the integration point, not a scratchpad.
2. **Sync before you push:** `git fetch && git rebase origin/main`, so you integrate the latest
   work and resolve any conflict in *your* tree. We keep **linear history**. If a conflict is in
   content you don't own or understand, **stop and ask** in the PR rather than guessing — a wrong
   resolution silently drops someone's change.
3. **Stage by explicit path** (`git add path/to/file`) — never `git add -A` / `git add .`. Your
   commit contains only the files your change touches.
4. **Conventional Commits.** Your **PR title** is a Conventional Commit (`feat:`, `fix:`, `docs:`,
   `chore:`, `test:`, `refactor:`). Because we **squash-merge**, the PR title *becomes the
   permanent history entry* — write it like one.
5. **Update the docs in the same PR.** If you change behavior, update *every* representation of it
   — the README, the relevant `references/*.md`, and any diagram or numbered step-list the change
   touches (a stale diagram is a *wrong* diagram). You do **not** hand-bump the `Version` field or
   write the changelog entry yourself —
   [release-please](https://github.com/googleapis/release-please) does that from your
   Conventional-Commit PR title: it opens a release PR that bumps the `Version` in `SKILL.md`'s
   metadata table and prepends the entry to [`CHANGELOG.md`](CHANGELOG.md), which a maintainer then
   enriches with the curated "what + why" narrative before cutting the signed release (see
   [`MAINTAINERS.md`](MAINTAINERS.md)). So when you change a **discipline**, write a clean
   `feat:`/`fix:` title and describe the *why* in the PR body — that becomes the changelog line.
   This is the skill's own same-commit-docs rule, applied to itself.
6. **Keep the universal core stack-agnostic.** `SKILL.md` and the references must not contain
   host, employer, or personal identifiers — those belong in a contributor's own
   `references/my-environment.md` (which is gitignored and never committed). The **`leakage-guard`**
   check enforces this; don't add anything that trips it. Your own *literal* identifiers go in an
   un-committed `references/leakage-denylist.local` (copy it from the `.template`) — that file guards
   the tree locally without ever being published. When a co-maintainer joins, add their **public**
   handle to CODEOWNERS/attribution (don't denylist it), but add **their** personal hosts / private-repo
   names / email to their own local denylist.
7. **If you encode a discipline, guard it with an eval.** New or changed rules should add or extend
   a scenario in `evals/` — the project's "changelog is the spec, evals are the tests" model.
8. **Run the gates locally** before opening the PR: `bash scripts/leakage-guard.sh`,
   `bash scripts/render-diagrams.sh` (render-check any Mermaid you touched), and — if you touched a
   helper script — `shellcheck scripts/*.sh`. Locally-green is necessary but **not sufficient** —
   the PR's required checks are the source of truth.
9. **Open the PR** with the **What changed / Why it changed / Testing** description (the PR template
   gives you the shape). Open it as a **draft** while it's WIP so CI runs but it can't merge early;
   mark it ready when it is. Link the issue it closes (`Closes #N`).
10. **"Done" means merged via a green PR** — not pushed to a branch.

Keep PRs **small and single-purpose** — one change per PR. A reviewer can hold the whole diff in
their head, and CI catches problems early.

## Authoring a discipline (how to word a rule)

When you add or sharpen a rule in `SKILL.md` or a reference, word it so it can be *checked*, not
just admired. Three tests — the skill's own falsifiability standard (`references/audit-report-format.md`),
applied to itself:

1. **Binary imperative, not a preference.** "Never store a bearer token in `localStorage`" /
   "Every outbound call gets a timeout" — not "prefer secure storage" or "consider adding timeouts."
   Soft words (*prefer, consider, reasonable, where appropriate*) turn a rule into a vibe a reviewer
   can't enforce. If a point genuinely *is* a judgment call, say so plainly rather than dressing it as
   a gate.
2. **Diff-checkable — name the observable.** State the thing a reviewer (or a grep, a test, a CI gate)
   can look at and see pass or fail: the file/line, the pattern, the assertion. A rule you can't point
   at in a diff is aspiration, not standard.
3. **Timeless, not a status report.** Write the durable invariant, not the current state. "Specs state
   intent in the present/invariant voice" — strip *currently, legacy, not-yet, tracked, TODO* framing;
   those describe a moment, and a rule outlives the moment. (Transient state belongs in an issue or the
   CHANGELOG, not a discipline.)

A load-bearing rule also earns an **eval** (workflow step 7) — the executable form of the same
falsifiability: if you can't write a scenario that fails without the rule and passes with it, the rule
may not be checkable enough yet.

## How your PR gets reviewed and merged

- **A maintainer reviews every contributor PR before it merges** — read like a code review, with
  every review thread addressed or resolved. We don't merge on green CI alone: green proves the
  *gates* passed, not that the change is correct, in-scope, and free of a subtle regression a check
  didn't cover.
- The repo's **required checks** (`docs-render`, `leakage-guard`, `shellcheck`) must pass.
- Merges are **squash-only** — rebase-merge (it rewrites your commits *unsigned*) and merge-commit
  are both disabled — and the branch is auto-deleted on merge. GitHub signs the squash commit, so
  your contribution lands **Verified** on `main` even if your own commits weren't signed; you don't
  need to set up signing.

> **A note on the review requirement.** The branch ruleset **requires one approving review**, and the
> maintainer (the repository-admin role) is a **bypass actor** — so the two cases resolve cleanly. A
> **contributor PR** lands the normal way: on a maintainer's approving review. The **maintainer's own
> PR** can't be self-approved (GitHub forbids approving your own PR), so it merges via **admin bypass
> after a documented self-review** — recorded in the PR — stands in for the second reviewer. This is
> **not** a waiver of review: every PR is reviewed; the bypass only covers the mechanical
> can't-approve-your-own-PR case. It mirrors the skill's own rule — *your own hand-written change,
> green checks + a recorded self-review suffice; someone else's change, a human reviews it*
> (`references/github-teams.md` §3).

[`CODEOWNERS`](.github/CODEOWNERS) documents who owns which parts of the skill. Code-owner review is
**not** required in the ruleset today (`require_code_owner_review` is off), so `CODEOWNERS` is advisory
— enabling it would route review automatically on the sensitive paths.

## Code of Conduct

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).

## Licensing

By submitting a contribution, you agree it is licensed under this project's
[Apache-2.0](LICENSE) license (inbound = outbound). That's all — there's no separate CLA or DCO
sign-off to remember.
