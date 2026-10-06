# CLAUDE.md — senior-engineering-partner

Agent/contributor guide for working **on** this repo (the skill itself lives
in `SKILL.md` + `references/`). Human-facing process docs: `CONTRIBUTING.md`
and `MAINTAINERS.md` — this file is the agent-facing distillation.

## Writer and reviewer (read before editing anything)

**One model writes a change, and a different reader reviews it before the PR.**
Reading, auditing, and *proposing* changes are fine on any model. **Writing** to
`SKILL.md`, `references/`, `scripts/`, `evals/`, or the repo docs is done by one
writer per change; before the PR opens, a second reader — another model, or a
human — reads the diff for unverified paths, flags, and commands; dense prose;
and overreach past the evidence. The PR body records who wrote, who reviewed,
and the reviewer's verdict. Any model may be the writer; this file names none.
A private environment profile (`references/my-environment.md`) MAY name a
writer, a reviewer, and the fallback for when the writer is unavailable; when
it does, sessions in that environment follow it. Skipping the second read, or
departing from a profile's named models, takes an express, per-change
instruction from the maintainer; a general "go ahead" earlier in the session is
not one. Rationale: one writer per change keeps its voice, judgment, and
rule-wording consistent instead of a patchwork of whichever models were loaded,
and a second reader catches what the writer misses.

## Repo shape

- `SKILL.md` — the universal core; `references/` — deep-dive references
  loaded on demand; `scripts/` — lint/guard/test tooling; `evals/` — the
  eval harness (scenarios, fixtures, baselines).
- The repo is **PUBLIC**. Environment-specific values bind through
  `references/my-environment.md`, which is `.gitignore`d and never committed
  — the repo ships only `references/my-environment.template.md`. **Never
  commit private identifiers (employers, hosts, domains, real names beyond
  the author) into code, commits, PR text, or eval baselines** — the CI
  denylist is only a partial guard, not a substitute for care.
- **Cite only this repo.** An issue, PR, or file named in a tracked file is
  one of this repo's own. Never name another repository, product, or an
  issue number from outside the skill; tell an origin incident generically
  (what happened, what it cost, why the existing rules missed it). Commit
  messages and PR bodies are public too, and the leakage guard does not
  scan them — the rule holds there by care alone.

## PR rules

- Branch → PR → all required checks green → **squash-merge only** (the
  ruleset enforces it). PRs require **1 approval and the author cannot
  self-approve** — by default, open the PR and hand off for review.
- Every PR gets a recorded review verdict in its body (a structured review
  of the diff — state what was checked and the conclusion).
- Core edits follow the skill's own disciplines: version/changelog handled
  by release-please from Conventional Commits — never hand-edit generated
  CHANGELOG sections or hand-bump the version/CITATION fields (they are
  release-automation-managed; see the `x-release-please` annotations).

## Gates & sharp edges

- Run `scripts/` checks locally before pushing (skill-lint, script tests,
  the content guard). **The guard scans the STAGED/TRACKED tree** — a
  violation in an unstaged file passes locally and fails after `git add`;
  always gate the staged tree.
- Eval fixtures MUST use the `.fixture` filename suffix (scanner-neutral;
  the suite's startup check enforces it).
- Eval sweeps: deep-reasoning models need long timeouts (`--timeout` well
  above 600s); **never switch branches in a clone while a sweep is running
  from it**.
- Mermaid blocks in any doc you touch get render-checked before commit.

## Release flow (maintainer steps in `MAINTAINERS.md`)

- release-please prepares the release PR; a maintainer cuts the **signed
  tag** locally (release automation cannot sign). After every release,
  check for **spurious release-please PRs** (a pre-tag run can propose a
  version regression — close it, delete its branch, strip the
  `autorelease: pending` label).

## Skill self-improvement

Changes that add or sharpen a discipline follow the consent-gated loop in
`references/skill-self-improvement.md`: propose via PR, never silently edit
the skill, and never *relax* a rule — loosening is human-initiated only.
