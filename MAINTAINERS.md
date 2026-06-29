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

[`.github/CODEOWNERS`](.github/CODEOWNERS) documents who owns which parts and (if "require review from
Code Owners" is ever enabled) routes review on the sensitive paths automatically.
