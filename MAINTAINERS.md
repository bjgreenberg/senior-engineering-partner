# Maintainers

This project is maintained by:

- **Brian Greenberg** ([@bjgreenberg](https://github.com/bjgreenberg)) — lead maintainer · <https://briangreenberg.net>
- **[@jeffols](https://github.com/jeffols)** — maintainer

## How we work

- Every change lands via a pull request with the required checks green (`docs-render`, `leakage-guard`)
  and a maintainer review — see [CONTRIBUTING.md](CONTRIBUTING.md).
- The branch ruleset requires **1 approving review**. The lead maintainer (repo admin) can self-merge
  their *own* PRs via an admin bypass, so a solo merge is never blocked — while every *other*
  contributor's PR gets a genuine four-eyes review before it lands.
- Merges are **squash-only**. GitHub signs the squash commit, so contributions land **Verified** on
  `main` even from unsigned feature branches — no commit-signing setup required to contribute.
- Security reports go through **private advisories**, never public issues — see [SECURITY.md](SECURITY.md).

## Cutting a release

Releases are **prepared by [release-please](https://github.com/googleapis/release-please) and
finished by a maintainer.** release-please watches `main`, derives the next version from the
[Conventional Commits](https://www.conventionalcommits.org/), and keeps an open *release PR* that
bumps the `Version` in [`SKILL.md`](SKILL.md) and prepends the new section to
[`CHANGELOG.md`](CHANGELOG.md). It deliberately stops there (`skip-github-release: true`): the
`tag-protection` ruleset requires **signed** tags, and a bot tagging via the API produces an
*unsigned* tag the ruleset would reject — so a maintainer cuts the signed tag and Release by hand.

1. **Enrich the changelog.** In the open release PR, edit the new `CHANGELOG.md` section to add the
   curated "what + **why**" narrative (the prose this skill values), then mark the PR ready.
2. **Merge the release PR.** Because release-please authored it with `GITHUB_TOKEN`, the
   `leakage-guard` / `docs-render` checks don't auto-run on it; review the (generated) diff and
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
   On its next run release-please reads the `vX.Y.Z` tag as the release marker and starts
   accumulating the following version. (Signing on a remote/locked machine: see the project's
   own commit-signing notes — squash-merge web-signs `main`, but the *tag* must be signed locally.)

[`.github/CODEOWNERS`](.github/CODEOWNERS) documents who owns which parts and (if "require review from
Code Owners" is ever enabled) routes review on the sensitive paths automatically.
