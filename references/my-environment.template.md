# My Environment Profile (template)

> **This is the one file you customize when you adopt this skill.** Copy it to
> `references/my-environment.md` (which is `.gitignore`d, so your real details never get
> committed) and fill in the placeholders below. The universal core in `SKILL.md` and every
> other reference is **stack-agnostic**; whenever a discipline needs a concrete value — a host,
> a repo, a service, a deploy target, an example app — it lives **here**, so you re-home the
> whole skill by editing this single file. Delete any section that doesn't apply to you.

## How to use this file

1. `cp references/my-environment.template.md references/my-environment.md`
2. Fill in the sections below with *your* environment.
3. The core already instructs the assistant to **read `my-environment.md` for any
   environment-specific claim** — so the more complete this file is, the more grounded and
   specific the assistant's guidance becomes. Treat it as living documentation: keep it current.

---

## Identity & calibration

- **Who you are / role:** `<e.g. backend engineer, solo founder, platform team lead>`
- **Experience level to calibrate to:** `<e.g. intermediate Python/Bash — adjust explanation depth>`
- **Anything the assistant should always know about how you work:** `<preferences, constraints>`

## Tech stack

List the concrete tools the disciplines bind to. Examples in the references are generic; pin
them to yours here.

- **Identity / SSO / MDM:** `<your SSO / identity provider; your MDM>`
- **Productivity / collaboration:** `<e.g. Google Workspace / Microsoft 365; Slack / Zoom>`
- **CRM / ERP / data:** `<e.g. your CRM, ERP, BI/analytics tools>`
- **Secrets management:** `<e.g. 1Password, Vault, cloud secret manager>` — the default for **every**
  secret (no hardcoded credentials, ever).
- **Version control & CI:** `<e.g. GitHub + GitHub Actions>`
- **Cloud / deploy target:** `<e.g. GCP Cloud Run + Cloud SQL/Postgres + object storage>`
- **Shell:** `<your shell + any hard preference, e.g. "Bash only, never PowerShell" — or "PowerShell" on Windows. The universal core is Bash/POSIX by default; this is where a hard preference lives.>`
- **Primary languages:** `<e.g. Python, Bash, JavaScript>`

## Hosts & machine config (optional)

Delete this section if you work on a single machine with no config-sync tooling.

- **Machines:** `<names/roles; how you verify which one you're on>`
- **Config sync (if any):** `<your config-sync tool, if any>`. If you use a single-writer
  sync tool, record its cardinal rule here (e.g. "edit the source of truth, not the rendered
  target"); the universal "no concurrent multi-writer dev in single-writer sync state" point lives
  in `references/multi-agent-coordination.md`.
- **Logs & runtime state:** `<where they live; never committed to the config repo>`

## House Git / SCM standards

The concrete setup behind `SKILL.md` *Source Code Management*.

- **Commit signing:** `<e.g. SSH-signed via 1Password op-ssh-sign; or GPG; or none>` — and any
  unattended-automation exemption.
- **Push/fetch transport:** `<e.g. per-repo deploy keys at ~/.ssh/deploy_keys/<owner>__<repo>,
  IdentitiesOnly+IdentityAgent=none; or the agent default>`
- **Merge method:** `<e.g. squash, never rebase>` and approvals policy.
- **Branch protection / PR-flow:** `<your default, and any documented single-writer exemptions>`
- **Where house standards are written down:** `<e.g. a team handbook repo>`

## Reference example app the examples bind to (optional)

Many references illustrate Tier-2 (production/commercial) patterns. If you have a real system the
examples should map to, describe it here so the guidance is concrete to *your* architecture.

- **Stack:** `<e.g. Postgres with Row-Level Security as the tenant-isolation boundary, FastAPI on
  Cloud Run, object storage, KMS-encrypted per-tenant keys, append-only audit tables, metered usage,
  Stripe billing>`
- **Environments / projects:** `<e.g. app-dev, app-prod, app-tfstate-prod>`
- **Deliberate exceptions to flag, not "fix":** `<e.g. a bucket that is public by design because a
  BI dashboard hotlinks its assets — verify stated intent before remediating>`
- **Architecture notes worth remembering:** `<auth model, isolation approach, etc.>`

These are **examples**, not universal requirements — the disciplines hold for any stack; the
specifics are yours.
