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
   touches (a stale diagram is a *wrong* diagram). If you change a **discipline**, also bump the
   **`Version`** field and add the matching **`#### vX.Y` entry** under the `### Changelog` heading
   in `SKILL.md`'s metadata table — that embedded section *is* this skill's changelog (there is no
   separate `CHANGELOG.md`). This is the skill's own same-commit-docs rule, applied to itself.
6. **Keep the universal core stack-agnostic.** `SKILL.md` and the references must not contain
   host, employer, or personal identifiers — those belong in a contributor's own
   `references/my-environment.md` (which is gitignored and never committed). The **`leakage-guard`**
   check enforces this; don't add anything that trips it.
7. **If you encode a discipline, guard it with an eval.** New or changed rules should add or extend
   a scenario in `evals/` — the project's "changelog is the spec, evals are the tests" model.
8. **Run the gates locally** before opening the PR: `bash scripts/leakage-guard.sh` and
   `bash scripts/render-diagrams.sh` (render-check any Mermaid you touched). Locally-green is
   necessary but **not sufficient** — the PR's required checks are the source of truth.
9. **Open the PR** with the **What changed / Why it changed / Testing** description (the PR template
   gives you the shape). Open it as a **draft** while it's WIP so CI runs but it can't merge early;
   mark it ready when it is. Link the issue it closes (`Closes #N`).
10. **"Done" means merged via a green PR** — not pushed to a branch.

Keep PRs **small and single-purpose** — one change per PR. A reviewer can hold the whole diff in
their head, and CI catches problems early.

## How your PR gets reviewed and merged

- **A maintainer reviews every contributor PR before it merges** — read like a code review, with
  every review thread addressed or resolved. We don't merge on green CI alone: green proves the
  *gates* passed, not that the change is correct, in-scope, and free of a subtle regression a check
  didn't cover.
- The repo's **required checks** (`docs-render`, `leakage-guard`) must pass.
- Merges are **squash-only** — rebase-merge (it rewrites your commits *unsigned*) and merge-commit
  are both disabled — and the branch is auto-deleted on merge. GitHub signs the squash commit, so
  your contribution lands **Verified** on `main` even if your own commits weren't signed; you don't
  need to set up signing.

> **A note on the "0 required reviews" setting.** The branch ruleset doesn't *mechanically* require
> an approval. That's a deliberate accommodation so the solo maintainer can merge their own work
> (where a documented self-review stands in for a second reviewer). It is **not** a waiver:
> **contributor PRs are reviewed by a maintainer as a matter of policy** before they land. This
> mirrors the skill's own rule — *your own hand-written change, green checks suffice; someone
> else's change, a human reviews it* (`references/github-teams.md` §3).

[`CODEOWNERS`](.github/CODEOWNERS) documents who owns which parts of the skill; if required reviews
are ever turned on, it routes review automatically on the sensitive paths.

## Code of Conduct

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).

## Licensing

By submitting a contribution, you agree it is licensed under this project's
[Apache-2.0](LICENSE) license (inbound = outbound). That's all — there's no separate CLA or DCO
sign-off to remember.
