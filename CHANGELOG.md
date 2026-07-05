# Changelog

All notable changes to the **senior-engineering-partner** skill are recorded here. The format
is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Releases are automated with [release-please](https://github.com/googleapis/release-please): it
reads the [Conventional Commits](https://www.conventionalcommits.org/) on `main`, opens a release
PR that bumps the `Version` in [`SKILL.md`](SKILL.md) and prepends the section below, and a
maintainer enriches that section's narrative before cutting the **signed** tag + GitHub Release
(see [`MAINTAINERS.md`](MAINTAINERS.md) → *Cutting a release*). The earlier entries were curated by
hand; the same "what changed and **why**" narrative is the goal going forward.

This skill was developed and battle-tested in real production work across many internal
revisions before its public release. The history below is the **public** changelog; earlier
internal-version specifics (private project names, hosts, and work history) are intentionally
omitted, and the universal core carries **zero** environment-specific detail — all of that lives
in your own `references/my-environment.md`.

## [1.16.2](https://github.com/bjgreenberg/senior-engineering-partner/compare/v1.16.1...v1.16.2) (2026-07-05)

The Claude-A loop's honest close on the one standing eval residual: the core render-check
mandate gains the reference's genuinely-tool-less fallback (do the static pass, name the
unrun check — never skip silently), and the stale-diagram scenario now grades the silent
skip as a hard fail (a new anti-behavior) with the render item evidence-anchored. Shipped
with a disclosed negative result: six with-skill samples across three content states show
the model never renders or names — a durable enforcement gap now measured precisely, not a
regression. Details in [#83](https://github.com/bjgreenberg/senior-engineering-partner/pull/83).

### Bug Fixes

* **skill:** render-check fallback in the core + an honest hard-fail guard on the silent skip ([#83](https://github.com/bjgreenberg/senior-engineering-partner/issues/83)) ([edb3a46](https://github.com/bjgreenberg/senior-engineering-partner/commit/edb3a46af3c8825cb5f7f3b179a52d77c3e2b17c))

## [1.16.1](https://github.com/bjgreenberg/senior-engineering-partner/compare/v1.16.0...v1.16.1) (2026-07-05)

Closes out the 2026-07-04/05 maintenance session. Beyond the privacy fix below, the release
carries the eval-suite overhaul that shipped as test-scope commits (recorded here by hand,
since Conventional Commits hides `test:` entries from the generated log):

* **Eval harness v2** ([#81](https://github.com/bjgreenberg/senior-engineering-partner/pull/81)):
  scenarios can ship fixture workspaces (`evals/fixtures/`, scanner-neutral `.fixture`
  suffix, two-level drift gates), claude-runner scenario runs get `Bash,Edit,Write`, and the
  judge receives the ordered tool-call trail plus workspace diffs behind hardened block
  boundaries — the three long-standing durable-fail scenarios turned out to be refusal
  artifacts of demanding edits against an empty workspace, not content gaps. Integrated with
  the v1.16.0 cross-CLI runner; with-skill runs read a staged skill copy that excludes
  `evals/` and the private profile files.
* **First harness-v2 baseline** ([#82](https://github.com/bjgreenberg/senior-engineering-partner/pull/82),
  `evals/baselines/2026-07-05-opus/`): bare 11/22/12/0 vs with-skill **29/16/0/0** — 23 of 45
  improved, 0 regressed, and the with-skill fail column is zero for the first time on any
  recorded sweep. All earlier baselines are declared historical (harness discontinuity).
* **Repo policy:** `skill-lint` and `script-tests` are now required status checks (five
  total), with the enumerating docs updated in the same pass
  ([#77](https://github.com/bjgreenberg/senior-engineering-partner/pull/77)).

### Bug Fixes

* **privacy:** scrub environment-specific identifiers from baseline evidence strings ([#79](https://github.com/bjgreenberg/senior-engineering-partner/issues/79)) ([26d523c](https://github.com/bjgreenberg/senior-engineering-partner/commit/26d523c44e19a858b8a7ac7f8cafce42d90c20ed))

## [1.16.0](https://github.com/bjgreenberg/senior-engineering-partner/compare/v1.15.0...v1.16.0) (2026-07-04)


### Features

* per-model portability baselines, cross-CLI eval runner, and the tranche-4 rules-lossless core reduction ([#78](https://github.com/bjgreenberg/senior-engineering-partner/issues/78)) ([bb28ce1](https://github.com/bjgreenberg/senior-engineering-partner/commit/bb28ce118e792fd48c2d5df60262ff2a6d1cc23b))
  * **"Does the skill work equally well across models?" is now a measurement, not an assumption.** Full baseline + with-skill sweeps on **Fable 5 / Sonnet 5 / Haiku 4.5** (opus judge) are recorded as `evals/baselines/2026-07-04-{fable,sonnet,haiku}/`. The headline: with identical skill text, with-skill fails run **16 (Haiku) → 7 (Sonnet) → 4 (Opus, older suite) → 3 (Fable)** — the content transfers down-model but enforcement reliability tracks model tier, and the skill's value *compounds* up-model (Fable: 22 of 45 improved, 0 regressed, the strongest profile on both curves). The shared durable-fail trio (`dependency-manifest-drift` · `stale-diagram-on-behavior-change` · `tdd-regression-red-first`) fails on *every* model — content gaps, not model gaps, and the standing sharpening target.
  * **The scenario runner is pluggable; the judge is not** (`scripts/run-evals.py --runner generic`): the same 45 scenarios can now grade any agent CLI (Codex, Gemini CLI, …) via a `--runner-cmd` template — `{prompt}`/`{model}` substituted **after** shell-style tokenization so a hostile prompt stays one argv token — with the SKILL.md body materialized as the CLI's own instruction file (`AGENTS.md`/`GEMINI.md`) per scenario, and the judge pinned to the `claude` CLI so verdicts stay comparable. No foreign-CLI flags are hardcoded (this repo can't test them); the template is the operator's assertion, verified against their installed `--help`.
  * **Tranche-4 token-mass reduction: the always-loaded core shrank ~18%** (~23.7k → ~19.4k tokens) **with zero enforceable rules dropped** — every section rewritten under a preserve-all-rules contract, approved by three adversarial verifier lenses per item (dropped-mandate / eval-anchoring / integrity, fallback-to-original on refutation), then a whole-file panel confirmed zero cross-section double-cuts. Displaced detail *moved* to `debugging.md`, `logging-and-monitoring.md`, and `github-teams.md` (incl. the 2026-06-10 squash-rule provenance), never silently deleted. Post-edit with-skill re-sweeps on all three models, with every drop single-probe re-run and adjudicated ([`2026-07-04-post-t4/`](evals/baselines/2026-07-04-post-t4/BASELINE.md)): **no drop traces to lost text**; Haiku fails 16→13, Sonnet passes 16→18, Fable within noise of its ceiling. Separately verified: the full body loads un-truncated via the real skill loader (`claude` CLI 2.1.201).
  * **The validation surfaced and fixed an intra-skill tension:** the blanket `MODULARIZATION.md` mandate collided with YAGNI (a model dutifully speccing future channels got judged as speculative design). The spec is now warranted only under **concrete packaging pressure** (a convert-trigger from the Single-File vs. Package framework), and the `yagni-no-speculative-abstraction` scenario's anti-behavior targets *code* artifacts, excusing prose planning notes — verified clean on a live run.
  * **Copilot-review catches folded** (same PR): `--runner-instructions-file` is validated to a bare filename so the skill-body write can't traverse out of the scenario scratch dir (two fixture tests prove the gate can fail); `run_generic()` trims only a trailing newline, keeping foreign-CLI transcripts faithful; results-dir docs name the `-generic` tag.


### Bug Fixes

* stop release-please from corrupting the CFF spec-version reference in SKILL.md ([#75](https://github.com/bjgreenberg/senior-engineering-partner/issues/75)) ([bd5b87c](https://github.com/bjgreenberg/senior-engineering-partner/commit/bd5b87c97ccaa97ad0bee10715d3cbfe98adf3fa))

## [1.15.0](https://github.com/bjgreenberg/senior-engineering-partner/compare/v1.14.0...v1.15.0) (2026-07-04)


### Features

* add CITATION.cff with a validation gate, release-please auto-bump, and the discipline in the skill core ([#73](https://github.com/bjgreenberg/senior-engineering-partner/issues/73)) ([b99b624](https://github.com/bjgreenberg/senior-engineering-partner/commit/b99b624c57301573a06b0ef48f8a73dd2c2c6cf6))

## [1.14.0](https://github.com/bjgreenberg/senior-engineering-partner/compare/v1.13.0...v1.14.0) (2026-07-04)

### Features

* **B2 coverage complete — the three disclosed gaps are closed.** ([#66](https://github.com/bjgreenberg/senior-engineering-partner/pull/66), [#69](https://github.com/bjgreenberg/senior-engineering-partner/pull/69), [#70](https://github.com/bjgreenberg/senior-engineering-partner/pull/70))
  * **RAG + a prompt-injection worked example** ([#66](https://github.com/bjgreenberg/senior-engineering-partner/pull/66)): `llm-apps.md` gains §7 — RAG as rung 1 of the escalation ladder, not an agent pattern (escalate into retrieval only past in-context limits; pin the embedding model — a silent swap invalidates the index; eval the retriever separately from the generator; the index is a derived cache whose **erasure reaches the vector store**). `secure-data-processing.md` gains the **two-zone structural fence** worked example in §2 (zone membership decided by who *controls* the text; planted-delimiter neutralization; an embedded directive is **reported as a finding, never obeyed**; residuals named) and a new §4 — **the vector store is a tenant-data store** (an app-side filter after similarity search is not a boundary; per-tenant namespaces flatten document ACLs; a seeded poisoned-corpus test proves the fence on the *retrieval* path; the embedding call is an egress). The OWASP LLM Top-10 mapping was made honest along the way: LLM08 is mapped *scoped to the slices actually covered* with named residuals, LLM09 (Misinformation) gets a real mapping to §7's grounding controls, and the old "LLM07/LLM09 bite when you fine-tune" claim — which was factually wrong — is corrected.
  * **Bash gets its deep reference** ([#69](https://github.com/bjgreenberg/senior-engineering-partner/pull/69)): `references/bash-scripting.md` — where `set -e` *doesn't* fire (condition contexts; the `local x=$(cmd)` masking), cleanup/atomic-output/locks **with corrected trap semantics** (bash fires `EXIT` on fatal INT/TERM already; a bare `trap cleanup INT TERM` lets a killed script report success — every claim empirically verified on stock bash 3.2.57), `curl -f`, the stock-macOS-3.2 portability floor, and BATS with the source-guard pattern. Load-bearing claims were probe-tested, not asserted.
  * **Frontend testing** ([#70](https://github.com/bjgreenberg/senior-engineering-partner/pull/70)): folded into `testing.md` as §8 (the domain stayed coherent — no new file): query by role/label, **contract-pinned network-boundary mocks** (the §1 consumer-mock rule where it bites hardest), thin critical-path E2E, browser flakiness under the zero-tolerance policy, the two floor behaviors as tests (inert render; preserved input), the axe + manual a11y gate, and snapshot discipline. The pre-merge checklist gains two UI lines.
  * Every slice shipped with its SKILL.md trigger + eval scenario per house doctrine — the suite grows 40 → **44**, and all four new scenarios proof-ran PASS (opus + opus judge).

### Chores

* **Phase-4 smalls** ([#71](https://github.com/bjgreenberg/senior-engineering-partner/pull/71)): a quarterly **mermaid-cli re-pin cadence** in MAINTAINERS.md; **fixture regression tests for the shipped gate scripts** (`scripts/tests/test-scripts.sh` — the guard must FAIL on a planted violation and PASS clean, per testing.md §3c); and a **green-optional `skill-lint`** (`scripts/skill-lint.py` + workflow) validating the Agent-Skills packaging incl. the 1024-char description limit — with a Copilot-review catch folded: block-scalar descriptions can no longer bypass the length check (regression fixture added). Neither new CI job is required — promotion is the maintainer's call.
* `scripts/run-evals.py` is executable ([#65](https://github.com/bjgreenberg/senior-engineering-partner/pull/65)) — the mode-644/exit-126 gotcha is dead.

## [1.13.0](https://github.com/bjgreenberg/senior-engineering-partner/compare/v1.12.0...v1.13.0) (2026-07-03)

The Phase-3 portability pass (audit finding B1): the universal core no longer bakes the
author's environment in as mandates. The assumed-baseline paragraph becomes a
**core-vs-overridable binding table** (Host OS / Shell / VC+CI / secrets manager / deploy
target) that governs any binding a profile doesn't set, and every mandate-position stack
noun — 1Password, Cloud Run, the GitHub framing, and the macOS mechanics that two
*universal* sections still mandated (the least-privilege floor's TCC/FDA vocabulary and the
`~/Library/Logs` log rule) — now reads as the shipped default's worked example, with host
equivalents named. The concrete worked examples stay concrete by design; the environment
profile template gains a Host OS field so every table row has a designated override slot.
Validated against the fresh 2026-07-02 recorded baseline (#62, the post-A1 re-baseline):
with-skill 6 up / 31 flat / 1 variance-cleared down on the 38 shared scenarios, 24 improved
/ 0 regressed vs bare, and **both new portability evals pass** (suite 38 → 40). Shaped by a
4-lens adversarial review + fold re-review, plus five folded Copilot findings.


### Features

* **skill:** de-bias the universal core — shipped defaults become example bindings, not mandates (B1) ([#63](https://github.com/bjgreenberg/senior-engineering-partner/issues/63)) ([b83d8a3](https://github.com/bjgreenberg/senior-engineering-partner/commit/b83d8a367369c08a96f55a733120257c8626739f))

## [1.12.0](https://github.com/bjgreenberg/senior-engineering-partner/compare/v1.11.0...v1.12.0) (2026-07-02)

The A1 token-mass reduction lands its final tranche: every heavy toolchain bullet in the
always-loaded core is now a pure trigger. The last two — **Scalability & system design** and
**Python web APIs** — shed their primer prose to the deep references they point at, taking
SKILL.md from 90,472 to 89,782 bytes with zero content loss: every dropped specific was
verified line-by-line in its reference *before* trimming, a 4-lens adversarial review
(content-loss, docs-honesty, coherence, load-bearing floor) folded back the few phrases that
belong in the always-loaded layer, and both Opus eval sweeps confirmed the same
improvement profile as the pre-trim skill (19 scenarios improved over the bare model, zero
real regressions — every apparent flip causally cleared by re-probe).

### Features

* **skill:** convert the last two heavy toolchain bullets to pure triggers (A1 tranche 3) ([#59](https://github.com/bjgreenberg/senior-engineering-partner/issues/59)) ([9656be0](https://github.com/bjgreenberg/senior-engineering-partner/commit/9656be0820e5dfd0c796eba0aafb8cda3e96de3e)) — Scalability & system design 1,164→858 B and Python web APIs 1,064→664 B, keeping the non-negotiables (tenant id never from the client; don't block the event loop; graceful `SIGTERM` drain; statelessness; queue + DLQ + idempotent consumer; the pool ceiling and its pooler fix) and relocating one implicit specific into `references/python-web-apis.md`, now stated outright: uvicorn stops accepting new connections on `SIGTERM` before draining (verified against uvicorn source). The Copilot review's precision catch is fixed at the source too — a blocking call stalls that *worker's* event loop, which on the documented single-worker Cloud Run deployment is the whole instance.

### Documentation

* README `Last updated` stamp refresh, PQC coverage mentions in the security line + compliance catalog row, and the MAINTAINERS note recording the title-only squash setting ([#58](https://github.com/bjgreenberg/senior-engineering-partner/issues/58)) ([b5fce97](https://github.com/bjgreenberg/senior-engineering-partner/commit/b5fce97))

## [1.11.0](https://github.com/bjgreenberg/senior-engineering-partner/compare/v1.10.0...v1.11.0) (2026-07-02)

The release where the skill learns to build the loops it already runs — and where its own
guard caught its own miss. A new LLM-application reference closes the audit's B2 gap
(looping/evals slice), a privacy fix scrubs a fingerprint the tiered leakage guard should have
caught the first time (and hardens the guard so it will), and the release runbook gains the
parse gotcha that briefly made release-please skip both merges.

*(The two entries below are hand-written: both squash commits were rejected by release-please's
conventional-commits parser — a wrapped code snippet in the PR-description-derived commit body —
so the generator considered 0 commits. See the new MAINTAINERS.md gotcha section, added in
[#56](https://github.com/bjgreenberg/senior-engineering-partner/issues/56).)*

### Features

* **skill:** LLM-app engineering reference — loop patterns, agent loops, evals (B2) ([#55](https://github.com/bjgreenberg/senior-engineering-partner/issues/55)) ([f3b43ef](https://github.com/bjgreenberg/senior-engineering-partner/commit/f3b43efa1f67181c77284109e70ae910edcb6d2a))

  **Why:** the skill ran feedback loops as *process* (tier-aware TDD, the adversarial-review
  re-review loop, the eval runner) but had zero guidance for *building* them into software —
  the audit's B2 gap, owner-requested after a loop-prompting best-practices review. The new
  `references/llm-apps.md` carries the start-simple escalation ladder, the five workflow
  patterns, evaluator-optimizer's fit preconditions (articulable criteria or don't loop), the
  agent loop with deterministic per-iteration verification, the every-loop-gets-a-brake rule
  (done-condition + iteration cap + token/cost budget — an uncapped model loop is the
  billing-DoS twin), and evals-as-the-outer-loop. Source-fidelity-reviewed against Anthropic's
  published guidance with the skill's own mandates kept clearly un-attributed; suite grows
  **37 → 38** (`llm-loop-stopping-criteria`).

### Bug Fixes

* **privacy:** scrub a domain fingerprint from the PQC eval scenario; warn when the Tier-2 guard input is absent ([#54](https://github.com/bjgreenberg/senior-engineering-partner/issues/54)) ([e0bcca9](https://github.com/bjgreenberg/senior-engineering-partner/commit/e0bcca92480ce61c981164f7f6a63be506817fbc))

  **Why:** the v1.10.0 PQC scenario shipped with a phrase on the private Tier-2 leakage
  denylist. Root cause was a silent downgrade, not the wording: `leakage-guard.sh` skipped
  Tier 2 without a sound when `references/leakage-denylist.local` was absent — and a git
  worktree never has the gitignored file, so the pre-PR run false-greened as a full pass. The
  scenario is re-domained and the guard now warns loudly whenever it runs Tier-1-only.

### Miscellaneous Chores

* **release:** document the squash-body parse gotcha; mark release 1.11.0 ([#56](https://github.com/bjgreenberg/senior-engineering-partner/issues/56)) ([d6183fc](https://github.com/bjgreenberg/senior-engineering-partner/commit/d6183fc07f50216af23fd624b692fe4743e21bfd))

## [1.10.0](https://github.com/bjgreenberg/senior-engineering-partner/compare/v1.9.0...v1.10.0) (2026-07-02)

The release where the A1 diet finally pays in bytes — and the skill learns to talk about the
quantum clock. The five heaviest toolchain bullets become pure triggers, and a new
crypto-agility + post-quantum discipline closes the one crypto topic the skill had zero
coverage of.

### Features

* **skill:** convert the five heavy toolchain bullets to pure triggers (A1 tranche 2) ([#51](https://github.com/bjgreenberg/senior-engineering-partner/issues/51)) ([166a805](https://github.com/bjgreenberg/senior-engineering-partner/commit/166a8052165ec9a3f59de9006877bea8222dd44c))

  **Why:** the always-loaded SKILL.md duplicated primer prose its references already carry,
  defeating progressive disclosure (audit finding A1). Google Apps Script, Observability &
  incident response, Diagrams & visual documentation, TypeScript & Node, and Security &
  compliance frameworks now state their load-bearing non-negotiables tersely and point at their
  references: **90,954 → 89,222 bytes (net −1,732)** — the first tranche with a real byte payoff
  (tranche 1 was +386, the pattern and the floor). Every dropped specific was verified
  line-by-line to already exist in its reference across three independent passes (zero misses);
  a 4-lens adversarial review + fold re-review restored ~540 B the compression had weakened
  (the Well-Architected sustainability carve-out, the GAS daily trigger-runtime budget's
  silent-stop failure, the RUM-client-monitor-as-PII-scrubbed-subprocessor constraint, concrete
  fast-burn/slow-burn alert routing). Eval-validated against the recorded 2026-07-01 baseline:
  with-skill **23 pass / 10 partial / 3 fail / 0 error** vs bare 7/17/12 — **19 improved,
  0 regressed**, every down causally cleared as harness artifact or judge variance. Also
  corrects the compliance bullet's under-inclusive SOC 2 claim (CC7/CC8 → CC6–CC8) — the
  inverse of tranche 1's Brewfile finding.

* **skill:** crypto-agility + post-quantum readiness discipline ([#53](https://github.com/bjgreenberg/senior-engineering-partner/issues/53)) ([ee24ad4](https://github.com/bjgreenberg/senior-engineering-partner/commit/ee24ad47dcee6440edd192a37f60422441612f78))

  **Why:** owner request ("we need to be secure") meeting a verified gap — `git grep` found zero
  post-quantum content anywhere in the tree. `compliance.md`'s A04 block now names the anchors
  (FIPS 203 ML-KEM / 204 ML-DSA / 205 SLH-DSA; NIST IR 8547's 112-bit-classical-deprecated-~2030
  / all-classical-disallowed-~2035 trajectory; CNSA 2.0) and **harvest-now-decrypt-later** as
  the threat with a clock on it — recorded traffic is broken via its *captured key exchange*,
  not the symmetric ciphertext. Triage-by-surface: AES-256 at rest is already PQ-adequate;
  signatures aren't HNDL-exposed *unless re-verified after the transition* (retained evidence at
  trial, git tags at clone time → timestamp/countersign). Strategy: **crypto-agility delegated
  to managed platforms** (hybrid X25519+ML-KEM; a default `*.run.app` endpoint gets it today, an
  LB-fronted service needs the SSL-policy opt-in until the announced Oct-2026 default flip) —
  hand-rolled PQC stays a finding. `data-protection.md` §4 ties HNDL to long-retention classes'
  retention/DPIA decisions. Adversarially fact-checked against NIST/Federal Register, NSA, Google
  Cloud, and Cloudflare sources — including an empirical `X25519MLKEM768` negotiation check —
  and hardened by the Copilot reviewer's ambiguity catch on the HNDL wording. Eval suite grows
  **36 → 37** (`crypto-agility-pqc-hndl`).

## [1.9.0](https://github.com/bjgreenberg/senior-engineering-partner/compare/v1.8.0...v1.9.0) (2026-07-02)

The release where the eval suite stops being documentation and starts being a gate — and
immediately earns its keep. **`scripts/run-evals.py` executes the regression scenarios against a
live model** (headless `claude -p` runs, an LLM judge grading `expected_behavior`/`anti_behavior`,
deterministic verdicts), in two modes: bare model vs. skill-injected. The first recorded baseline
(`evals/baselines/2026-07-01-opus/`) measured the skill improving 16 of 31 scenarios over the bare
model with zero regressions — and exposed one stuck failure the skill's prose never fixed:
`stale-diagram-on-behavior-change`.

Both findings drive the second feature. **Phase 2, tranche 1 of the core restructuring** converts
the first DEVELOPMENT DISCIPLINE cluster (Docker/Kubernetes, GCP, Databases, Package managers,
IDEs) to **pure triggers** — terse non-negotiables plus the read pointer — with every dropped
specific verified line-by-line to already exist in its reference. A four-lens adversarial review
hardened the result: it restored three load-bearing rules the trim would have lost (Kubernetes
runtime secrets via ESO/CSI — never a base64 `Secret`; resource requests+limits; no signing
certs/keys/profiles committed), and surfaced that the old Brewfile bullet had contradicted
`package-managers.md`'s `--no-mas` rule since v1.0.0 — that claim is deleted as a correction, not
relocated. And the stuck failure gets its fix: the behavior-change docs discipline is now
**procedural** — a request to "update the code" *includes* the docs that depict that code's
behavior (not scope creep; the *don't-widen-scope* rule cross-points here), and the hunt is
deterministic (`git grep` the old behavior's names; append-only records get a new entry or a
superseding ADR, never a rewrite). Re-running both sweep modes against the recorded baseline
validated the tranche: 16 improved / 0 regressed vs. bare — the identical profile as v1.8.0 —
and `stale-diagram-on-behavior-change` improved fail→partial. The honest ledger: the file is
+386 bytes (the strengthening and restored non-negotiables outweigh the five shortest bullets'
trims); the byte payoff of the restructuring comes from the heavy bullets in the next tranches.


### Features

* **evals:** add a runner that executes the regression suite ([#47](https://github.com/bjgreenberg/senior-engineering-partner/issues/47)) ([7cc6e4b](https://github.com/bjgreenberg/senior-engineering-partner/commit/7cc6e4b5b380137fc9794b94de41aec918d7aef9))
* **skill:** convert the infra toolchain cluster to pure triggers; make the behavior-change doc sweep procedural ([#49](https://github.com/bjgreenberg/senior-engineering-partner/issues/49)) ([f640611](https://github.com/bjgreenberg/senior-engineering-partner/commit/f640611bdd9886e4a81ada1ab991932dbff47998))

## [1.8.0](https://github.com/bjgreenberg/senior-engineering-partner/compare/v1.7.1...v1.8.0) (2026-07-01)

Closes the freshness blind spot in the dependency discipline. The skill already demanded
pinning, locking, and an alert-to-zero *security* audit — but said nothing about a pin that
simply rots: drifting toward end-of-life, silently missing bug and performance fixes, and
compounding into a painful multi-major jump. **A pin is for reproducibility, not a museum.**
The new SKILL.md bullet adds a proactive **currency check on a cadence** (`pip list --outdated`,
`npm outdated`, `brew outdated` + `mas outdated`, and Dependabot/Renovate *version*-updates —
not only *security*-updates) as its own lane: scheduled, batched, reviewed as code, run through
the thin contract test so a breaking upgrade fails red, and held behind a release-age cooldown
so a freshly published malicious version can't reach you the day it drops. End-of-life is
treated as a **floor** issue (an EOL runtime stops getting security fixes at all), distinct
from the urgent security lane, which stays alert-to-zero. `references/package-managers.md`
gains the Homebrew/mas currency detail, and
`evals/scenarios/dependency-currency-not-just-pinned.json` guards the lesson.

### Features

* **skill:** add a dependency-currency discipline (stay current, not just pinned) ([#41](https://github.com/bjgreenberg/senior-engineering-partner/issues/41)) ([ef4d196](https://github.com/bjgreenberg/senior-engineering-partner/commit/ef4d196a236fe7dc4e200e90e6e3ddf6ae1e7af5))

## [1.7.1](https://github.com/bjgreenberg/senior-engineering-partner/compare/v1.7.0...v1.7.1) (2026-07-01)

External-review follow-ups. An AI-assisted public review flagged the skill; three points held up
under verification and are folded in here. The headline is a real — if cosmetic — bug: the
frontmatter wasn't strict-valid YAML, so GitHub rendered a parse error (Claude Code's lenient loader
always parsed it, so discovery never broke). Plus two reusability refactors.

### Bug Fixes

* **Frontmatter is now strict-valid YAML** ([#37](https://github.com/bjgreenberg/senior-engineering-partner/issues/37), [93757ab](https://github.com/bjgreenberg/senior-engineering-partner/commit/93757ab5dddc49ec35299133e9bc4b0c0ce50341)). The unquoted `description` contained `: ` (colon-space) from the mode triggers (`REVIEW:`, `MVP:`, `DEBUG:`), which strict YAML reads as a nested mapping — Ruby Psych failed. Quoting the value fixes it for every parser; the reviewer's "multi-line" diagnosis was wrong, but the defect was real.

### Changed

* **The hard shell preference moved to the profile** ([#39](https://github.com/bjgreenberg/senior-engineering-partner/issues/39)). "Bash only / never PowerShell" was an absolute baked into the universal core — a forker on Windows would inherit it. The core now reads "a POSIX shell (Bash is the shipped default; your profile sets the shell)"; the hard preference lives in `references/my-environment.md`. No behavior change for anyone whose profile already sets it.
* **Deduplicated the always-loaded core against its references** ([#40](https://github.com/bjgreenberg/senior-engineering-partner/issues/40)). The diagram taxonomy and the single-file-testing detail were inlined in `SKILL.md` *and* fully present in their references; the core now keeps the always-on rules + pointer and defers the detail — the skill's own no-duplication rule applied to itself. The security section stays inlined (its content isn't duplicated).

## [1.7.0](https://github.com/bjgreenberg/senior-engineering-partner/compare/v1.6.0...v1.7.0) (2026-07-01)

A dogfooding release: the repo adopts the supply-chain + documentation disciplines the skill
teaches, then folds the lessons back in as new rules. It now runs **OpenSSF Scorecard** on
*itself* — the skill already told you to check a *dependency's* Scorecard; now it checks its own,
scoring **7/10** after a least-privilege fix — carries an honest, live badge row, and gained a
**required-badges** standard in `SKILL.md`. Every badge is true and live; no hardcoded "passing" shipped.

### Features

* **A live badge row is now required on every remote-backed repo — and only honest badges** ([#36](https://github.com/bjgreenberg/senior-engineering-partner/issues/36), [9fc2fcb](https://github.com/bjgreenberg/senior-engineering-partner/commit/9fc2fcb3f1580d141e77ce85afa1b2b93aab228b); discipline [#33](https://github.com/bjgreenberg/senior-engineering-partner/issues/33); repo's own row [#29](https://github.com/bjgreenberg/senior-engineering-partner/issues/29)). Every repo with a remote gets a badge row from day one — the same "standard, not a flourish" posture as branch protection: a **live** CI-status `badge.svg`, license, latest release, and (public repos) an OpenSSF Scorecard posture badge. The honesty rule rides with it — a badge is a *claim*, so never a hardcoded `passing`, a coverage badge with no coverage, an SLSA/SBOM badge with no provenance, or a drifting version; a false badge is the same stale-claim failure as a wrong diagram. Every badge URL is verified live before it ships.
* **OpenSSF Scorecard, run on our own repo — not just our dependencies** ([#30](https://github.com/bjgreenberg/senior-engineering-partner/issues/30), [9edc4e0](https://github.com/bjgreenberg/senior-engineering-partner/commit/9edc4e0969c32052a70de10db5ee27c9cb7b46b2); docs [#33](https://github.com/bjgreenberg/senior-engineering-partner/issues/33)). `foss-adoption.md` used Scorecard to vet an *inbound* dependency; `compliance.md` now documents it as **bidirectional** — the same tool run on your own repo is a supply-chain posture self-assessment, published as a public score the badge reads. Captures the gotchas learned firsthand: keep the workflow minimal (`checkout` + `scorecard-action`), SHA-pin the actions, and skip the optional SARIF upload whose codeql-action pin scorecard's publish verification rejects as an "imposter commit."

### Bug Fixes

* **Least-privilege release-please permissions** ([#34](https://github.com/bjgreenberg/senior-engineering-partner/issues/34), [836d0f4](https://github.com/bjgreenberg/senior-engineering-partner/commit/836d0f4a5014b5dcb09d220412018f520ee40b75)). Moved `contents`/`pull-requests` write from the workflow top level to the job — the skill's own `github-actions.md` rule, and a self-inconsistency it fixes. Lifted Scorecard's Token-Permissions check from **0 to 10** (7/10 overall).
* **Minimal Scorecard workflow — fix the broken publish** ([#32](https://github.com/bjgreenberg/senior-engineering-partner/issues/32), [933473e](https://github.com/bjgreenberg/senior-engineering-partner/commit/933473ee8fd256799231e393320fc2a8e4460a72)). The first run analyzed fine but failed to publish; dropping the optional SARIF→code-scanning step (the "imposter commit" above) fixed it and shrank the third-party action surface.

## [1.6.0](https://github.com/bjgreenberg/senior-engineering-partner/compare/v1.5.0...v1.6.0) (2026-07-01)

A comparative-analysis release. After a deep read of an external multi-agent coding-standards
system, this pulls in the disciplines that genuinely sharpen a **prose, advisory** skill — and
deliberately leaves out what doesn't fit one: a machine-readable standards *format* that is inert
without an orchestrator to enforce it, and a full product-lifecycle. Five load-bearing additions,
each guarded by an eval; an independent baseline-vs-with-skill run confirmed two close a real gap a
strong model misses (the CSV-injection framing and the ADR-floor line) while the rest hold as
regression guards. (Plus a documentation-accuracy sweep — the review-model note, the
architecture-diagram counts, and the reference catalog — in #23–#25.)

### Features

* **Reuse-first, rule-of-three, and YAGNI, named in the modular-code discipline** ([#18](https://github.com/bjgreenberg/senior-engineering-partner/issues/18), [54bdfb3](https://github.com/bjgreenberg/senior-engineering-partner/commit/54bdfb3943680ad2b330ef958c0783ebe3fa42ad)). The section had a "don't reinvent" nudge but never named the three bedrock rules a senior reviewer applies at code-time: reuse before writing new, abstract only at the second-or-third concrete caller (not the first), and no speculative generality — no parameters/hooks/extension points for features nobody has asked for. Unused flexibility is dead code; this is *don't widen scope silently* applied to design.
* **ADRs name the discipline they waive; the floor is never ADR-overridable** ([#21](https://github.com/bjgreenberg/senior-engineering-partner/issues/21), [6525714](https://github.com/bjgreenberg/senior-engineering-partner/commit/65257146de8f2dd5854594fcaa1ff7388aed3306)). An ADR that deviates from a standing discipline must cite the *specific* rule it overrides — an exception becomes auditable, not silent drift — and the security/CIA floor (secrets, input validation, injection prevention, isolation, authn, tenant RLS) can never be waived by one; only tier-scaled rigor can. "Internal / behind auth / just an MVP" does not move the floor. Also adds the human-review hard-block (an unresolved `CHANGES_REQUESTED` outranks green CI and a bot `APPROVE`) and a CONTRIBUTING "authoring a discipline" convention (binary / diff-checkable / timeless — the skill's falsifiability standard applied to rule-writing).
* **New `standards-authoring.md` reference — distill sprawling conventions into checkable rules** ([#22](https://github.com/bjgreenberg/senior-engineering-partner/issues/22), [5eff0a5](https://github.com/bjgreenberg/senior-engineering-partner/commit/5eff0a590c70cb16dd49cb9a48316065bf64dc5e)). The inverse of the rest of the skill: instead of *applying* standards, a guided procedure to turn a project's scattered conventions (a 2,000-line `CLAUDE.md`, `.cursorrules`, `*_guidelines.md`) into an enforceable set — discover sources (prose *and* ground-truth artifacts), filter (timeless / enforceable / dedup), take per-rule human approval (write nothing unapproved), classify floor-vs-overridable. Prose-first and format-agnostic: a machine-checkable JSON+validator set only where CI will actually enforce it.


### Bug Fixes

* **Spreadsheet/CSV formula injection on export, and SSRF as a first-class API7** ([#19](https://github.com/bjgreenberg/senior-engineering-partner/issues/19), [8f887b0](https://github.com/bjgreenberg/senior-engineering-partner/commit/8f887b0adc9b1a85b7b9f9cccd5be83f97df4dfb)). Two output/boundary gaps the skill left implicit outside the Apps Script context. CSV formula injection (CWE-1236) is a *distinct output sink* from HTML escaping — a cell beginning `=`/`+`/`-`/`@` executes as a formula in Excel/Sheets/LibreOffice — now covered in `frontend-web-security.md` §3 as the export context of encode-per-context. And a general user-supplied-URL SSRF (allowlist the destination, block link-local/metadata + private ranges, re-validate after redirects) now has its own row in the OWASP API Top-10 map as **API7:2023**.
* **Fail closed — never return a swallowed error as a success-shaped empty/default** ([#20](https://github.com/bjgreenberg/senior-engineering-partner/issues/20), [fbb9b70](https://github.com/bjgreenberg/senior-engineering-partner/commit/fbb9b70d7de7f0a5562d4d0e5e3eda86209b7953)). `resilience-engineering.md` already had "fail clear, never silent" and safe-labeled fallbacks; the subtle gap was the *success-shaped* failure — an `except: return []` / `return None` that makes a *failed* call read as a legitimately-empty one, so bad data flows on unnoticed. Sharpens the existing rule (rather than adding a redundant one) to fail closed by default, degrading only through a deliberate, labeled fallback — reconciling "degrade, don't die" with "fail closed."

## [1.5.0](https://github.com/bjgreenberg/senior-engineering-partner/compare/v1.4.0...v1.5.0) (2026-06-30)

Dogfooding again: two PRs' worth of lessons from a real build session where a **fully green test
suite still shipped a broken integration**, plus an escalation of the verification step itself.

### Features

* **Consumer-side contract testing — and "test the decision, not the component it renders"** ([#16](https://github.com/bjgreenberg/senior-engineering-partner/issues/16), [aeee0e5](https://github.com/bjgreenberg/senior-engineering-partner/commit/aeee0e506f9e5eb662104cb66325239ed969e01f)). A new-user flow shipped broken past a green suite: the UI was coded and mocked against an *assumed* response (`200`-with-empty) while the server correctly returned `403` — a false green no unit test caught. `references/testing.md` now requires a consumer's mock to encode the producer's **real** responses (status codes *and* error bodies), or a thin integration test across the seam — contract drift cuts both ways. And it calls out the sibling miss: a "thin" route/handler still owns the branch *decision* (which state to show, how to classify an error), so that logic must be extracted and tested — "the components are tested" is not "the orchestration is tested."
* **The runnable setup is documentation too** ([#16](https://github.com/bjgreenberg/senior-engineering-partner/issues/16), [aeee0e5](https://github.com/bjgreenberg/senior-engineering-partner/commit/aeee0e506f9e5eb662104cb66325239ed969e01f)). A required config var that never reached the dev compose crashed `docker compose up` at boot, long after the test suite was green. The documentation discipline (SKILL.md) now treats **every launch surface** — compose files, env templates, deploy manifests, the README quickstart — as documentation that must move in lockstep when a new required var is added, and treats the quickstart as a *verifiable* artifact you actually run before claiming it works.
* **Adversarial multi-lens verification for high-stakes diffs** ([#15](https://github.com/bjgreenberg/senior-engineering-partner/issues/15), [bf9f7db](https://github.com/bjgreenberg/senior-engineering-partner/commit/bf9f7db9cabbb92a995282d25a27a7e7edea866a)). The "verify before done" step now escalates a Tier-2 / security- or isolation-sensitive change to several independent, refute-first lenses — then re-reviews whatever folding the findings introduced. That loop is what catches a *green-but-insufficient* change (passes every gate, reads as correct, yet misses its scoped goal) that a single confirmatory read sails past. A multi-lens panel on a trivial diff is review-theater — match the breadth to the stakes.

## [1.4.0] - 2026-06-29 — Dogfooding: file-sync repo corruption, scheduled-job catch-up, infra-doc discipline

Three generalizable lessons that surfaced running the skill against a real multi-machine fleet migration:
- **`dev-environment-isolation.md` (new §2 subsection) + ENVIRONMENT ISOLATION floor — never host a live `.git` in a file-sync tree.** A file-syncer (iCloud "Desktop & Documents", Dropbox, OneDrive) replicating a live repo *corrupts* it — concurrent `.git` writes, half-synced pack/ref/lock files, online-only eviction of `.git` objects, conflict copies — a **distinct** failure from "sync ≠ backup" (which is about a sync propagating a bad change). Fix: repos in a non-synced path, synced via git push/pull; if a sync tree must contain one, relocate it out and leave a symlink (verify the sync tool's symlink behavior with a scratch test first).
- **`resilience-engineering.md` (new §5) — scheduled work must catch up after downtime.** Wall-clock schedulers (`cron`, launchd `StartCalendarInterval`, systemd calendar timers) silently **skip** runs missed while the host was off/asleep, not defer them. Pair the wall-clock trigger with an elapsed-time catch-up trigger + an **idempotent due-gate**, and compute "is a run outstanding?" the same way in the gate and in whatever heartbeat monitors the job (a no-op catch-up run must write nothing, so it can't reset the monitor's signal).
- **SKILL.md DOCUMENTATION — "every representation" now names infra/environment/layout docs.** A doc you *read* to understand a change is one you must update — including the environment/host profiles and directory-layout indexes that describe *how things are wired*, not just code-level docs.

## [1.3.1] - 2026-06-29 — Fix-at-source discipline + a portability correction

Small follow-on, itself an instance of the discipline it adds — issues caught while shipping v1.3.0, fixed at the source instead of deferred:
- **"Fix it at the source the moment you trip over it" (`engineering-workflow.md` §5).** Names the default that pairs with the existing defer-register: when work surfaces a *different* small fixable problem (a latent bug, a stale comment, a guard false-positive), fix it **now at its root** while the context is loaded, rather than papering over it locally or filing it for a "later" that compounds — the proactive twin of `debugging.md`'s fix-the-cause-not-the-symptom. Guardrails: keep it in its own commit; in a shared tree, flag a problem belonging to *another's* in-flight work to its owner rather than absorbing it (`multi-agent-coordination.md`). Deferral (with a tracked trigger) is the exception, for what genuinely can't be fixed in-flight.
- **Portability correction (`debugging.md`).** The v1.3.0 non-ASCII-byte tell suggested `grep -nP` unqualified; `-P` is GNU/ripgrep-only (not stock macOS/BSD grep), so it's now labelled as such with `cat -v`/`hexdump -C` as the portable primaries — honoring the skill's own "don't suggest a flag that may not exist" rule.

## [1.3.0] - 2026-06-29 — Dogfooding: test/prod privilege-parity + gate-construction lessons

Additions from building an **RLS production-parity gate** for the multi-tenant codebase — lessons that only surface when you write a security gate end-to-end, including a blind spot in the skill's *own* RLS-testing guidance:
- **Test/prod privilege parity (`databases.md`, the headline).** The skill mandated pgTAP RLS testing but its documented pattern *seeds/migrates as the superuser* — which silently can't verify the production invariant, because a superuser bypasses RLS unconditionally while production (Cloud SQL/RDS, no true superuser) relies on a **non-superuser owner's `BYPASSRLS`** attribute. Generalized: *a test harness running with more privilege than production cannot verify a security invariant that depends on the privilege difference.* Fix = a **production-parity gate** that re-runs the suite under the prod privilege model (non-superuser `BYPASSRLS` owner), with the `CREATE EXTENSION`-needs-superuser pre-create gotcha called out. Cross-referenced from `testing.md` §2 and the `audit-report-format.md` test/prod-parity flag (now with the privilege sub-case + remediation).
- **Gate-construction principles (`testing.md` §3c).** Three rules that generalize "red-first" from a single test to a whole gate: **(1)** a gate must be able to *fail* — build a fail-first negative and invert the assertion so a passing negative fails the gate (a green that can't go red proves nothing); **(2)** a gate must **assert** its preconditions (role attributes, object ownership, versions), not just print them, or a refactor passes it for the wrong reason; **(3)** trust the tool's own *verdict* signal, not a bare non-zero exit, so an infra failure can't masquerade as the proof you wanted.
- **`docker compose run` recreates a `depends_on` service — CI-only (`containers-and-orchestration.md`).** An ephemeral gate that bootstraps a dependency out of band (`up -d db` → seed → `compose run migrator`) can have that dependency **recreated** by `compose run` on the CI runner (not on local Docker Desktop/OrbStack — a works-on-my-machine trap), wiping the bootstrap. Use **`--no-deps`** when you own the dependency's lifecycle.
- **Suspect the bytes when a symbol is unimpeachable (`debugging.md`).** A bash `unbound variable` on a variable you clearly set can be a non-ASCII character (smart quote, em-dash, ellipsis) adjacent to `$var` whose leading UTF-8 byte folds into the name; keep shell scripts ASCII, and `cat -v`/`hexdump` reveals it.
- **New eval** `evals/scenarios/rls-superuser-parity-gate.json` encoding the headline lesson so it can't silently regress.

## [1.2.0] - 2026-06-29 — Dogfooding: `AUDIT:` mode + lessons from a real codebase audit

Additions from applying the skill to a full senior audit of a real multi-tenant codebase — gaps the prior evaluation didn't surface because they only appear when the skill drives an actual end-to-end audit-and-remediate workstream:
- **New `AUDIT:` mode** — a sixth trigger for a **report-first, whole-codebase audit**. `REVIEW:` mandates "a senior engineer who spots a fix delivers it," which actively fights a repo-wide audit where the deliverable is a severity-ranked report and the user picks what to fix; conflating the two buried findings in unrequested diffs. `AUDIT:` is report-only, mechanize-the-checkable, `file:line`-evidenced, strengths-included, then drop into `REVIEW:`/`DEBUG:` to implement. Added to the `description` triggers.
- **New `references/audit-report-format.md`** — the finding schema, the CRITICAL/HIGH/MEDIUM/LOW severity taxonomy (with the *test/prod-parity* and *deferred-but-gating* cross-cutting flags), and the report structure, so audits are comparable and every finding is falsifiable. Closes the "no findings-report template / severity taxonomy" gap.
- **Push-only CI steps can red-fail `main` invisibly** (`github-actions.md`) — a step gated `if: github.event_name == 'push'` (attestation, deploy, release-cut) is never exercised by a PR run, so a structurally-broken one (e.g. build-provenance attestation on a user-owned **private** repo) keeps every PR green and red-fails every merge. Make such steps non-blocking / condition-gated, and verify them once via `workflow_dispatch`.
- **Prefer `git grep` for tree sweeps** (EPISTEMIC DISCIPLINE) — an unquoted `grep -r --include=*.py` is glob-expanded by zsh and silently matches nothing (a false "verified absent"); quote the pattern or use `git grep`.

## [1.1.0] - 2026-06-28 — Evaluation follow-ups

Fixes from a full skill self-evaluation. Privacy & authoring correctness first:
- **Two-tier `leakage-guard`.** Generic class-patterns (a CGNAT/Tailscale IP range, Obsidian-style
  wiki-links) stay in the public `scripts/leakage-guard.sh` and run in CI; your *literal* identifiers now live in
  an un-committed `references/leakage-denylist.local` (from a new `.template`), so the public repo no
  longer has to publish hostnames/employer/repo names in order to block them.
- **Frontmatter `description` trimmed to ≤1024 chars** (was ~1.6k, over Anthropic's hard limit) — kept
  the role, languages, `Use when`, and the mode triggers; moved the framework enumeration to the body.
- **Fixed the `render-diagrams.sh` digest comment** (it claimed to ship no digest while pinning one; the
  pinned digest is published — the comment was wrong, not the pin).
- Noted that eval `source` version tokens (`v2.x–v6.x`) are pre-release provenance, not public versions.

Content additions (from the evaluation's scope/security-framework findings):
- **New `references/google-apps-script.md`** — `clasp`+git, minimal `oauthScopes`, `PropertiesService` secrets/limits, `LockService`, trigger quotas + the 6-min wall, pure-logic isolation for testing (+ a guarding eval). GAS is a headline language that lacked a reference.
- **New `references/javascript-and-typescript.md`** — TS strict mode (the `mypy --strict` analog), runtime-validated typed boundaries (the Pydantic analog), Node `SIGTERM`/no-floating-promises patterns. Closes the TS-typing gap.
- **Named the framework mappings** the skill already implements: **OWASP LLM Top 10 (2025)** in `secure-data-processing.md` and **OWASP API Security Top 10 (2023)** (API1 BOLA ≠ web A01) in `threat-modeling-and-api-design.md`.
- **Profile-before-you-optimize** discipline (`debugging.md`); **legacy-refactor + tech-debt register** (`engineering-workflow.md`); **systems-theory naming** — feedback loops, Senge archetypes, iceberg/Cynefin, Conway's Law, Safety-II — across the relevant references.
- **Compliance one-liners**: PCI-DSS scope posture (`compliance.md`), NIST AI RMF / ISO 42001 pointers, and an explicit i18n non-goal (`ui-design-and-accessibility.md`).
- **Repo/community:** README "What it governs" coverage section, a `MAINTAINERS.md`, and CODEOWNERS updated for a second maintainer (two-tier leakage model + admin-bypass review flow documented).

## [1.0.0] - 2026-06-25 — Initial public release

- First public, sanitized release: a **stack-agnostic universal core** (`SKILL.md`, always
  loaded) + a **swappable environment profile** (`references/my-environment.md`, copied from the
  shipped template) + a library of read-on-demand `references/`. Re-home the skill by editing one
  file.
- Ships `scripts/` (dependency-audit, Mermaid render-check, self-review checklist), an `evals/`
  regression suite (each scenario encodes a checkable engineering lesson), and CI that
  render-checks diagrams and guards against environment-specific leakage.

## Pre-release evolution (sanitized summary)

The skill grew from a focused reviewer / pair-programmer / mentor into a full engineering-discipline
system. The arc, with all specifics removed:

- **Foundations** — the mode triggers (`REVIEW:`/`EXPLAIN:`/`MVP:`/`DEBUG:` + default pair
  programmer); a secrets-manager security floor (no hardcoded secrets); PEP 8 + type hints;
  pytest/Jest/BATS; `bandit`/ShellCheck; pinned dependencies; modular code; README + CHANGELOG
  standards; Conventional Commits.
- **Typing & architecture** — a `TypedDict` mandate (no `dict[str, Any]` black holes), the
  single-file-vs-package decision framework, and a testing pattern for single-file scripts.
- **macOS & ops hardening** — LaunchAgent `.app`-bundle / TCC standards (least-privilege Full Disk
  Access, the compiled-launcher requirement), Bash command-injection prevention, structured-logging
  location/rotation, and unattended-job monitoring with a dead-man's-switch.
- **Epistemic discipline** — verify-before-asserting (anti-hallucination) and deterministic-first
  (mechanize anything checkable rather than reasoning it out token-by-token).
- **Process layer** — the spec → plan → tier-aware iron-law TDD → verify-before-done self-review
  workflow, plus the `DEBUG:` root-cause method (reproduce → hypothesize → isolate → fix cause →
  red-first regression test).
- **Phase-aware rigor ladder** — Prototype → MVP → Production, with a security/CIA floor (and a
  backup/continuity floor) that holds at every tier; only verification depth scales.
- **Toolchain depth** — Docker/Kubernetes, GCP/Cloud Run, databases (Postgres/Supabase RLS,
  BigQuery, SQLite), FastAPI, GitHub Actions, and compliance mappings (NIST CSF 2.0 + SSDF, OWASP,
  SOC 2, Well-Architected).
- **Supply-chain & security gates** — SAST + secret-scanning + manifest-level dependency-audit +
  type-check gates as merge blockers; pin **and** hash-lock fetched inputs; emit an SBOM + SLSA
  build provenance on outputs.
- **Reliability & continuity** — disaster recovery (3-2-1-1-0 immutable backups, scheduled restore
  drills), business continuity (BIA-justified RTO/RPO, provider-outage and bus-factor planning),
  resilience engineering (timeouts, circuit breaker, bulkhead, load-shed, designed degraded modes),
  and scalability/system design (statelessness, queues + DLQ, the transactional outbox).
- **Privacy, threat modeling & API design** — GDPR/CCPA-as-code (DSAR, erasure cascade, retention),
  in-PR STRIDE threat models, and attack-surface-shrinking API design.
- **UI & docs** — responsive, light/dark, **WCAG 2.2 AA** accessibility; diagrams-as-code
  (Mermaid-first, render-checked before commit) kept in lockstep with the code they depict.
- **Self-tests** — an `evals/` suite that encodes each hard-won lesson as a checkable scenario, so a
  discipline can't silently regress.
- **Portability** — restructured into a universal core + a swappable environment profile; this
  public release completes that separation so the core is fully reusable by anyone.
