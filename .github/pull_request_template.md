<!--
Conventional-Commit PR title (it becomes the squash-merge history entry), e.g.
  feat: add a circuit-breaker pattern to resilience-engineering.md
  fix: correct the squash-merge wording in the SCM section
  docs: clarify the my-environment.md fork step
-->

## What changed


## Why it changed


## Testing
<!-- How you verified it: gates run, render-checks, what you read/tested. -->


---
<!-- Contributor checklist — see CONTRIBUTING.md. Tick what applies. -->
- [ ] Branch is rebased on the latest `main`; PR title is a Conventional Commit.
- [ ] Small and single-purpose (one change per PR).
- [ ] Docs updated in **this** PR — README / the relevant `references/*.md` / any diagram or step-list the change touches; and if a discipline changed, the `SKILL.md` changelog entry + `Version` bump (this repo's changelog lives in `SKILL.md`, not a separate `CHANGELOG.md`).
- [ ] `bash scripts/leakage-guard.sh` and `bash scripts/render-diagrams.sh` pass locally (and any Mermaid I touched renders).
- [ ] No host/employer/personal identifiers added to the universal core (those live in a private `references/my-environment.md`).
- [ ] If I added or changed a discipline, an `evals/` scenario guards it.
- [ ] I self-reviewed the diff (correctness, scope, security).
