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
- [ ] Docs updated in **this** PR — README / the relevant `references/*.md` / any diagram or step-list the change touches. Do **not** hand-edit the `Version` or `CHANGELOG.md`: [release-please](https://github.com/googleapis/release-please) derives both from the Conventional-Commit PR title (see `MAINTAINERS.md` → *Cutting a release*).
- [ ] `bash scripts/leakage-guard.sh` and `bash scripts/render-diagrams.sh` pass locally (and any Mermaid I touched renders).
- [ ] `python3 scripts/skill-lint.py` and `bash scripts/tests/test-scripts.sh` pass locally (word budget, reference integrity, gate fixtures, the baseline-coverage tripwire).
- [ ] If I touched `.github/workflows/`, `bash scripts/actions-lint.sh` passes locally.
- [ ] No host/employer/personal identifiers added to the universal core (those live in a private `references/my-environment.md`).
- [ ] If I added or changed a discipline, an `evals/` scenario guards it in **this** PR — or the PR body carries an explicit `Eval-waiver: <reason>` line (an auditable deferral, never a silent skip).
- [ ] I self-reviewed the diff (correctness, scope, security).
