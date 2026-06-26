# Security Policy

`senior-engineering-partner` is a Claude Code **skill** — Markdown instructions plus a few helper
shell scripts. It ships no running service and holds no secrets, so the security surface is narrow,
but it's real:

- **Helper scripts** under `scripts/` — e.g. an injection or unsafe-handling bug in a shell helper.
- **Skill content that could be abused** — e.g. an instruction-injection vector, or guidance that,
  if followed, would weaken a user's security posture.
- **Reintroduced identifiers** — the skill is deliberately scrubbed of environment-specific detail;
  a regression that puts personal, host, or employer data back into the public tree is a privacy
  issue (`scripts/leakage-guard.sh` guards against it).

## Reporting a vulnerability

**Please don't open a public issue for a security report.**

- **Preferred:** use GitHub's **private vulnerability reporting** — the **Security → "Report a
  vulnerability"** button on this repository. It opens a private advisory only the maintainer can
  see.
- **Alternatively:** contact the maintainer via **<https://briangreenberg.net>**.

Please include what you found, how to reproduce it, and the impact. You'll get an acknowledgement
within a few days, and a fix worked under coordinated disclosure — with credit to you unless you'd
prefer to stay anonymous.

## Supported versions

This is a rolling, single-branch project: fixes land on `main`. Please report against the current
`main`.
