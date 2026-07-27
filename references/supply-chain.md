# Supply Chain — alerts, audit gates, SAST/secret scanning, pin+verify, SBOM/provenance

Companion reference for the senior-engineering-partner skill. The core (SKILL.md →
*SECURITY CHECKS & VALIDATION* and *DEPENDENCY MANAGEMENT*) carries the always-loaded
floor — per-language scanners as merge-blocking gates, alert count at zero, every fetched
artifact pinned AND integrity-verified. This file is the full mechanics.

## GitHub security alerts & Dependabot (keep the alert tab at zero)

Every GitHub repo gets supply-chain alerting *turned on and acted on* — advisories are
work items, not a dashboard. (Other hosts: GitLab dependency scanning + secret detection,
else Renovate + gitleaks in CI — alerting on, count zero.)

- **Enable the trio**: Dependabot **alerts**, **security updates**, and **secret
  scanning + push protection**. Commit `.github/dependabot.yml` covering *every*
  ecosystem (`pip`, `npm`, `github-actions`, `docker`, …) so SHA-pinned actions and
  digest-pinned images don't fall behind.
- **Triage every alert; zero open.** Bump the pin (and any drifted manifest), or dismiss
  a false positive/unreachable path *with a written reason*. An ignored alert tab is an
  unowned, growing liability.
- **Review Dependabot's PRs as code** — CI gates them, read the changelog for breaking
  changes, then merge. No blind auto-merge; no rot.
- **Scanners are necessary but NOT sufficient — know each one's blind spots.** An
  image/OS scanner (Trivy/grype) sees only built-image packages, usually floored at
  HIGH/CRITICAL — it misses (1) **MEDIUM/LOW advisories** (still real on a hostile-input
  path, e.g. a PDF/zip parser), (2) a **manifest in no image** (legacy/dev-only
  requirements), (3) **manifest drift** (`pyproject.toml` behind `requirements.txt`).
  Gate the *manifests themselves* (below); never present "image scan green" as "no known
  vulns."

## Dependency-audit gate (manifest-level, all severities) — required where deps are pinned

Gate pinned manifests at *every* severity, in CI **and** the same script locally — a
vulnerable pin fails the PR at the source.

- **Python:** `pip-audit` over **every** manifest — each `requirements*.txt` (`-r`) *and*
  `pyproject.toml` (project mode, `pip-audit .`) so drift can't hide a CVE. Wrap in
  `scripts/audit.sh` (CI calls it); `pip-audit` exits non-zero on findings, so
  `set -euo pipefail` makes it a real gate (`--strict` also fails on
  dependency-collection errors).
- **Other ecosystems — native auditor, same posture:** Node `npm audit`
  (+ `audit signatures`); Rust `cargo audit`; Go `govulncheck`; Ruby `bundler-audit`;
  Swift `osv-scanner` over the committed `Package.resolved` (GitHub Advisory Database
  curates Swift; Dependabot alerts cover it too). **`osv-scanner`** is the polyglot
  fallback (lockfiles across ecosystems, same OSV DB) — right for a mixed-language repo.
- **Manifest blind spot:** `trivy fs --scanners vuln .` (or `osv-scanner`) catches
  vulnerable lockfiles whether or not they reach an image — the complement to image
  scanning.
- **Required status check** once green (with test/build/migration gates), so a vulnerable
  dependency cannot merge.

## Static analysis (SAST) + secret-scanning gates — required where code is hosted

Code-level review the dependency/image/secret-alert scanners do **not** perform —
merge-blocking CI gates **and** the same script locally; also the *deterministic half of
code review*, still working when an AI review bot is flaky, quota-limited, or absent.

- **SAST:** `semgrep` with curated security packs (e.g. `p/security-audit`, the language
  pack, `p/dockerfile`, `p/owasp-top-ten`, `p/github-actions`), **failing on any
  finding**; language-native linters (`bandit`, `gosec`, `eslint-plugin-security`, …)
  stay as their own gates. Keep green only with **documented, audited** exceptions —
  inline `# nosemgrep: <rule>` with justification for a real false positive, or a
  narrowly-scoped exclusion explained in the gate script — **never a blanket disable**.
- **Secret scanning of history AND working tree:** `gitleaks` (or `trufflehog`) over full
  git history + current tree, as a gate. Allowlist **only** synthetic test fixtures (root
  `.gitleaks.toml` scoped to test dirs); real secrets never enter the repo — secret
  manager at runtime; push protection is the second line — this gate catches a committed
  secret that push-protection or Dependabot would miss.
- **Name the complementarity; don't duplicate-and-claim-covered.** SAST finds code bugs,
  gitleaks secrets, `pip-audit`/Trivy vulnerable deps, bandit Python issues — each covers
  the others' blind spots. State which gate covers what.
- **Both become required status checks once green** (get the repo owner's authorization
  where promotion needs it).

## Pin AND checksum-verify EVERY fetched artifact (a pin without a hash is not enough)

A pin says *what* you asked for; a checksum/digest proves you *got exactly that,
untampered* — pinning alone still trusts the network, registry, and mutable tags. Every
fetched artifact (CI tool binary, installer, tarball, base image, GitHub Action,
`curl … | bash` script) is **both** version-pinned **and** hash-verified, by the
strongest mechanism the ecosystem offers:

- **Binaries/tarballs (canonical pattern):** pin version, download over HTTPS, verify the
  published checksum *before* use — `echo "<sha256>  file.tgz" | sha256sum -c -`, gating
  on its exit. **Never `curl … | bash`** an unpinned, unhashed URL; never run a
  downloaded installer unverified.
- **Install the whole distribution — and gate on the tool's output, not its exit code.**
  A dist shipping `share/`/`lib/` beside `bin/` resolves those resources relative to the
  binary; a bare-binary copy silently orphans them while the tool keeps exiting 0. Pair
  the install with the enforcement half: assert the produced artifact contains what the
  tool exists to produce.
- **Containers:** pin by **digest** (`image@sha256:…`), never a mutable tag — the digest
  *is* the integrity check. Prefer a scanner/tool run from a digest-pinned official image
  over an unverified package install.
- **GitHub Actions:** pin third-party actions by **commit SHA**, not a tag
  (`github-actions.md`). Prefer a checksum-verified binary or digest-pinned container
  over a third-party action adding GitHub-API/token surface you don't need.
- **Language packages:** ecosystem hash-locking — `pip install --require-hashes` with a
  `--generate-hashes` lock, `npm ci` against a committed lockfile (+
  `npm audit signatures` for provenance), a committed
  `Cargo.lock`/`poetry.lock`/`uv.lock`/`Package.resolved` (SwiftPM: CI resolves with
  `-onlyUsePackageVersionsFromResolvedFile`, pins by version never branch). A bare
  `pkg==1.2.3` is *version*-pinned, **not** *integrity*-pinned — say so; hash-lock where
  the gate matters.
- **A tool's rule definitions are a dependency too.** Runtime-fetched rules (semgrep
  `--config p/…`) are an *unpinned, unverified* input — note it; strongest posture is
  vendored/pinned rules (`--config ./rules/`) so a registry change can't silently alter
  the gate.

## The output side: SBOM and build provenance

Pin+hash proves *inputs*; **SBOM** + **provenance** prove to a *consumer* what the
*artifact* contains and how it was built (US EO 14028, EU CRA, the CISA attestation
form). For anything you build and ship (image, release, package):

- **Generate an SBOM** — **CycloneDX** (`cyclonedx-py`/`cyclonedx-npm`) or **SPDX**
  (`syft`) — components, versions, licenses; attach to the release/image so downstream
  auditing (and your own `osv-scanner`/Dependabot) reads a manifest of record.
- **Produce and sign build provenance** — keyless **Sigstore/cosign**; in GitHub Actions
  the first-party `actions/attest-build-provenance` (+ `actions/attest-sbom`); on GKE,
  **Binary Authorization** admits only attested images
  (`containers-and-orchestration.md`).
- **Frame maturity as SLSA levels** (`slsa.dev`): provenance generated (L1) → hosted,
  tamper-resistant builder with source/build separation (L2+). Name your level and the
  next; *verify exact action versions/attestation predicates against current docs.* CI
  wiring: `github-actions.md`.

Goal: a **reproducible, tamper-evident** build — re-runs fetch byte-identical inputs, a
compromised mirror or moved tag **fails the gate** instead of silently substituting code,
and the artifact ships with a signed SBOM + provenance a consumer can verify.

## Staying current (freshness lanes)

A pin is for reproducibility, not a museum. An unbumped pin silently rots — drifts toward
end-of-life, misses non-security fixes, compounds into a painful multi-major jump — and
past **end-of-support** there are no security fixes at all, so freshness there is a
*floor* issue. Run a **proactive currency check on a cadence, separate from the security
audit**: `pip list --outdated` · `npm outdated` · `brew outdated` + `mas outdated`
(report-only — never `mas upgrade` in automation, per `package-managers.md`) ·
**Dependabot/Renovate `version`-updates** (not only `security`) for GitHub Actions pins
and base-image digests. Two lanes: a **security** bump is *urgent* (alert-to-zero); a
**freshness** bump is *scheduled, batched, and deliberate* — reviewed as code, run
through the thin contract test so a breaking upgrade fails red (`foss-adoption.md`), and
held behind a **release-age cooldown** (Renovate `minimumReleaseAge`) so a
freshly-published malicious version can't reach you immediately. Bump majors on purpose,
one at a time; never blind-chase `latest`.
