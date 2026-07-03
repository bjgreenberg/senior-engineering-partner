# IDE & Dev-Environment Standards (VS Code, Xcode, Google Antigravity)

Companion reference for the senior-engineering-partner skill.


Editors and IDEs are a supply-chain and secret-leak surface, not just a UI. The three threats that actually bite here: an extension/plugin running with your full user privileges, a secret committed into editor or build config, and an unreviewed agent-generated diff landing in a shared repo. The quality gate for all three: **workspace config is committed, reproducible across your machines, and leaks nothing.** Anything synced via a config-sync tool must be byte-identical-correct on every machine — see SKILL.md's Machine-synced config discipline before touching any synced editor config.

---

## VS Code

### 1. Discipline / best practices

- **Commit `.vscode/`, but only the shareable subset.** `.vscode/settings.json` (workspace-level formatting, linter paths, `python.testing.*`) and `.vscode/extensions.json` (`recommendations` array) belong in the repo so every machine and any teammate get the same setup. **Never commit a `.vscode/launch.json` or `tasks.json` that embeds environment-specific absolute paths or args** — they break on the other machine. If a launch config must differ per machine, leave it out and document the setup in the README.
- **Workspace settings ≠ user settings.** Repo `.vscode/settings.json` is for *project* conventions (tab width, `editor.formatOnSave`, `python.defaultInterpreterPath` pointed at the project venv). Personal preferences (theme, keybindings) belong in **user** settings, synced by **Settings Sync via your Microsoft/GitHub account — never by committing them to a project repo.**
- **The integrated terminal inherits your full env.** It sources your shell init (`~/.zshrc`). Anything you `export` there — an `op read` result cached into a variable, a token — is visible to every task, debug session, and extension subprocess the terminal spawns. **Keep secrets out of shell init.** Fetch them at the point of use (`op read "op://vault/item/field"`) inside the script that needs them, scoped to that process, never exported globally. This is the same least-privilege rule SKILL.md applies to TCC grants.
- **Devcontainers for risky toolchains.** When a project pulls an unvetted toolchain or a pile of transitive npm/pip deps, develop it inside a `.devcontainer/` so the blast radius is a container, not your `$HOME` with its 1Password agent socket and SSH keys. Bash in `postCreateCommand` (the shipped default; use the shell your profile sets).

### 2. QA & quality gates

- **`extensions.json` recommendations are the reproducibility gate.** A new clone on either Mac should surface "this workspace recommends…" and install the same linters/formatters. If the project relies on an extension that isn't in `recommendations`, the setup is not reproducible — fix it.
- Pin the toolchain the editor *drives*, not the editor: the `requirements.txt`/`pyproject.toml` (pinned per SKILL.md) and `package-lock.json` are the source of truth. The editor config points at them; it does not replace them.
- Wire `.vscode/settings.json` to the real gates so they run on save / in the Problems panel: ShellCheck, the Python linter feeding `bandit`-clean code, and the test runner. CI on GitHub (`<org>/*` required checks) remains the authority — the editor is the fast local echo of it, never a substitute.

### 3. Test cases

- After editing committed `.vscode/` config, **verify it cold on another machine** (or a fresh clone): open the folder, confirm the recommended extensions resolve, the interpreter/venv is found, format-on-save fires, and the test runner discovers tests. A path that resolves on one machine but is hardcoded `/Users/...` breaks on another.
- Confirm no machine-specific absolute path leaked into committed JSON: `grep -R "/Users/you" .vscode/` should return nothing — use `${workspaceFolder}` and relative paths instead.

### 4. Security testing

- **Respect Workspace Trust. Open untrusted folders in Restricted Mode and keep them there.** A `.vscode/tasks.json` with `"runOptions": { "runOn": "folderOpen" }` is built to run on folder open. That auto-run is gated twice — the workspace must be **trusted** (automatic tasks never run in an untrusted/Restricted-Mode workspace) *and* automatic tasks must be allowed (`task.allowAutomaticTasks`, off by default, prompts Allow/Disallow the first time). So the danger is reflexively clicking **Trust** and then **Allow** on a repo you didn't author. Don't: read `.vscode/tasks.json` and `.vscode/launch.json` first. A cloned third-party repo is untrusted by default — treat it that way. (Verify the exact setting name/default against current VS Code docs; the trust-then-allowlist behavior is the durable part.)
- **Vet every extension — it runs with your full user privileges.** An installed extension can read your files, spawn processes, reach the network, and see anything in the integrated terminal's env. This is a real supply-chain vector (typo-squatted and trojaned extensions ship regularly). Install only extensions you can justify; prefer first-party (Microsoft Python, ms-vscode) and high-reputation publishers; check publisher, install count, and source repo; remove anything you're not actively using.
- **Scan committed editor config for secrets before every push** — same `git-secrets`/`gitleaks` gate SKILL.md mandates. The classic leak is an API key or connection string pasted into `settings.json` (`"someTool.apiKey": "..."`) or a token baked into a `tasks.json` command. Secrets come from `op read` at runtime, never from committed JSON. Supabase service-role keys, Stripe secret keys, and GCP service-account JSON in particular must never appear in any `.vscode/` file.
- Settings Sync syncs user settings through your account — audit that you have not let a personal access token or a snippet containing a secret ride along in synced user config.

---

## Xcode

Xcode is in scope for the macOS `.app` work the fleet already does (the `UpdateAll.app` / LaunchAgent launcher pattern). **`references/macos-app-bundles.md` owns the bundle layout, the C launcher, ad-hoc signing, hardened-runtime/notarization, and TCC/FDA rules — read it for anything that ships or runs on another machine.** This section covers Xcode-the-IDE hygiene; it does not restate that standard.

### 1. Discipline / best practices

- **Signing: automatically-managed for local/interactive, manual for CI.** "Automatically manage signing" lets Xcode provision against your Apple ID for day-to-day local builds. For reproducible CI (`xcodebuild`), use **manual** signing with an explicit signing identity and provisioning profile installed on the runner — auto-signing depends on interactive Apple ID state that a headless runner doesn't have, and you want CI builds deterministic, not dependent on whatever profile Xcode regenerated last.
- **Separate Debug and Release configs and schemes.** Debug builds carry symbols, verbose logging, and dev endpoints; Release is what you sign, harden, and notarize. Never ship a Debug build. Keep scheme settings (e.g. which config Archive uses) deliberate, not defaulted.
- **Manage command-line tools with `xcode-select`.** Point the active developer dir explicitly so `xcodebuild`, `clang`, etc. are the version you intend on every machine:
  ```bash
  xcode-select -p                                   # print active dev dir
  sudo xcode-select -s /Applications/Xcode.app/Contents/Developer  # set it (needs sudo; affects all users)
  ```
  The bare Command Line Tools (`/Library/Developer/CommandLineTools`) and a full Xcode are different toolchains — and `xcodebuild` requires the full Xcode, not the CLT. A build that works on one machine and fails on another is often this mismatch. The C launcher in `references/macos-app-bundles.md` (`cc -O2 -arch arm64 -arch x86_64 …`) compiles against whatever `xcode-select` points at, so keep all machines aligned.

### 2. QA & quality gates

- **`xcodebuild` is the reproducible gate, not the Xcode GUI.** CI and any "does it build clean" check run `xcodebuild` with an explicit scheme/config so the result doesn't depend on hidden GUI state:
  ```bash
  xcodebuild -scheme MyScheme -configuration Release \
    -destination 'platform=macOS' clean build
  xcodebuild -scheme MyScheme -configuration Release test
  ```
  (Verify exact destination/flags against current `xcodebuild` docs for the target platform.)
- Treat compiler warnings as gate failures — the SKILL.md "zero warnings is the standard" rule (stated there for ShellCheck) applies here too. Set `SWIFT_TREAT_WARNINGS_AS_ERRORS = YES` for Swift and `GCC_TREAT_WARNINGS_AS_ERRORS = YES` for Objective-C/C on the Release config (they are separate settings — the GCC one does not cover Swift).

### 3. Test cases

- Use the project's test target (`XCTest`/`XCUITest`) and run it headless via `xcodebuild … test` so the same suite runs locally and in CI. Mirror SKILL.md's test-quality rules: name tests for the behavior asserted, not `test1`.
- For any compiled launcher destined for a `.app` bundle, the real integration test is end-to-end in the bundle — build it, sign it, install it, and confirm it runs under the LaunchAgent and (if FDA is involved) actually reads the protected path without `Operation not permitted` / exit 126. That verification procedure lives in `references/macos-app-bundles.md`.

### 4. Security testing

- **`.gitignore` all signing material and local build state — never commit it.** At minimum:
  ```gitignore
  *.p12
  *.cer
  *.mobileprovision
  *.provisionprofile
  exportOptions.plist
  *.xcuserstate
  xcuserdata/
  DerivedData/
  build/
  ```
  Certificates and private keys (`*.p12`) and provisioning profiles are credentials — they belong in 1Password / the CI secret store, installed onto the runner at build time, not in git. A committed `*.p12` is a signing-identity compromise.
- **No hardcoded secrets in `Info.plist` or source.** This is the SKILL.md zero-tolerance no-hardcoded-secrets rule applied to Apple targets: API keys, tokens, and endpoints with embedded credentials must not live in `Info.plist`, `*.entitlements`, asset catalogs, or `.swift`/`.m` source — they're trivially extracted from a shipped binary with `strings`. Inject at build time or fetch at runtime; for tooling, `op read`.
- Run the no-secrets scan (`gitleaks`/`git-secrets`) over the Xcode project the same as any repo before push. Provisioning UUIDs and team IDs in a committed `project.pbxproj` are expected (commit `project.pbxproj`); private keys and API tokens are not.
- For anything distributed or run on another machine, **hardened runtime + Developer ID signature + notarization are mandatory** — unsigned/ad-hoc is acceptable only for tools that never leave the Mac. The signing-options table and the notarization rationale are in `references/macos-app-bundles.md`; do not duplicate or contradict it here.

---

## Google Antigravity (Google's agentic IDE)

> **Verify UI specifics against current Google Antigravity docs.** Antigravity is new (Gemini-backed, with an Agent Manager that spawns agents across workspaces) and its menus, permission model, and defaults change between releases. The rules below are the **durable disciplines** that hold regardless of the exact UI — do not assume a specific menu item, setting name, or default exists; check the product's current documentation before relying on one.

The core shift: an agentic IDE writes code, runs commands, and edits files **on your behalf**. Treat that the way you'd treat a junior engineer with commit access and a terminal — with review, scoping, and an audit trail.

### 1. Discipline / best practices

- **Review every agent-generated diff with the same rigor as a human pull request. Read it before accepting — no auto-accept on faith.** An agent confidently produces plausible-but-wrong code, invents APIs, and occasionally proposes destructive shell commands. You are the reviewer of record; the SKILL.md `REVIEW:` standard (security, edge cases, correctness, then the fix) applies to machine-authored diffs exactly as to human ones.
- **Never let the agent auto-approve destructive or irreversible actions.** `rm`/`unlink`, force-push, `DROP`/`DELETE` against a real database, `gcloud`/`gsutil` mutations, dependency removals — these require an explicit human gate. (Antigravity gates shell/terminal commands behind a per-command confirmation policy by default rather than running them unprompted — verify the current default and setting names against Antigravity's docs; leave that posture on, don't widen it to blanket-allow.) Recall the environment's sharp edges: a deliberately-public GCS bucket **must stay public** (flipping it private breaks BI dashboards that hotlink its raw URLs), and Supabase RLS policies are tenant-isolation boundaries — an agent "tidying" either is a production incident. Keep a human in the loop for any command that mutates cloud or DB state.
- **Scope the agent to least privilege.** Point it at one project/worktree, not your whole `$HOME`. Don't run it where it can reach your SSH keys, the 1Password agent socket, or unrelated repos. Same principle SKILL.md enforces for TCC: grant the minimum the task needs, and never the agentic equivalent of FDA-to-`/bin/bash`.

### 2. QA & quality gates

- **The non-negotiable gate: an agent's work passes through the same CI as a human's.** Agent-authored changes land via branch → PR → required CI on GitHub, never direct-to-`main`. Branch protection on `<org>/*` is exactly what catches an agent that skips tests or ignores a linter. The gate is identical to the human one by design — don't build an agent bypass.
- ShellCheck / `bandit` / `npm audit` (SKILL.md mandated) run on agent output before merge, no exception. Machine-written code is *more* likely to need them, not less.

### 3. Test cases

- Require tests **for** the change and run them yourself — do not accept the agent's assertion that they pass. Re-run locally and confirm green (SKILL.md: "verify the end state, don't assume it"). An agent that writes a test asserting its own (wrong) behavior passes its own suite while shipping a bug.
- Diff-test the side effects, not just the code: after an agent session, run `git status` / `git diff` and account for **every** changed file. Flag, never sweep in, edits you didn't intend — the SKILL.md "flag, don't absorb, stray changes" rule is sharper here because the agent, not you, made the edits.

### 4. Security testing

- **Keep secrets out of the agent's context.** An agentic IDE transmits prompt/context to a model provider — for Antigravity that is Gemini (and, via Model Garden, potentially other vendors' models). Anything in the open files, terminal scrollback, or pasted context can leave the machine. Do not put live credentials, `op read` output, Supabase service-role keys, Stripe keys, GCP service-account JSON, or customer/tenant data where the agent can read them. Reference secrets by secret-manager reference (e.g. a 1Password `op://` path); let the runtime resolve them, outside the agent's view.
- **When the agent writes to a shared repo, `references/multi-agent-coordination.md` governs.** The agent is a second writer the moment it touches a tree another agent or human shares: one worktree/branch/task per writer, branch + PR (never direct-to-`main`), squash-merge (`gh pr merge --squash`, never rebase — SKILL.md), `git pull --rebase` before push, stage by explicit path (never `git add -A` in a shared tree), single-writer ownership for un-branchable state. That file is the full standard — follow it, don't re-derive it.
- **Audit and log what the agent executed.** Keep a record of the commands it ran and the diffs it produced so an unexpected outcome is traceable. Per SKILL.md, route any logging to the platform's user-log location (`~/Library/Logs/<tool>.log` on macOS; elsewhere the host's idiom) with rotation and `chmod 600` — agent transcripts capture paths, hostnames, and sometimes secrets, so they are not world-readable and not committed to a repo.
- Unattended agent commits follow the SKILL.md per-invocation signing exemption (`git -c commit.gpgsign=false commit …`) — 1Password may be locked when automation fires. The exemption is per-invocation, never per-machine.

---

## Cross-IDE summary

| Threat | VS Code | Xcode | Antigravity |
|---|---|---|---|
| Supply chain | Vet/limit extensions (full user privs) | `.gitignore` signing material; pin toolchain via `xcode-select` | Review every diff; scope agent to least privilege |
| Secret hygiene | No secrets in `settings.json`/`tasks.json`; secrets out of shell init | No keys in `Info.plist`/source; no `*.p12` in git | Secrets out of agent context (transmitted to model provider) |
| Review discipline | Workspace Trust; read `tasks.json` before trust + allow | Debug vs Release separation; warnings-as-errors | Agent diff = human PR; CI is the gate |
| Reproducibility gate | Commit `.vscode/` + `extensions.json`, machine-portable | `xcodebuild` (not GUI), manual signing in CI | Branch → PR → required CI, identical to human |

The unifying rule: **committed editor/build config must be reproducible across machines and leak nothing; agent-driven changes get human-PR review and ride the same CI gate as everything else.** Anything that syncs goes through the Machine-synced config discipline (SKILL.md), byte-identical-correct on every machine.
