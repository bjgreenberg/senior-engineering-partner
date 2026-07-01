# Package Manager Standards (Homebrew, npm, mas)

Companion reference for the senior-engineering-partner skill.


The cross-cutting rule for every package manager here: **a committed, pinned manifest is the source of truth, and an `install` from that manifest must reproduce the same state on every machine.** Reproducibility is the discipline; supply-chain awareness (typosquatting, malicious `postinstall`, untrusted taps) is the security gate. An unpinned dependency or an untrusted source is a finding, not a default.

If you sync packages across multiple machines, decide a **convergence model** deliberately and write it down: does the sync ever *remove* packages, or only add them? An install-only sync needs an explicit removal path (a tombstone list, not a blind `brew bundle cleanup`, which would fight the other machine and thrash). And keep **`mas` (App Store) entries out of a synced Brewfile** (`--no-mas`) — App Store apps are per-Apple-ID and permanently divergent. Record your concrete model in `references/my-environment.md`.

This extends, never replaces, the SKILL.md **DEPENDENCY MANAGEMENT** rule (no `*`/`latest`, commit lockfiles, flag known-vuln deps) and the **SECURITY CHECKS** rule (`npm audit` resolves/documents HIGH). Read those first; the specifics below are the package-manager layer on top. If your manifests are synced across machines, follow SKILL.md's **Machine-synced config** discipline — edit the source of truth and push it; never hand-edit the live target.

---

## Homebrew

### A Brewfile is the source of truth — `brew bundle`, not ad-hoc `brew install`

A Mac configured by a trail of one-off `brew install` commands is not reproducible — a second machine drifts the moment you forget one. Capture the machine in a `Brewfile`, commit it, and treat it like code.

- **The `brew bundle` lifecycle:**
  ```bash
  brew bundle dump --file=~/Brewfile --force   # snapshot current machine into the manifest
  brew bundle install --file=~/Brewfile        # install everything the manifest names
  brew bundle check --file=~/Brewfile          # assert the machine matches the manifest (QA gate)
  ```
  `--force` on `dump` overwrites an existing Brewfile. `brew bundle cleanup --file=~/Brewfile` exists and *would* uninstall anything not in the manifest — but **in this fleet you almost never run it** (see the next bullet); without `--force`, `cleanup` only *lists* what it would remove and exits non-zero.
- **Be careful with `brew bundle cleanup` in a multi-machine setup.** If you sync the Brewfile across machines with an *install-only* model (each machine accumulates the union of everyone's packages), a blind `cleanup` rips out packages another machine legitimately needs, and the next sync reinstalls them — thrashing. Removing a package fleet-wide needs an explicit, synced **tombstone** mechanism, not `cleanup`; record yours in `references/my-environment.md`.
- **If the Brewfile is synced, edit the source and push it.** Per SKILL.md's Machine-synced config rule, an apply is not delivery — another machine never converges until the source is committed and pushed.

### Formula vs. cask vs. tap vs. mas — entry types

| Entry | Installs | Example | Notes |
|---|---|---|---|
| `brew` | CLI formula (built/bottled) | `brew "gh"`, `brew "shellcheck"` | command-line tools, libraries |
| `cask` | GUI `.app` / pkg | `cask "visual-studio-code"`, `cask "google-cloud-sdk"` | installs into `/Applications` |
| `tap` | third-party formula source | `tap "hashicorp/tap"` | **runs arbitrary code — vet it (below)** |
| `mas` | Mac App Store app | `mas "Xcode", id: 497799835` | valid Brewfile syntax, but **excluded from this fleet's synced Brewfile** (see mas section) |

The `cask "google-cloud-sdk"` line is how `gcloud`/`bq`/`gsutil` land on every machine reproducibly — the same CLI used for Cloud Run, GCS, and BigQuery work. Keeping it in the Brewfile means a fresh machine has the GCP toolchain after one `brew bundle install`, not a manual SDK download.

A formula can be **superseded over time** — a project drops its Homebrew-core formula for a vendor cask or tap. When `brew bundle` starts failing on a once-good entry, or `brew` warns a formula is deprecated/disabled, migrate it rather than leaving a line that fails every `brew bundle install`: update the entry type in the source Brewfile, tombstone the old name (so a synced union capture can't resurrect it), and add the replacement.

### Stay current, not just pinned — `brew outdated` on a cadence

`brew bundle` makes the machine *reproducible*; it does not keep it *current*. This is the Homebrew face of the SKILL.md **DEPENDENCY MANAGEMENT** *stay-current-don't-just-stay-pinned* rule: a formula frozen for years drifts toward deprecation (the superseded-formula case above) and misses upstream fixes.

- **Check currency report-first, upgrade deliberately.** Run `brew outdated` (and `mas outdated` — report-only, see the mas section) periodically to *see* what has drifted, then move the ones you've decided to move with a targeted `brew upgrade <formula>`, re-`dump` the Brewfile, and commit the changed entries as code. Keep the check report-first and the upgrade a reviewed change.
- **Never a blind fleet-wide `brew upgrade`.** In an install-only synced-Brewfile setup an unscoped `brew upgrade` on one machine desynchronizes the union and thrashes the next sync — the same hazard as `brew bundle cleanup` above. Upgrade named formulae on purpose, review the diff, then propagate via the committed source, not by racing each machine forward independently.

### Vet third-party taps — a tap runs arbitrary install code

**Adding a tap or installing from one executes formula Ruby on your machine with your privileges.** A formula's `install` block can run any command. Treat an untrusted tap exactly like piping a stranger's script into your shell.

- Prefer `homebrew/core` and `homebrew/cask` (audited, the default). For a third-party tap, only add ones from the upstream vendor's own org (e.g. `hashicorp/tap`) — confirm the GitHub org is the real project, not a typosquat.
- A cask that pulls a binary from a random URL is the same supply-chain risk as an unpinned npm dep — flag it for review rather than silently adding it.
- **Never run `brew` as root / under `sudo`.** Homebrew refuses it for a reason: a root-owned `/opt/homebrew` (Apple Silicon) lets any later formula write system-owned files, and a compromised formula then runs as root. If a `brew` step in setup automation wants `sudo`, that is the bug — fix prefix ownership (`sudo chown -R "$(whoami)" "$(brew --prefix)"`), don't escalate brew.

### QA gate: `brew bundle check`

`brew bundle check --file=~/Brewfile` verifies the manifest is fully satisfied — it exits non-zero if the machine doesn't match the file. Use `--verbose` to list the unmet dependencies. This is the convergence assertion for fresh-Mac setup and CI:

```bash
brew bundle check --file=~/Brewfile --verbose || {
  echo "Machine drifted from Brewfile — run: brew bundle install --file=~/Brewfile" >&2
  exit 1
}
```

Run it after install on a fresh/second machine to prove the machine reproduced. `brew doctor` is the complementary health check (broken symlinks, conflicting installs) — run it when a build misbehaves, not as a gate.

### Security testing: `brew audit` when authoring a formula

If you write a formula (private tap, internal tooling), `brew audit --strict --online <formula>` is the lint + security gate — it checks for unsafe patterns, bad URLs, missing checksums, and style. A formula without a pinned `sha256` for its download is an unverified-source finding; `brew audit` catches it. For casks, `brew audit --cask <token>`. Don't ship an internal formula that hasn't passed `--strict`.

---

## npm

This section **extends** the existing SKILL.md `npm audit` rule and the no-`*`/no-`latest` dependency rule — it does not restate them. Assume those still apply.

### Commit `package-lock.json`; install with `npm ci` in CI, never `npm install`

`npm install` may *rewrite* `package-lock.json` (resolving ranges to whatever is newest) — so it is non-reproducible by design and can pull a different dependency tree than the one you tested. `npm ci` installs **exactly** the locked tree, fails if `package.json` and the lockfile disagree, and deletes `node_modules` first for a clean slate.

- **CI and any reproducible/automated install use `npm ci`.** A Cloud Run container build for a Node service must `npm ci`, not `npm install`, or the deployed image can differ from what was tested. `npm install` is for *intentionally* changing dependencies during development.
- The lockfile is only meaningful if it's committed and current — a stale or uncommitted `package-lock.json` defeats both reproducibility and audit. This is the npm equivalent of the committed-Brewfile gate.
- **Gate the lockfile drift in CI.** `npm ci` already exits non-zero when `package.json` and the lockfile disagree — make it a required check so a hand-run `npm install` that quietly rewrote the tree can't merge unnoticed.
- **`npm audit signatures` verifies registry provenance** (packages were published by who they claim) — wire it as a gate, but note it needs **npm 9+**; pin a minimum `npm` (in `engines`/CI) or a fleet still on npm 8 silently skips it. For your *own* published packages, `npm publish --provenance` from CI (OIDC-backed) attests the build source — *verify whether it's automatic on your CI or needs the explicit flag against current npm docs.*

> Note: if you sync **global** npm packages across machines, use the same deliberate install-only-plus-tombstone model as brew. Per-project `node_modules` are not synced; the committed lockfile is the source of truth there.

### Pin the `engines` field

State the Node/npm versions the project is built for so a contributor (or a Cloud Run build) on the wrong major doesn't fail mysteriously:

```jsonc
"engines": { "node": ">=20 <21", "npm": ">=10" }
```

`engines` is advisory by default — to make a mismatch a hard error locally, set `engine-strict=true` in a committed project-level `.npmrc` (the `engine-strict` config key is current on npm 11). Verify exact enforcement behavior against the npm version actually in use.

### Lifecycle scripts are the supply-chain attack surface — `postinstall` runs arbitrary code

**The dominant npm supply-chain vector is a malicious `postinstall`/`preinstall` script in a dependency, which runs automatically the moment you install it — before you ever import the package.** Typosquatted package names (`crossenv` vs `cross-env`) exist specifically to get that script executed.

- For installing **untrusted or one-off** packages (evaluating something, not a committed dependency), use `npm install --ignore-scripts` so lifecycle scripts don't auto-run. Audit the package first, add it as a real dependency second.
- For a project that genuinely needs **zero** lifecycle scripts, set `ignore-scripts=true` in committed `.npmrc` — but know that some legitimate native-module packages won't build without their `postinstall`, so this is a per-project decision, not a blanket rule.
- Treat a *new or unexpected* `postinstall` appearing in a dependency diff as a security event worth reading the script before merging — exactly what dependency-review in PR flow is for (below).

### Supply-chain security gates

| Gate | Command | What it catches |
|---|---|---|
| Vuln scan (existing rule) | `npm audit` | known CVEs in the dep tree; resolve/document HIGH |
| Registry signature integrity | `npm audit signatures` | tampered/unsigned packages vs. the registry's signatures |
| Publish provenance | `npm publish --provenance` | (when *you* publish) cryptographically links the package to its CI build + source commit |
| Deeper supply-chain | Socket / Snyk | new install scripts, suspicious network/filesystem use, maintainer changes — beyond CVE lists |

- `npm audit signatures` verifies the packages you installed match what the registry says it served — catches tampering that a CVE scan won't. Run it alongside `npm audit` in CI.
- `npm publish --provenance` (run from a CI provider that supports OIDC, e.g. GitHub Actions on `<org>/*`) attaches a verifiable provenance statement tying the published artifact to the exact source commit and build — the publishing side of the same trust chain.
- `npm audit` / Socket / Snyk give *signal*, not gospel — triage findings against whether the vulnerable code path is actually reached. Document an accepted HIGH with rationale; don't let an unfixable transitive advisory block delivery silently.

### Never commit tokens in `.npmrc` — use env interpolation

An `_authToken` written literally into a committed `.npmrc` is a leaked credential (exactly the kind of thing the SKILL.md secrets protocol exists to stop). npm expands `${VAR}` in `.npmrc` at read time, so reference an environment variable instead and source the value from 1Password:

```ini
# .npmrc (safe to commit — no literal secret)
//registry.npmjs.org/:_authToken=${NPM_TOKEN}
```
```bash
# token comes from 1Password, never the repo
export NPM_TOKEN="$(op read 'op://Private/npm/token')"
```

A committed `.npmrc` should contain only registry config and env *references* — never a literal token. If a real value must live on disk locally, confirm that file is git-ignored.

### Version-range discipline (cross-reference)

The no-`*`-and-no-`latest` rule is already in SKILL.md DEPENDENCY MANAGEMENT — it applies here verbatim. The lockfile pins the *resolved* tree, but a loose range in `package.json` still lets the next `npm install` (or a fresh resolve) drift you onto a newer, unvetted version. Keep ranges tight (`^`/`~` with intent, exact pins for anything security-sensitive) so the manifest and the lockfile tell the same story.

---

## mas (Mac App Store CLI)

`mas` is the App Store CLI. Treat it as a **reporting and re-install** tool, and keep it out of a synced manifest. Two non-obvious facts drive that:

- **Keep App Store apps out of a synced Brewfile.** Capture with `brew bundle dump --force --no-mas`. App Store apps are tied to a specific Apple ID and are permanently divergent across machines, so unioning them across a fleet thrashes. `mas "...", id: ...` is valid Brewfile syntax in general; it's just a poor fit for a synced manifest.
- **Do not run `mas upgrade` from update automation.** On modern macOS, `mas` does **not** suppress terminal echo when prompting for the App Store password, so credentials can appear in clear text and get captured in a log file — a credential-leak finding. The tested house pattern is **report-only**, with installation handled by the system:
  ```bash
  mas outdated   # report what App Store apps have updates (safe; no auth)
  ```
  Actual installation is left to **System Settings → App Store → Automatic Updates**, which authenticates securely through the system UI. Treat a script that calls `mas upgrade`/`mas install`/`mas get` non-interactively in a logged context as a security finding, not a convenience.

### Useful commands and the durable caveat

```bash
mas list       # installed App Store apps, with numeric IDs
mas outdated   # pending updates (reporting)
```

The mas surface shifts across macOS releases — **state behavior as principle and verify a specific against current `mas` + macOS docs before relying on it:**

- **`mas` requires being signed into the App Store.** Sign-in is done through the GUI App Store app on current macOS; the CLI sign-in path has been unstable across versions (e.g. the installed `mas` exposes `signout` but no `signin` subcommand). No sign-in → mas can't install.
- **mas can install free apps and re-install apps already associated with the signed-in Apple ID** (`mas get`/`purchase`, root-required on recent versions), but it is not a reliable way to first-acquire *paid* apps from the CLI. Practically, treat mas as a way to **re-install and report on apps this machine/Apple ID already knows** — which is the reproducibility use case — not a general app-discovery installer. Do first acquisition once in the GUI App Store.
- Because App Store apps are excluded from the synced manifest and are Apple-ID-specific, **do not expect a fresh-Mac `brew bundle install` to reproduce them** — that is by design. If second-machine App Store parity ever matters, document the manual GUI step rather than trying to script it through mas.

---

## Quality & security gates — summary

- **Reproducibility gate (QA).** Manifests committed, pinned, converged: the `Brewfile` (`brew bundle check` passes), `package-lock.json` committed (`npm ci` installs it cleanly). A machine that doesn't match its manifest, or a synced source change that isn't committed + pushed, is a finding.
- **Supply-chain gate (security).** `npm audit` + `npm audit signatures` (HIGH resolved or documented), `brew audit --strict` on any formula you author, dependency-review on the lockfile/Brewfile diff in PR flow, and **no `mas upgrade` in a logged automation context** (credential echo). Lifecycle-script changes (`postinstall`) and new third-party taps get read before merge.
- **Secrets gate.** No literal `_authToken`/credential in any committed manifest or `.npmrc` — env reference sourced from 1Password (`op read`), same as the SKILL.md secrets protocol.
- **Flag, don't absorb.** Any unpinned dependency, loose version range, untrusted tap, raw-URL cask, or literal token in a manifest is surfaced explicitly — same posture as the SKILL.md "flag stray changes" rule. A package manager's job is to make the machine reproducible *and* the supply chain auditable; a manifest that does one without the other isn't done.
