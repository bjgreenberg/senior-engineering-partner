# GitHub Actions CI/CD Standards

Companion reference for the senior-engineering-partner skill.


CI is the merge gate that makes the PR-flow real (SKILL.md Source Code Management): branch protection requires these checks green before a squash-merge. The the example SaaS `.github/workflows/ci.yml` is the reference — a **multi-gate** pipeline (lint/test → image build → DB+RLS → API integration), each a separate job that must pass. The governing principle: **every claim the code makes about itself is verified by a job, and the workflow holds the minimum privilege to do so.**

## Workflow structure

- **Trigger on `push` to `main` and on `pull_request` to `main`.** PR runs gate the merge; the push run covers the post-merge state of `main`.
- **One job per provable claim, named for what it proves.** The house pipeline:
  - `test` — pytest + `bandit` over the package, the shim, and the API.
  - `docker` — `docker compose config -q` (compose file is valid) + `docker build` (Dockerfile builds, apt packages resolve, every pinned wheel exists).
  - `migrations` — apply `dbmate` migrations to a pgTAP Postgres and run the RLS suite (cross-ref `databases.md`).
  - `api-test` — bring up ephemeral Postgres, apply migrations, drive the real HTTP API to prove the auth→session-GUC→RLS pipeline isolates tenants end to end (cross-ref `python-web-apis.md`).
  - `audit` — `pip-audit` (or `npm audit`/`osv-scanner`) over every pinned manifest, all severities, via the shared `scripts/audit.sh`. Fails on a known-vulnerable dependency the image scan would miss (see the dependency-audit gate below).
- **Jobs are independent and parallel by default.** Use `needs:` only for a true dependency (e.g. deploy `needs:` the test gates). Don't serialize gates that don't depend on each other — it just slows the merge.
- **The local gate and the CI gate must be the same script.** `scripts/db-test.sh` / `scripts/api-test.sh` run identically on a dev Mac (OrbStack) and on `ubuntu-latest` (bundled Docker) — the only dependency is a Docker runtime. A CI-only reproduction of a gate rots; a shared script does not.

## Least privilege (the default posture)

- **Set `permissions:` explicitly at the top — default to read-only.** The repo-wide default `GITHUB_TOKEN` is far broader than a test job needs:
  ```yaml
  permissions:
    contents: read   # the workflow only checks out and tests
  ```
  Grant a *specific* job more only where it genuinely needs it (e.g. `id-token: write` for OIDC, `packages: write` to push an image), scoped at the job level, never repo-wide. This is the CI mirror of SKILL.md's principle of least privilege; a CodeQL finding will (correctly) flag an over-broad token.
- **Never expose `GITHUB_TOKEN` or any secret to untrusted code.** `pull_request_target` and workflows that check out a fork's code run attacker-controlled input — do not give those write permissions or secret access. Prefer `pull_request` (read-only, no secrets) for fork PRs.

## Pin your actions

- **Pin third-party actions by full commit SHA**, not a moving tag — `uses: actions/checkout@<40-char-sha>  # v4.x`. A tag like `@v4` is repointable; a compromised or retagged action then runs with your token (the supply-chain attack class that hit `tj-actions/changed-files`). First-party `actions/*` at a major tag is the *minimum* acceptable bar; SHA-pin everything for a commercial pipeline, and let Dependabot PR the bumps.
- **Pin tool versions in the job, not "latest."** `setup-python` with an explicit `python-version` that **matches the Dockerfile and prod** (the engine pins 3.12 in CI to match the image, even though local dev runs 3.14 — a version skew between CI and prod is a class of "passes CI, breaks in prod" bug). Cache the toolchain (`cache: pip`).

## Secrets in Actions

- **Secrets come from the `secrets` context or an OIDC exchange — never hardcoded, never `echo`'d.** A secret printed to the log (even accidentally, via `set -x` or a debug `echo`) is leaked; Actions masks known secret values but not derived ones. SKILL.md's "never log secrets" applies to CI logs too.
- **For cloud deploys, use OIDC → Workload Identity Federation, not a stored service-account key.** `google-github-actions/auth` with `id-token: write` mints a short-lived token from GitHub's OIDC provider — **no long-lived `*.json` SA key in repo secrets** (cross-ref `gcp.md` IAM: "never long-lived SA keys"). This is the single highest-value CI security upgrade for a GCP-deployed app.

## Security & quality gates to wire in

- **`bandit` as a gating step** (`-ll` HIGH/MEDIUM, `-r` over the source dirs). Document every `--skip` inline with *why* it's accepted (the engine CI skips B310 — all `urlopen`s hit fixed `https://` endpoints — and B108 — `/tmp/jobs` is intentional Cloud Run ephemeral storage). An undocumented skip is a hidden waiver.
- **Lint + type-check as gating steps** (the non-security half of static analysis, SKILL.md *Type Annotations*). A `lint` job runs **`ruff check`** + **`ruff format --check`** (replaces flake8/black/isort); a `typecheck` job runs **`mypy --strict`** (or **`pyright`**) over the package. Both fail the PR. The skill mandates complete annotations — this is the gate that proves they hold; without it the mandate is unverified. For a large untyped legacy module, ratchet (gate touched modules; widen the include list over time) rather than a blanket ignore.
- **CodeQL** (GitHub's SAST) on a schedule + PRs for a commercial app — it catches the over-broad-token, injection, and data-flow issues `bandit` misses. Findings are tracked (e.g. "CodeQL #13"); resolve or explicitly dismiss-with-reason.
- **Dependency review / Dependabot** on the lockfile and `requirements*.txt` (cross-ref `compliance.md` A03:2025 supply chain). Commit a `.github/dependabot.yml` covering *every* ecosystem (`pip`, `npm`, `github-actions`, `docker`), enable Dependabot alerts + security updates + secret-scanning/push-protection, and **keep the alert tab at zero** — every alert is triaged (bump-and-merge, or dismiss-with-reason), never left to pile up.
- **A manifest-level dependency-audit gate (`pip-audit` / `npm audit` / `osv-scanner`), all severities, as a *required* check.** Wrap it in a `scripts/audit.sh` that CI and developers both run (the gate-script-shared-with-local pattern below), auditing **every** manifest — each `requirements*.txt` *and* `pyproject.toml` (`pip-audit .` project mode). This is **not redundant with the image Trivy scan**: an image scanner only sees packages that reach a built image and is usually floored at HIGH/CRITICAL, so it misses (1) MEDIUM/LOW advisories (still real on a hostile-input parser), (2) a manifest that's in no image (a legacy/dev requirements file), and (3) `pyproject`↔`requirements` **drift**. The manifest audit closes all three; keep parallel manifests in lockstep so a bump can't land in one file and rot in another. (Trivy/grype on the *image* and `trivy fs`/`osv-scanner` on the *tree* are complements, not substitutes — state which blind spot each covers.)
- **The image build is a gate, not a deploy** — building in CI proves the Dockerfile and every pinned dependency resolve; it does not push. Pushing/deploying is a separate, privilege-scoped job gated on the test jobs.
- **Emit an SBOM + signed build provenance for the released image** (the output side of supply-chain — SKILL.md *Supply-chain integrity*). On the publish job: generate an **SBOM** (`syft` → SPDX, or `cyclonedx-py`/CycloneDX) and attach it; produce **build provenance** with the first-party **`actions/attest-build-provenance`** and **`actions/attest-sbom`** (keyless Sigstore signing — needs `id-token: write` + `attestations: write`, scoped to that job only). This makes the artifact independently verifiable (`gh attestation verify`) and moves you up the **SLSA** levels; on GKE, Binary Authorization then admits only attested images (`containers-and-orchestration.md`). *Verify the current action versions + predicate types against GitHub's docs.*
- **Assert the image runs the *real* app, not a dev/legacy entrypoint.** A green build proves the image *compiles*, not that it boots the authenticated production app — a stale `CMD`, a dev server, or an unauthenticated legacy entrypoint can ship green. Add a gate that starts the built image and asserts the production entrypoint answers correctly (health is up **and** an authenticated path returns 401 unauthenticated, not 200), and fence dev-only entrypoints so they can't become the prod default (cross-ref `gcp.md` PORT-bind check).
- **Make the security/integration gates *required*, not just present.** A pipeline that runs `migrations` (RLS) and `api-test` (tenant isolation) but only marks `test` as required in branch protection lets a PR merge red on a cross-tenant leak. Every job that can go red on an auth bypass, a failed migration, or a cross-tenant leak is a **required** check — adding a gate to CI isn't done until it's added to the required-checks list (`github-teams.md`).

## Deploy, approval & rollback

- **Promotion to prod is a gated step, not the automatic consequence of a green merge.** Put the deploy job behind a GitHub **Environment** (`production`) with **required reviewers** — a human approves the promotion after CI is green (branch protection for the deploy itself; cross-ref `github-teams.md`, and `iac-terraform.md` for the matching `terraform apply` approval). The deploy authenticates via OIDC→WIF, never a stored key.
- **Make rollback a one-step, pre-planned action.** Cloud Run keeps prior revisions — roll back by routing 100% traffic to the last-known-good revision (instant, no rebuild — `observability-and-incident-response.md` runbook). Wire a **post-deploy smoke check** (health + an authenticated path) and fail/auto-roll-back the deploy if it fails, rather than leaving a broken revision serving traffic.
- **Progressive delivery for risky changes (optional, beyond instant-rollback).** Cloud Run supports **traffic-splitting** — deploy the new revision with `--no-traffic`, then migrate a **canary** percentage (`--to-revisions REV=10`) while watching the SLO/error metrics, and promote to 100% only if it stays healthy (or roll the split back to 0%). Instant-rollback (above) is the floor; a canary is the upgrade for a high-blast-radius change. *Verify the current `gcloud run services update-traffic` flags.*
- **Releases are automated, not hand-tagged.** For a versioned/distributed artifact, a release job runs **release-please** (or semantic-release): it reads the Conventional Commits, computes the semver bump, updates `CHANGELOG.md`, tags, and opens/creates a **GitHub Release** — and the release attaches the SBOM + provenance from the build job. Keeps the tag, the CHANGELOG, and the notes in sync with the commits automatically (SKILL.md SCM).
- **Bound artifact & log retention.** Build artifacts, images, and CI logs accrue cost and are a log-noise + supply-chain surface — set a retention window (short for PR artifacts, longer for released images addressed by digest) instead of keeping everything forever.

## QA & quality gates (meta)

- **A required check must be reliable** — a flaky gate trains the team to "re-run until green," which defeats it. Ephemeral-service gates (`db-test.sh`) wait for readiness (`pg_isready` loop) before asserting and tear down on `trap EXIT`. Fix flakiness; don't `continue-on-error` a real check.
- **Fail fast, fail loud.** `set -euo pipefail` in every gate script; a migration or assertion failure exits non-zero and fails the job. No gate should pass by swallowing an error.
- **Make these checks *required* in branch protection** (SKILL.md: "required CI status checks where CI exists"). A green-optional check is decoration.

## Test cases (what to verify about the pipeline itself)

- **A deliberately-broken PR is rejected:** a failing test, a `bandit` HIGH, a malformed compose file, or a cross-tenant RLS leak must each turn the corresponding job red and block the merge — verify the gate actually gates.
- **The `permissions` block is minimal:** assert (review or a policy check) that no job holds write scopes it doesn't use.
- **Actions are pinned:** a check (or review discipline) that no `uses:` references a floating `@main`/`@master`.

## Deploy stage (when you add it)

- **Gate deploy on the test/migration/api jobs**, run it in its own job with `id-token: write` only, authenticate via OIDC→Workload Identity (cross-ref `gcp.md`), deploy the *image built and scanned in this run* (by digest), and roll forward via Cloud Run revisions (instant rollback to the prior revision). Never deploy an unpinned or unscanned image, and never from a job that also has broad repo write access.
