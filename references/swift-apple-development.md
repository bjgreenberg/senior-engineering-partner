# Swift & Apple-Platform Development — project generation, CloudKit sync, concurrency & field diagnosis

Companion reference for the senior-engineering-partner skill.

**Scope:** the deep discipline for building macOS/iOS/watchOS/iPadOS apps in Swift — project
generation, signing/provisioning, cross-device state design, CloudKit sync with `CKSyncEngine`,
Swift 6 concurrency field notes, and the on-device diagnosis toolkit. The floor itself lives in
SKILL.md and is not repeated (secrets, input validation, least privilege, isolation). Adjacent
references own their pieces: LaunchAgent `.app` packaging + TCC/FDA → `macos-app-bundles.md`;
Xcode workspace hygiene → `dev-environments.md`; UI/a11y (which fully applies to SwiftUI —
Dynamic Type, 44 pt targets, Reduce Motion, light/dark + the three-state appearance control) →
`ui-design-and-accessibility.md`; general test taxonomy → `testing.md`.

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
  `UDID xxxxxxxx…` prefix (as Finder/System Information copy it) is silently invalid.
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
  `ProcessInfo.beginActivity(.userInitiatedAllowingIdleSystemSleep, reason:)` while the work
  is active and ends it when idle — that option still permits **system sleep** (a sleeping
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

## Sources

- Apple developer documentation: `CKSyncEngine`, WidgetKit, ActivityKit, `os.Logger`,
  `ProcessInfo` activity API, `xcodebuild` provisioning flags — behavior verified empirically
  where the docs are silent (push reliability, `containermanagerd` group-ID enforcement,
  token staleness); re-verify version-volatile items on your target OS.
- XcodeGen documentation (github.com/yonaskolb/XcodeGen) — `project.yml` schema.
