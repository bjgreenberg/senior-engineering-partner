# Maintainers

This project is maintained by:

- **Brian Greenberg** ([@bjgreenberg](https://github.com/bjgreenberg)) — maintainer · <https://briangreenberg.net>

## How we work

- Every change lands via a pull request with the required checks green (`docs-render`, `leakage-guard`,
  `shellcheck`, `skill-lint`, `script-tests`, `citation-validate`) and a maintainer review — see [CONTRIBUTING.md](CONTRIBUTING.md).
- The branch ruleset requires **1 approving review**. The maintainer (repo admin) can self-merge
  their *own* PRs via an admin bypass, so a solo merge is never blocked — while every *other*
  contributor's PR gets a genuine four-eyes review before it lands.
- Merges are **squash-only**. GitHub signs the squash commit, so contributions land **Verified** on
  `main` even from unsigned feature branches — no commit-signing setup required to contribute.
- Security reports go through **private advisories**, never public issues — see [SECURITY.md](SECURITY.md).

### mermaid-cli re-pin cadence (docs-render gate)

`scripts/render-diagrams.sh` runs mermaid-cli from a digest-pinned container image (`MMDC_IMAGE` — the single pin location; the docs-render workflow calls the script). The digest keeps the gate reproducible; it does not keep it current (SKILL.md *stay current, not just pinned* — a pin is for reproducibility, not a museum). **Re-pin quarterly**, or sooner when a Mermaid syntax feature or rendering fix we need ships:

1. Read the mermaid-cli release notes for rendering changes that could alter committed diagrams.
2. Resolve the new tag's digest: `docker buildx imagetools inspect ghcr.io/mermaid-js/mermaid-cli/mermaid-cli:<tag>`.
3. Update `MMDC_IMAGE` in `scripts/render-diagrams.sh` (tag noted in the comment, digest in the pin).
4. Prove it: run the render check over every diagram-bearing file locally, or let the `docs-render` gate do it on the PR — a digest bump that changes rendering behavior must fail there, not on `main`.

## Cutting a release

Releases are **prepared by [release-please](https://github.com/googleapis/release-please) and
finished by a maintainer.** release-please watches `main`, derives the next version from the
[Conventional Commits](https://www.conventionalcommits.org/), and keeps an open *release PR* that
bumps the `Version` in [`SKILL.md`](SKILL.md) (and `version`/`date-released` in
[`CITATION.cff`](CITATION.cff)) and prepends the new section to
[`CHANGELOG.md`](CHANGELOG.md). It deliberately stops there (`skip-github-release: true`): the
`tag-protection` ruleset requires **signed** tags, and a bot tagging via the API produces an
*unsigned* tag the ruleset would reject — so a maintainer cuts the signed tag and Release by hand.

> **Reviewing the release PR — watch the `extra-files` diff.** release-please scans **every
> line** of an `extra-files` doc (`SKILL.md`, `CITATION.cff`) for its `x-release-please-*`
> marker and bumps the first semver on any line that carries one. So a line that merely
> *quotes* a complete marker as documentation gets its semver rewritten too — the v1.15.0
> release did exactly this, silently changing a "CFF 1.2.0" spec reference to "CFF 1.15.0"
> (corrected by the follow-up fix, which ships as the v1.15.1 patch). The release PR's
> `SKILL.md`/`CITATION.cff` diff should only ever touch
> the intended version stamp; any *other* changed line is this bug — reject and fix the prose
> to name the marker family (`x-release-please`), not the literal complete tokens.

1. **Enrich the changelog.** In the open release PR, edit the new `CHANGELOG.md` section to add the
   curated "what + **why**" narrative (the prose this skill values), then mark the PR ready.
2. **Merge the release PR.** Because release-please authored it with `GITHUB_TOKEN`, the
   `leakage-guard` / `docs-render` / `shellcheck` / `skill-lint` / `script-tests` / `citation-validate` checks don't auto-run on it; review the (generated) diff and
   admin-merge: `gh pr merge --squash --admin`.
3. **Cut the signed tag + GitHub Release** from the merged `main`:
   ```bash
   git switch main && git pull
   VERSION="$(jq -r '."."' .release-please-manifest.json)"   # the version the release PR set
   git tag -s "v$VERSION" -m "v$VERSION"        # signed annotated tag - satisfies tag-protection
   git push origin "v$VERSION"
   gh release create "v$VERSION" --verify-tag --title "v$VERSION" \
     --notes "$(awk "/^## \[$VERSION\]/{f=1;print;next} /^## \[/{f=0} f" CHANGELOG.md)"
   ```
   (Signing on a remote/locked machine: see the project's own commit-signing notes — squash-merge
   web-signs `main`, but the *tag* must be signed locally.)
4. **Flip the release PR's label — or the next release is silently blocked.** release-please tracks
   release state by **PR label, not by the git tag**. With `skip-github-release: true` it never marks
   the merged release PR as released, so every subsequent run **aborts** with *"There are untagged,
   merged release PRs outstanding"* and opens no new release PR until you relabel it. After the tag +
   Release are cut, move the merged release PR from `autorelease: pending` to `autorelease: tagged`:
   ```bash
   gh pr edit <release-pr#> --add-label "autorelease: tagged" --remove-label "autorelease: pending"
   ```
   (Create the `autorelease: tagged` label once if the repo doesn't have it.) Only then does
   release-please treat `vX.Y.Z` as the baseline and start accumulating the next version.
   *(Learned the hard way: the 1.5.0 release PR stayed `autorelease: pending` and silently blocked the
   1.6.0 release PR across six green workflow runs until it was relabeled.)*

### Gotcha (historical here since the title-only flip; live wherever squash includes the PR body): a squash body can make release-please skip the commit entirely

**Since 2026-07-02 this repo squashes with "Default to pull request title" only** (API:
`PR_TITLE` + `BLANK`) — flipped precisely to kill this failure class; the enriched CHANGELOG,
not the commit body, carries each release's narrative. The gotcha below still matters if the
setting is ever reverted, and for any repo squashing with "title and description" (`PR_BODY`):
the whole PR description becomes the *commit message body*, and release-please runs the
*conventional-commits parser over that body*. A body
line that (after GitHub's ~72-column hard-wrap) **begins with a `token(`-shaped fragment** — e.g.
a wrapped code snippet starting a line with `json.load(open(` — is read as a malformed footer and
the parser rejects the WHOLE commit: the run logs `commit could not be parsed … unexpected token '('`
and `Considering: 0 commits`, and the release PR silently never opens or updates. *(Learned the
hard way: the #54/#55 merges were both skipped this way and 1.11.0 had to be forced.)* Two rules:

- **Check the release-please run log after every merge to `main`** — a green run that "considered
  0 commits" is a failure wearing a success conclusion.
- **Recover with a `Release-As` footer**: open a tiny `chore:` PR whose *entire* PR body is a short
  plain-prose line plus a final `Release-As: X.Y.Z` line (no code spans, no long lines). That
  forces the version; then hand-write the skipped merges' entries during the changelog-enrichment
  step (step 1 above), citing their PR numbers.

[`.github/CODEOWNERS`](.github/CODEOWNERS) documents who owns which parts and (if "require review from
Code Owners" is ever enabled) routes review on the sensitive paths automatically.
