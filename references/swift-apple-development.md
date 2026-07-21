# Swift & Apple-Platform Development — project generation, tooling & supply-chain gates, security floor, CloudKit sync, concurrency & field diagnosis

Companion reference for the senior-engineering-partner skill.

**Scope:** the deep discipline for building macOS/iOS/watchOS/iPadOS apps in Swift — project
generation, signing/provisioning, cross-device state design, CloudKit sync with `CKSyncEngine`,
Swift 6 concurrency field notes, the on-device diagnosis toolkit, and the enforcement lane:
lint/format/compiler gates (§8), SwiftPM supply chain (§9), the Apple bindings of the security
floor (§10), the test-harness and coverage gates (§11), and CI wiring (§12). The floor itself
lives in SKILL.md and is not repeated (secrets, input validation, least privilege, isolation) —
§10 binds it to Apple surfaces. Adjacent references own their pieces: LaunchAgent `.app`
packaging + TCC/FDA + Developer ID hardened-runtime/notarization → `macos-app-bundles.md`;
Xcode workspace hygiene → `dev-environments.md`; UI/a11y (which fully applies to SwiftUI —
Dynamic Type, 44 pt targets, Reduce Motion, light/dark + the three-state appearance control) →
`ui-design-and-accessibility.md`; general test taxonomy → `testing.md`; the Swift CI job shape
→ `github-actions.md`. Distribution ownership is stated explicitly in §13.

Every rule here was extracted from live multi-device bring-up of a shipping app — the costs
cited (one-shot sync, uncatchable crashes, devices drifting apart) were all paid for real.
OS-version-volatile behaviors are flagged inline: verify them on your target OS, not from memory.

---

## 1. Project structure & generation

- **The project manifest is source code; the `.xcodeproj` is a build artifact.** Generate the
  project with **XcodeGen** from a committed `project.yml`: the generated `.xcodeproj` is
  **never committed and never edited through the Xcode UI** — a UI edit to a generated project
  is lost on the next `xcodegen generate`, and an `.xcodeproj` diff is unreviewable. Build =
  `xcodegen generate && xcodebuild …`. Record the choice as an ADR — it trades Xcode's default
  workflow for reviewable, mergeable project definition.
- **Stage capability blocks in `project.yml` before you can use them.** Entitlements that
  depend on something external (a paid developer account, a provisioned container) go in as
  **commented staged blocks** next to the settings they'll join, uncommented the day the
  capability is real — the diff that activates a capability is then two uncomments, not a
  from-scratch authoring session. Gate the code path at runtime on the entitlement actually
  present (e.g. a SecTask entitlement check) so the same binary runs correctly unsigned.
- **Pure logic lives in a SwiftPM package, not the app target.** Timer math, state machines,
  merge logic, history bucketing — a platform-free package with **injected clocks** and
  deterministic tests (`swift test` in CI, no simulator required). App targets are thin
  adapters over it. This is the skill's isolate-logic-from-adapters rule, bound to Swift;
  cross-platform UI shares a `Shared/` source group with per-platform target folders.

## 2. Signing, provisioning & devices

- **Dev-signed builds run ONLY on registered devices.** A dev-signed app copied to an
  unregistered machine will not launch — that's provisioning, not a bug. Register devices in
  the developer portal; the UDID form field must contain the bare identifier — a pasted
  value carrying a `UDID ` label prefix is silently invalid.
- **Provision headlessly with `-allowProvisioningUpdates`.** Added to `xcodebuild` (plus
  `-allowProvisioningDeviceRegistration` for new devices), it mints certificates, registers
  App IDs and capabilities, and generates profiles without opening Xcode — and it works with
  **generic destinations** (`-destination 'generic/platform=iOS'`), so CI or a headless session
  can produce installable device builds.
- **Verify what a build actually carries — never assert entitlements from the manifest.**
  `codesign -d --entitlements - <app>` shows the entitlements really embedded;
  `security cms -D -i <profile>.provisionprofile` shows a profile's `ProvisionedDevices`. The
  manifest is intent; the binary is fact (the skill's verify-before-assert rule, bound here).
- **App Group IDs are platform-asymmetric for dev-signed apps.** On some macOS versions,
  `containermanagerd` **rejects `group.*` identifiers for dev-signed apps** ("should be
  prefixed by requestor's team ID") — the macOS group is `<TEAMID>.<bundle-id-root>` while
  iOS/watchOS use `group.<bundle-id-root>`. Version-volatile: verify on your target macOS.
  And keep the scopes straight: an **App Group is intra-device** (app ↔ widget/extension);
  only cloud sync crosses devices — a value written to the group container has not "synced."
- **Container migrations are copy-not-move, newest-wins.** When state relocates (sandbox
  container → App Group), copy from every legacy location, adopt the newest by timestamp, and
  **leave the legacy files in place** — an older build that runs again (or a partial rollout
  on another device) must not find its data gone. Idempotent by construction.
- **An attached Xcode debugger keeps an iPhone from auto-locking.** A device that never
  sleeps during testing is the debugger's doing, not your app's — verify power/idle behavior
  by launching from the home screen, no cable.

## 3. Swift 6 concurrency — field notes

- **Assertions are not errors: no `try`/`catch` will ever see one.** A framework precondition
  failure (`EXC_BREAKPOINT`) terminates the process regardless of enclosing `do`/`catch` — so
  any claim that a call is "guarded by try/catch" must be **verified against the failure
  type**: guarded against thrown errors, unguarded against asserts. Design so the assert can't
  fire; you cannot recover from it.
- **Task-locals inherit into `Task {}` but NOT into `Task.detached {}`.** Both a bug source
  (state you expected to follow the child task doesn't) and a tool — `Task.detached` is the
  documented escape hatch when a framework uses a task-local to forbid re-entrancy (see the
  `CKSyncEngine` rule below). Know which one you're writing and why.
- **`nonisolated(unsafe)` only with a written justification.** It is a proof obligation
  transferred from the compiler to you — the comment must say why the access is actually safe
  (e.g. a framework type documented thread-safe but not yet `Sendable`-annotated). Bare
  `nonisolated(unsafe)` to silence a diagnostic is the Swift twin of a naked `# type: ignore`.
- **`@MainActor` statics and `Sendable` captures:** a `@MainActor` static accessed from a
  nonisolated context needs `await`; a closure crossing an isolation boundary can capture only
  `Sendable` values. Fix by moving the work to the right actor, not by sprinkling `unsafe`.

## 4. Cross-device state — never store ticks

- **Running state is an absolute end timestamp, not a countdown.** For any timer/progress
  value shown on multiple surfaces or devices, persist **when it ends** (plus what phase it
  is), never the remaining seconds. Every surface — app UI, widget, watch, Live Activity —
  derives remaining time from its **own wall clock**, so all devices agree to the second
  without exchanging a single update while running; sync latency delays only *transition*
  visibility, never correctness. Store an `updatedAt` for last-writer-wins on current-state
  values. ADR-worthy: it's the difference between zero steady-state traffic and a
  per-second update storm that widgets can't render anyway.
- **Let the system render countdowns.** SwiftUI `Text(timerInterval:)` (and the ActivityKit
  equivalents) render a live-updating countdown from a static timeline entry — **no
  per-second widget timelines, no per-second Live Activity updates**. Reload widget timelines
  at the moment new state is *applied* (one reload per transition), not on a schedule.

## 5. `CKSyncEngine` hard rules

Each of these cost a real outage or crash; none is guessable from the API surface:

- **Saves MUST reuse the server-returned `CKRecord`.** CloudKit's conflict detection rides on
  the record's change tag. Persist (or cache) the record the server returns and mutate *that*
  for the next save — building a fresh `CKRecord(recordType:recordID:)` for an existing row
  is rejected `serverRecordChanged` on every attempt, **forever**: sync works exactly once and
  never again. On a rejection, adopt the server record, re-apply your fields, and resend.
- **NEVER call `sendChanges()`/`fetchChanges()` inside the event handler.** `CKSyncEngine`
  wraps event delivery in a task-local and **hard-asserts** on re-entrant engine calls —
  `EXC_BREAKPOINT`, uncatchable (§3). Escaping requires `Task.detached`; a plain `Task {}`
  **inherits the task-local and still crashes**. Schedule follow-up work, don't perform it
  in-handler.
- **Change tokens are a bandwidth optimization, not a correctness mechanism.** A persisted
  token can be durably ahead of the state it describes (quit between token-save and
  state-apply = that change is skipped forever), and token-based fetches have gone stale even
  in-session. For a **small-record schema** (a handful of records), skip tokens for
  correctness paths: **fetch the records directly by ID and compare change tags** — a
  token-free poll is stale-proof by construction. At minimum, reconcile
  local-newer-than-server at every launch.
- **Seed the engine with current local state at start.** Restored pending saves are dropped
  if the batch provider has nothing to serve when asked — hand the engine your current state
  when you create it, and reconcile at launch, or a queued-then-relaunched save silently
  evaporates.
- **Timebox every awaited engine call in a loop.** A single hung `fetchChanges()` wedged a
  poll loop's `await` forever — silently, with no error. Race engine calls against a timeout
  (task group: real call vs `Task.sleep`), log the timeout at `.notice`, and let the next
  tick retry.
- **Silent pushes are the fast path, not the delivery guarantee.** Development-environment
  APNs silent pushes to macOS are demonstrably unreliable (version-volatile; verify on your
  stack). Design a **poll fallback** at a modest interval, and fire an immediate fetch on
  foreground-return (iOS `scenePhase`, macOS `didBecomeActiveNotification`) — the moment the
  user looks is the moment staleness is visible.
- **Choose conflict semantics per record type, and write them down.** Last-writer-wins fits
  current-state values (with `updatedAt`, §4). An append-only ledger (history, sessions,
  events) needs a **union merge**: model it as a grow-only set, merge = union + dedup, and
  **echo a merged result back only when it is a strict superset** of what the server holds —
  that combination is convergent (no entry lost regardless of arrival order) *and* settles
  (no infinite echo loop). Prove both properties with red-first tests before trusting it.

## 6. App Nap & background execution (macOS)

- **App Nap freezes idle apps' timer loops.** A `MainActor` polling loop in a windowless or
  occluded app stops ticking after a while (observed ~20 min) — the app isn't crashed, just
  napping, and it wakes with stale state. An app whose **background currency is a feature**
  (a sync poll, a countdown that must stay fresh) takes
  `ProcessInfo.processInfo.beginActivity(options: .userInitiatedAllowingIdleSystemSleep,
  reason:)` while the work is active and ends it (`endActivity`) when idle — that option
  still permits **system sleep** (a sleeping
  machine converging one tick after wake is correct behavior; a machine kept awake by a timer
  app is a bug). Pair it with the foreground-return fetch (§5) so waking the app always
  refreshes immediately.

## 7. Field diagnosis toolkit (macOS/iOS)

- **`log show` can return empty from sandboxed/automation shells — a false negative.** The
  archive query can silently yield nothing where entries exist; use **`log stream`** with a
  subsystem predicate for live capture. Remote capture over `ssh` needs the predicate in a
  **copied script** — inline quoting through ssh mangles it. (The skill's
  false-negative-search rule: an empty result from a tool that can fail empty is not
  "verified absent.")
- **Only `.notice` and above persist to the log archive** — `.info`/`.debug` are
  memory-only by default. Put lifecycle breadcrumbs (engine started, poll tick, save
  accepted/rejected, merge applied) at **`.notice`**, structured and **payload-free** — the
  never-log-content rule applies; log *about* the sync, never the synced data.
- **Crash triage reads `~/Library/Logs/DiagnosticReports/*.ips`** — JSON (a metadata first
  line + a body object); the body's `faultingThread` indexes `threads[]`, whose frames name
  the crashing code. **Monitor that directory for any deployed GUI app** — users report
  crashes late and vaguely; the OS reports them instantly and precisely. This is the
  observability floor (deployed code gets failure alerting) bound to local apps — a crash
  reporter you never read is the unread alert tab.
- **Verification one-liners:** `pluginkit -m -p <extension-point>` — is the
  widget/extension actually registered; `codesign -d --entitlements -` — what the build
  really carries (§2); `xcrun devicectl list devices` — pairing + Developer Disk Image
  state when a device build won't install.

## 8. Toolchain gates — lint, format, and the compiler as a gate

The Swift twin of the `ruff` + `mypy --strict` posture: every mandate names its checker, and
the checker is a merge-blocking gate run identically in CI and locally.

- **SwiftLint in strict mode is the lint gate.** `swiftlint lint --strict` (a committed
  `.swiftlint.yml` at the repo root scopes it) — `--strict` promotes warnings to errors so the
  gate actually gates; a warning-only lint run is advice, not a gate. Rule opt-ins/disables
  live in the committed config where a reviewer can see them — never inline-disable a rule
  without a justification comment (the `# nosemgrep`-with-reason posture).
- **`swift format` is the format gate.** The formatter ships **in the Swift 6+ toolchain**
  (`swift format`, the adopted apple/swift-format) — no third-party dependency:
  `swift format lint --strict --recursive Sources/ Tests/` fails CI on drift;
  `swift format --in-place --recursive` fixes locally. Older toolchains install
  swift-format separately; verify `swift format --version` on your toolchain.
- **The compiler is a gate, not just a build step.** Build in **Swift 6 language mode**
  (`SWIFT_VERSION = 6.0` in `project.yml` settings; `swiftLanguageMode(.v6)` in `Package.swift`)
  so strict concurrency checking is on and data races are compile errors, and make CI treat
  **warnings as errors** (`SWIFT_TREAT_WARNINGS_AS_ERRORS = YES`, or
  `swift build -Xswiftc -warnings-as-errors` for packages) — a warning that survives to `main`
  is a documented-forever exception nobody documented. A codebase not yet on the v6 mode
  ratchets like a legacy untyped Python module: new targets adopt it, the include list widens
  over time, never a blanket downgrade. (Setting names are toolchain-versioned — verify
  against your Xcode/Swift release.)
- **Mechanize the `nonisolated(unsafe)`-needs-justification rule (§3).** The written-comment
  mandate gets a deterministic backstop, same as documented-`# nosemgrep`: a CI grep asserting
  every occurrence carries an adjacent justification. The pattern below flags any
  `nonisolated(unsafe)` whose line (or the line above) lacks a comment:

  ```bash
  # gate: every nonisolated(unsafe) carries a same-line or preceding-line comment
  git grep -n "nonisolated(unsafe)" -- '*.swift' | while IFS=: read -r f n _; do
    line=$(sed -n "${n}p" "$f")
    prev=""; [ "$n" -gt 1 ] && prev=$(sed -n "$((n-1))p" "$f")
    case "$line" in *"//"*) continue;; esac
    case "$prev" in *"//"*) continue;; esac
    echo "UNJUSTIFIED nonisolated(unsafe): $f:$n" >&2; exit 1
  done
  ```

  A comment-shaped non-reason still passes the grep — the gate mechanizes *presence*; review
  judges *sufficiency*. Same division of labor as every documented-exception rule.

## 9. SwiftPM supply chain — pin, commit, audit

The skill's lockfile + audit discipline (SKILL.md *Dependency Management*, *Dependency-audit
gate*), bound to SwiftPM:

- **`Package.resolved` is the lockfile — commit it.** Same rule as `package-lock.json` /
  `Cargo.lock` / `poetry.lock`: an uncommitted `Package.resolved` means every clone and every
  CI run may resolve different dependency versions. Commit it for apps *and* for the pure-logic
  package; keep it in lockstep with the manifest in the same commit.
- **CI resolves pinned, never freshly.** `xcodebuild` takes
  `-onlyUsePackageVersionsFromResolvedFile` (alias `-disableAutomaticPackageResolution`) —
  "prevents packages from automatically being resolved to versions other than those recorded
  in the `Package.resolved` file"; SwiftPM's equivalent is
  `swift package resolve --force-resolved-versions` (also accepted by `swift build`/`test`).
  A CI run that silently re-resolves is the mutable-tag failure mode: green on versions you
  never reviewed. (Flags verified against Xcode 26 / Swift 6.3; re-verify on your toolchain.)
- **Pin by version, never by branch.** A `.branch("main")` dependency is a mutable tag — the
  build changes under you without a diff. `from:`/`exact:` version requirements only;
  `Package.resolved` then records the revision hash, which is the integrity check SwiftPM
  gives you (a version pin alone is not integrity — SKILL.md *Supply-chain integrity*).
- **The auditor is `osv-scanner` + Dependabot.** osv-scanner scans `Package.resolved`
  (the `swift/packageresolved` plugin, enabled by default since v2.4.0) against OSV's
  **SwiftURL** ecosystem, which the GitHub Advisory Database has curated since 2023; GitHub's
  dependency graph + **Dependabot alerts also support Swift** — so the enable-the-trio +
  alert-tab-at-zero rule (SKILL.md *GitHub security alerts*) applies to Swift repos with no
  carve-out. Wire osv-scanner into the same audit gate script CI and local runs share.
  (Support status is version-volatile — verify your osv-scanner version's supported-lockfiles
  list before relying on the gate.)
- **Build-tool plugins and macros are build-time code execution — vet them as such.** A SwiftPM
  build-tool plugin or macro runs *at build time* on your machine and in CI: the npm
  lifecycle-script twin (`package-managers.md`). The FOSS-adoption checklist
  (`foss-adoption.md`) applies with extra weight to any dependency that ships a plugin or
  macro; Xcode's per-plugin/macro trust prompts are the last line, not the vetting.

## 10. The security floor, bound to Apple surfaces

SKILL.md's floor controls, each with its Apple-platform mechanism. None of these is
tier-scalable — they hold at every tier, and none is ADR-overridable.

- **Runtime secrets live in the Keychain — never `UserDefaults`, never a plist, never source.**
  Keychain Services is the app-runtime binding of the secret-manager rule (the `op read` /
  `PropertiesService` twin): tokens, session keys, and per-user credentials go in with a
  deliberate `kSecAttrAccessible` choice (`…WhenUnlockedThisDeviceOnly` unless sync/background
  access is a stated need — the default is a decision, not a shrug), and a **Keychain access
  group** only when another target genuinely reads it (least privilege — an app-group-wide
  secret is a wider blast radius). `UserDefaults` and files in the container are backed up,
  unencrypted-at-rest relative to Keychain classes, and trivially readable on a jailbroken or
  backup-extracted device.
- **App Sandbox on, entitlements minimized.** For distributed apps the sandbox is the
  least-privilege boundary: **mandatory for App Store** distribution, the hardening default
  for Developer ID. Declare only the entitlements the app uses — each `com.apple.security.*`
  entitlement is a standing TCC-grade grant a reviewer must be able to justify; the staged-
  capability-block pattern (§1) exists so unused capabilities stay commented out, not shipped
  "just in case". Verify what the binary actually carries with
  `codesign -d --entitlements -` (§2) — the manifest is intent, the binary is fact.
- **App Transport Security stays intact — no arbitrary-loads exceptions.** ATS is the HTTPS
  floor bound to Apple platforms: `NSAllowsArbitraryLoads` (and its media/web-content
  variants) turns the floor off app-wide and is treated like committing a secret — a
  diff-checkable violation, not a config choice. A genuinely-required exception is
  **per-domain**, justified in the diff, and carries the App Review justification text; audit
  `Info.plist`/`project.yml` for `NSAppTransportSecurity` keys in review.
- **Privacy manifests are a shipping gate.** App Store submissions require
  `PrivacyInfo.xcprivacy` declaring collected data and **required-reason API** usage
  (enforced since May 2024) — an undeclared required-reason API is a review rejection, i.e. a
  red gate at the worst possible moment. Third-party SDKs on Apple's commonly-used list must
  ship their own privacy manifest **and signature** — check both at adoption time
  (`foss-adoption.md`), not at submission. This is the `data-protection.md` data-minimization
  discipline in Apple's enforcement clothing: the manifest is a *claim* about what you
  collect; keep it true in the same commit that changes what you collect. (Requirement
  details are Apple-policy-volatile — verify against current App Store submission docs.)
- **Every app-entry surface is a trust boundary.** Custom URL schemes, universal links,
  `NSUserActivity`/handoff payloads, drag-and-drop, XPC endpoints, and App Intents all deliver
  **attacker-influencable input** — the input-validation floor applies at each: validate and
  canonicalize before acting, never build file paths or commands from URL components, treat a
  URL-scheme payload like a webhook body (authenticated callers only where the action has
  side effects). XPC services additionally verify the *caller* (audit-token/entitlement
  checks), not just the message — an unauthenticated XPC endpoint in a privileged helper is
  the classic macOS LPE shape.

## 11. Test harness, plans & coverage

- **Two harnesses, one split.** Pure logic lives in the SwiftPM package (§1) and tests with
  **Swift Testing** (`@Test`/`#expect`) or XCTest via `swift test` — deterministic, no
  simulator, the fast lane CI runs on every push. App-target behavior (UI flows, extension
  wiring, anything needing a host app) tests via `xcodebuild test` against a **pinned
  simulator destination** (an unpinned "latest" destination is a version-skew flake source).
  New tests default to Swift Testing; XCTest remains for UI-automation and performance APIs
  it still owns — don't rewrite green XCTest suites for fashion.
- **A committed `.xctestplan` is the test manifest.** Test plans pin which suites run in
  which configuration (sanitizers, regions, repetitions) and make "what does CI run" a
  reviewable file instead of scheme-buried GUI state — the same manifest-over-IDE-state rule
  as `project.yml` (§1).
- **Coverage is a failing gate, not a report** — `testing.md` §3's branch-coverage rule,
  rebound: run `xcodebuild test -enableCodeCoverage YES`, read the result bundle with
  `xcrun xccov view --report --json <path>.xcresult`, and fail CI below the floor (xccov
  emits line/function coverage per target — gate the *package and app targets*, high floor on
  the pure-logic package; a thin `jq` assertion over the JSON is the gate). Swift has no
  `--cov-fail-under` equivalent built in, so the threshold check is a few lines of script —
  write it once, share it between CI and local like every other gate. (xccov output shape is
  Xcode-versioned; verify on your toolchain.)

## 12. CI wiring

The Swift job shape — macOS runners, `xcodegen generate && xcodebuild test` as the gate,
pinned resolution (§9), the coverage assert (§11), lint/format jobs (§8), signing via an App
Store Connect API key injected from the secrets manager
(`-authenticationKeyPath`/`-authenticationKeyID`/`-authenticationKeyIssuerID` — the manual-
signing-for-CI principle from `dev-environments.md`, mechanized), and the two
source-of-truth asserts (committed `project.yml` generates cleanly; no `.xcodeproj` is
tracked) — lives in **`references/github-actions.md`** with the rest of the pipeline
standards. Read it before wiring a Swift repo's CI.

## 13. Distribution ownership (who owns what)

Explicitly, so nothing falls between references: **`macos-app-bundles.md`** owns Developer ID
distribution mechanics — hardened runtime, notarization + stapling, the LaunchAgent `.app`
pattern. **This reference** owns the code-level submission gates for store-distributed apps:
sandbox + entitlement minimization, ATS integrity, the privacy manifest, pinned + audited
dependencies, and the test/coverage gates that must be green before any build is submitted —
for App Store, TestFlight, and Developer ID alike. **Out of scope here, deliberately:** the
go-to-market side of shipping — store listings, screenshots, pricing, review strategy,
marketing sites — belongs to whatever GTM process or skill the project uses; this discipline
ends where the engineering gates end (the build that reaches TestFlight/App Review is green,
signed, sandboxed, manifest-complete). If no GTM owner exists, say so in the project README
rather than letting submission steps go unowned.

## Sources

- Apple developer documentation: `CKSyncEngine`, WidgetKit, ActivityKit, `os.Logger`,
  `ProcessInfo` activity API, `xcodebuild` provisioning flags — behavior verified empirically
  where the docs are silent (push reliability, `containermanagerd` group-ID enforcement,
  token staleness); re-verify version-volatile items on your target OS.
- XcodeGen documentation (github.com/yonaskolb/XcodeGen) — `project.yml` schema.
- Toolchain gates (§8): SwiftLint (github.com/realm/SwiftLint) `--strict`; `swift format`
  subcommands and `-onlyUsePackageVersionsFromResolvedFile` / `--force-resolved-versions` /
  `-enableCodeCoverage` / `-authenticationKey*` flags verified against Xcode 26 / Swift 6.3
  `--help` output — re-verify on your toolchain.
- Supply chain (§9): osv-scanner release notes (`swift/packageresolved` default-on since
  v2.4.0); OSV **SwiftURL** ecosystem (osv.dev); GitHub changelog 2023-06-19 — dependency
  graph, Dependabot alerts & Advisory Database Swift support.
- Security floor (§10): Apple developer documentation — Keychain Services, App Sandbox,
  App Transport Security, privacy manifests / required-reason APIs (App Store enforcement
  since 2024-05-01), universal links / XPC; Apple-policy-volatile items flagged inline.
