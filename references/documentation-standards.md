# Documentation Standards (README, badges, CHANGELOG, CITATION, ADRs)

Companion reference for the senior-engineering-partner skill. The core (SKILL.md →
*DOCUMENTATION*) carries the always-loaded floor: docs ship in the **same commit** as the
change they describe, every representation of changed behavior gets hunted down
(`git grep` the old names), and a doc you *read* to understand a change is one you must
update when you change it. This file is the full mechanics for each artifact type.

## README.md — every project, script directory, or module

- **A `Last updated:` stamp directly under the H1 title** — date + time, 12-hour format,
  America/Chicago (Central): `YYYY-MM-DD HH:MM AM/PM TZ`, e.g.
  `Last updated: 2026-06-21 10:22 PM CDT`. Get it deterministically, **never guess**:
  `TZ='America/Chicago' date '+%Y-%m-%d %I:%M %p %Z'`. **Bump it in the *same commit*
  every time you create or modify the README** — part of the edit, like the CHANGELOG; a
  README touched without a refreshed stamp is a staleness signal.
- **Required sections:** purpose and scope; prerequisites and dependencies (reference
  `requirements.txt` or `pyproject.toml`); setup and installation; usage examples with
  sample commands or inputs/outputs; environment variable / secrets setup (referencing
  the secret manager where applicable); a **Troubleshooting** section — document known
  failure modes and their fixes proactively, before users hit them; known limitations or
  edge cases. For single-file scripts: a Files and Modules section with a table of every
  top-level function and its purpose.
- **A linked Contents section once the README is long** — past roughly 10 KB or 8+
  sections, add a `## Contents` list of section links after the intro, and end **each**
  section with a small back-link (`<sub>[↑ Back to contents](#contents)</sub>`) so
  readers can navigate both ways. **Never hand-compute the anchor slugs** — GitHub's
  slugger has non-obvious rules (`&` becomes `--`, a trailing `…` leaves a trailing `-`,
  backticks and dots vanish) — **validate every internal link mechanically**: the
  canonical `github-slugger` package, or the rendered page's own anchors. A 404 anchor is
  a broken deliverable, like a failing test.

## Status badges — every remote-backed repo, and only true, live badges

A day-one standard like branch protection, not a flourish. (A throwaway Tier-0 repo with
no README is exempt — match the standard to the repo.)

- **Floor row:** a **live CI-status badge** (the workflow's own `badge.svg`, never a
  static "passing" image), the **license**, the **latest release** where versioned; a
  **public** repo adds its security posture (**OpenSSF Scorecard** badge — see
  `compliance.md`).
- **A badge is a *claim*** — **never** a hardcoded `passing`, a coverage badge without
  coverage instrumentation, SLSA/SBOM/provenance without build attestation, `tests`
  without a test suite, or a drifting static version. A false badge is the same
  stale-claim failure as a wrong diagram.
- Prefer **live, dynamic self-reporting** badges (the workflow/Scorecard/Best-Practices
  `badge.svg`, shields.io dynamic release/license endpoints) — honest **by
  construction**, where a **static level claim** drifts; never freeze a level into the
  URL.
- Before committing, **verify the badge's actual *claimed level* against its source of
  truth — not merely that the URL returns HTTP 200** (an `in progress` OpenSSF Best
  Practices badge 200s exactly like a `passing` one).

## CHANGELOG.md

Maintain alongside every project in [Keep a Changelog](https://keepachangelog.com)
format with Conventional Commits-style type labels (`Added`, `Fixed`, `Changed`,
`Removed`), updated in the **same commit** as the code change — never a follow-up.
Date-based sections for scripts without semver; semver sections for packages.

## CITATION.cff — citable public repos

A versioned/released public repo that is plausibly *citable* — research software, a
dataset, a standards/methodology artifact — ships a
[Citation File Format](https://citation-file-format.github.io/) `CITATION.cff`
(CFF 1.2.0), so the host's citation surface (GitHub's "Cite this repository" button, the
Zenodo–GitHub DOI integration) works from a manifest of record. It is a *claim* — the
badge-row honesty rules apply:

- **Validate it as a gate** (`cffconvert --validate` from a digest-pinned container, one
  script run verbatim locally and in CI) — an invalid file silently breaks the cite
  button, a broken deliverable like a failing test.
- **Never hand-maintain `version`/`date-released`** — wire both into the release
  automation (release-please `extra-files` with the inline `x-release-please`
  version/date comment-annotations: YAML comments, so the file stays schema-valid; a
  working example is in this repo's own `CITATION.cff`). A hand-bumped citation version
  is the drifting-static-claim failure again.
- **Never write the *literal, complete* annotation markers next to an unrelated semver
  in an `extra-files` doc** — release-please scans every line for the marker and will
  bump that semver too (this repo's v1.15.0 release did exactly that to a "CFF 1.2.0"
  spec reference; name the marker family, not the literal tokens).
- Tier-aware like badges: a Tier-0/throwaway, or a repo nobody would ever cite, skips it.

## MODULARIZATION.md

For single-file scripts under concrete packaging pressure (a convert-trigger from the
*Single-File vs. Package* framework is near) — target layout, trigger conditions,
migration steps. This becomes the implementation spec when the time comes; absent that
pressure, writing one is speculative design (YAGNI).

## ADRs (Architecture Decision Records)

When a choice has real trade-offs and future-you (or a new contributor/agent) will ask
"why is it this way" — a tech selection, a schema or tenant-isolation approach, a
build-vs-buy — record a short ADR (context → decision → consequences → alternatives
rejected) in a dated, immutable `docs/adr/NNNN-*.md`; supersede with a new ADR, never
edit the old one. Git history shows *what* changed; the ADR captures *why*.

- **An ADR that *deviates* from a standing discipline must name the rule it overrides**
  — cite the *specific* rule and record why the trade-off is acceptable, so the
  exception is an auditable decision a reviewer can find, not silent drift.
- **The security/CIA floor is never ADR-overridable.** An ADR can waive only
  *tier-scaled rigor* (defer a load-test tier, a mutation-test gate, multi-region) —
  never a floor control: no-hardcoded-secrets, input validation at trust boundaries,
  injection prevention, environment isolation, authentication, tenant RLS. "It's
  internal / behind auth / just an MVP" does not move the floor. A proposed ADR that
  tries to waive a floor control is a red flag to push back on, not a decision to
  record.

## Docstrings & inline comments

- **Inline comments** explain the *why*, not the *what*; non-obvious logic must be
  commented.
- **Docstrings:** every Python and JS function and class gets a docstring/JSDoc block —
  purpose, parameters, return values, exceptions raised.

## Diagrams

Owned by `diagrams-and-visual-docs.md` — the taxonomy, the when-NOT-Mermaid decision,
authoring pitfalls, and the same-commit + render-check rules the core carries.
