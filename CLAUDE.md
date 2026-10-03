# CLAUDE.md — senior-engineering-partner

Agent/contributor guide for working **on** this repo (the skill itself lives
in `SKILL.md` + `references/`). Human-facing process docs: `CONTRIBUTING.md`
and `MAINTAINERS.md` — this file is the agent-facing distillation.

## Model requirement (read before editing anything)

**Authoring in this repo is done by the designated writer model, and a second
model reviews every change.** Today the writer is Fable 5.1 (`claude-fable-5-1`,
alias `fable`) and the reviewer is Opus 5.5 (`claude-opus-5-5`, alias `opus`).
Reading, auditing, and *proposing* changes are fine on any model; **writing** to
`SKILL.md`, `references/`, `scripts/`, `evals/`, or the repo docs is done by the
writer. On any other model, delegate the writing to a writer subagent (Claude
Code's Agent tool with `model: "fable"`), give it the brief, the current text,
and the evidence, and review what comes back. If the writer is unavailable
(usage limits or an outage), the reviewer model writes as a fallback: say
"fallback-written" in the commit and the PR body, and have the writer re-read
the change when it is back. Before the PR, get the reviewer model's read
(unverified paths, flags, and commands; dense prose; overreach past the
evidence) and record the verdict in the PR body. Proceed otherwise only on an
express, per-change instruction from the maintainer; a general "go ahead"
earlier in the session is not one. The writer changes only after a blind
head-to-head on real work; when the names change, update this section.
Rationale: one writer keeps the skill's authored content consistent in voice,
judgment, and rule-wording instead of drifting with whichever model happens to
be loaded, and a second model catches what the writer misses.

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
