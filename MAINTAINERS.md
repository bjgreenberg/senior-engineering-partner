# Maintainers

This project is maintained by:

- **Brian Greenberg** ([@bjgreenberg](https://github.com/bjgreenberg)) — maintainer · <https://briangreenberg.net>

## How we work

- Every change lands via a pull request with the required checks green (`docs-render`, `leakage-guard`,
  `shellcheck`) and a maintainer review — see [CONTRIBUTING.md](CONTRIBUTING.md).
- The branch ruleset requires **1 approving review**. The maintainer (repo admin) can self-merge
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
   `leakage-guard` / `docs-render` / `shellcheck` checks don't auto-run on it; review the (generated) diff and
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

[`.github/CODEOWNERS`](.github/CODEOWNERS) documents who owns which parts and (if "require review from
Code Owners" is ever enabled) routes review on the sensitive paths automatically.
