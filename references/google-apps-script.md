# Google Apps Script Discipline

Companion reference for the senior-engineering-partner skill.

> **Rigor tier:** GAS work is most often Tier 0/1 (a personal automation, a Sheets-bound script, a scheduled report). Apply the lean baseline — but the security floor holds at every tier: secrets in `PropertiesService` (never literals), **least-privilege OAuth scopes**, input validation on anything the script ingests, and structured failure logging. A script that emails on a trigger, touches a shared Sheet, or calls an external API has crossed into territory where the floor bites.

Apps Script is one of this skill's four headline languages. It is real software running on Google's infrastructure with a real OAuth grant against the user's Workspace — treat it that way, not as "a macro." The recurring failure modes are specific to the platform: the built-in editor as the only copy, an over-broad scope grant, a trigger that blows the 6-minute wall, a concurrent write that corrupts a shared store, and logic so entangled with `SpreadsheetApp` that nothing is testable.

> *The quotas, limits, and manifest fields below are **version-specific and change without notice** (Google's own caveat). The numbers here are current as of writing — **verify against live limits** at the Quotas page before relying on a ceiling, and check the manifest field names against current docs before pinning syntax. The discipline (minimize scope, isolate logic, lock shared writes, log structurally) is durable; the exact numbers are not.*

---

## 1. `clasp` + real version control (the editor is not a backup)

The in-browser Apps Script editor is a single mutable copy with no diffs, no branches, no review, and no offline recovery — editing production code live in it is the GAS equivalent of `vim`-ing on prod. Pull the project into a real repo and treat it like any other code:

- **`clasp` is the bridge.** `clasp clone <scriptId>` pulls the project to local files; `clasp push` / `clasp pull` sync; `clasp` keeps `.js`/`.gs` + the `appsscript.json` manifest as plain text you can commit, diff, and PR. Wire it into the same branch → PR → review gate as everything else (SKILL.md *Source Code Management*) — no direct edits to the deployed copy.
- **Commit the manifest.** `appsscript.json` carries the OAuth scopes, runtime version, and trigger config — it is the security surface of the project and **must** be in git and reviewed on every change (§3). A scope added silently in the web editor is an un-reviewed privilege escalation.
- **Pin the V8 runtime** in the manifest (`"runtimeVersion": "V8"`) so ES6+ syntax (Coding Standards) is available and behavior is reproducible — don't leave it on the deprecated Rhino runtime by accident.
- **`.clasp.json` holds the `scriptId`, not secrets.** It is safe to commit. Real secrets never live in any committed file (§5).
- *Verify the current `clasp` command surface and login flow against its docs before scripting around it — the CLI evolves.*

---

## 2. Triggers + their quotas (the 6-minute wall is real)

Two trigger kinds, and the distinction is load-bearing for both security and reliability:

- **Simple triggers** (`onOpen`, `onEdit`, `onInstall`) run automatically, **cannot** access services that need authorization, and run with tight limits — use them only for in-document UI/light edits.
- **Installable triggers** (time-driven, on-edit, on-form-submit, on-change) run **as the installing user** with that user's full authorization. That is the dangerous one: an installable trigger carries a real OAuth grant and fires unattended. Create them in code (`ScriptApp.newTrigger(...)`) so they're reproducible and reviewable, not hand-wired in the UI where they rot invisibly.

**Quotas and limits (verify against live limits — current at writing):**

| Limit | Consumer (gmail.com) | Workspace account |
|---|---|---|
| Script runtime **per execution** | 6 min | 6 min |
| Custom function runtime per execution | 30 sec | 30 sec |
| Total **trigger runtime per day** | 90 min | 6 hr |
| Triggers per user per script | 20 | 20 |
| Simultaneous executions per user | 30 | 30 |
| `UrlFetchApp` calls per day | 20,000 | 100,000 |

- **The 6-minute execution wall is the classic GAS crash.** A trigger that iterates thousands of rows or makes a fetch per row will hit it and die mid-run, leaving partial state. Design for it: **batch** Sheets I/O (one `getValues()`/`setValues()` over a range, never a per-cell `getValue()` in a loop — that's both slow and quota-burning), process in chunks, and for genuinely long work **checkpoint progress to `PropertiesService` and re-schedule a continuation trigger** so each run stays under the wall and resumes idempotently. A re-run that double-processes a row is a correctness bug — make the work idempotent (mark rows done, key by id).
- **The daily trigger-runtime budget is small** (90 min on a consumer account). A hot trigger that runs every minute and does real work will exhaust it and silently stop firing — which emits no error (cross-ref *dead-man's-switch*, `logging-and-monitoring.md`). Right-size the trigger interval to the work, and alert if expected runs stop.
- **Triggers fail silently by default.** A thrown error in a time-driven trigger surfaces only in the executions list / an emailed failure notice — wire explicit failure alerting (§7), don't assume you'll notice.

---

## 3. OAuth scope minimization (least privilege, explicit `oauthScopes`)

A GAS project requests an OAuth grant against the user's Google account; an over-broad grant is the same least-privilege violation as a wildcard IAM role.

- **Auto-detected scopes over-reach.** Apps Script scans the code and auto-grants scopes — and it errs broad (e.g. pulling in a full read/write Drive scope when you only read one file). **Pin an explicit, minimal `oauthScopes` array in `appsscript.json`** and review it: list only the scopes the code actually needs.
- **Prefer the narrowest scope that works** — e.g. `.../auth/spreadsheets.currentonly` (the bound document only) over `.../auth/spreadsheets` (every Sheet the user owns); a per-file/per-document scope over an account-wide one. Each broadened scope widens the blast radius if the script (or a dependency it calls) is compromised.
- **The scope set is a reviewed artifact.** Because the manifest is committed (§1), a scope change shows up in the diff and gets a second look — a new `mail.google.com` or full-`drive` scope appearing in a PR is a flag, not a rubber stamp.
- *Verify scope strings against the current OAuth-scopes reference; the manifest field is `oauthScopes`. Published add-ons must not request more scope than they need.*

---

## 4. `LockService` — concurrency on shared Sheets/Properties

Multiple trigger executions (up to 30 simultaneous per user) can run the same code at once. Any read-modify-write against a **shared** store — a counter in Script Properties, an append to a shared Sheet, a sequence number — is a race: two executions read the same value, both increment, one write is lost.

- **Wrap the critical section in a lock.** `LockService.getScriptLock()` serializes across all users (the right choice for a shared resource); `getUserLock()` serializes one user against themselves; `getDocumentLock()` scopes to the open document.
- **Always set a timeout and always release** — the canonical shape:
  ```javascript
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) {           // ms; bail if contended rather than hang
    throw new Error('Could not obtain lock; another run holds it');
  }
  try {
    // read-modify-write the shared Sheet / Script Property here
  } finally {
    lock.releaseLock();                 // release in finally — never leak a lock
  }
  ```
  `tryLock(timeoutInMillis)` returns false on contention; `waitLock(timeoutInMillis)` throws instead. Use `try/finally` so an exception in the body still releases.
- **A lock is not a substitute for idempotency.** Locks serialize concurrent runs; they do nothing about a re-run after a 6-minute timeout (§2). You need both — lock the write, and make the operation safe to repeat.

---

## 5. `PropertiesService` for secrets (+ its size limits)

This is the GAS form of the *Secrets Management* floor — API keys and tokens are **never** literals in the source.

- **Three stores, by scope:** **Script** (`getScriptProperties()`) — shared by all users of the script, the place for a service API key; **User** (`getUserProperties()`) — scoped to the current user, for per-user tokens; **Document** (`getDocumentProperties()`) — shared by users of the open document. Pick the narrowest store that fits.
- **Store the secret out-of-band, read it at runtime.** Set the value once (a one-off setup function or the Script Properties UI), then `PropertiesService.getScriptProperties().getProperty('API_KEY')` at use — and instruct the user to transfer the value from the correct 1Password vault, not paste it into chat or a committed file. **Never log the value** at any level.
- **Size limits (verify against live limits — current at writing):** 500 KB total per property store; 9 KB per individual value. Properties is a small key-value config/secret store, **not a database** — a script that stuffs accumulating state into one property will hit the 9 KB value ceiling or the 500 KB store ceiling and start throwing. For real data, use a Sheet or an external DB; for a large cache, `CacheService` (with its own TTL/size limits) over Properties.
- **`PropertiesService` is not encrypted-at-rest you control** — it's adequate for a personal-tool API key, but a high-value or multi-tenant secret belongs in a real secrets manager (Secret Manager via a service-account-backed call), not Script Properties. Match the store to the value's sensitivity.

---

## 6. Advanced Services vs. `UrlFetchApp`

Two ways to call a Google (or external) API — choose deliberately:

- **Advanced Services** (enabled in the manifest's `dependencies.enabledAdvancedServices`) give a typed, authenticated client for Google APIs (Drive, Calendar, Sheets API, Admin SDK, etc.) that rides the project's existing OAuth grant — no manual token handling, no hand-built requests. **Prefer them for Google APIs:** less code, correct auth, fewer ways to leak a token. Enabling one **adds its OAuth scope**, so it's a least-privilege decision (§3) — enable only what you use.
- **`UrlFetchApp`** is the raw HTTP client — the right tool for **external** APIs and for Google endpoints with no Advanced Service. When you use it: set explicit timeouts via the request options, wrap every call in `try/catch` (Coding Standards mandates this for all network calls), check `getResponseCode()` before trusting the body, **never** put a key in the URL or log the full request, and respect the daily call quota (§2). Treat every response as untrusted input — validate before acting on it, and sanitize before logging (log injection, CWE-117).

---

## 7. Structured logging — `console.log` → Cloud Logging

Apps Script's `console.log`/`console.error` route to **Google Cloud Logging** (the executions/logs view; the old `Logger.log` only survives a single execution and isn't queryable) — that's the GAS surface of the skill's structured-logging discipline.

- **Use `console` (Cloud Logging), not `Logger`,** for anything you'll need after the run — it's persisted, queryable, and severity-tagged (`console.error` vs `console.log`).
- **Log structured, machine-parseable events** — a short message plus fields (the row id, the trigger name, a correlation id, `duration_ms`), not f-stringed prose — so the executions log is queryable, not grep-only. `console.log({event, sheetId, rows})` serializes the object.
- **Never log secrets, tokens, PII, or the fetched payload** at any level (cross-ref *Secrets Management* + *Structured Logging*). **Sanitize externally-influenced values** (a cell value, a form field, a fetched string) before logging — strip CR/LF/control chars (CWE-117).
- **Surface trigger failures explicitly** (§2) — a time-driven trigger that throws is invisible unless you alert. Catch, log the structured error, and emit a notification (an email/webhook) on failure; pair it with a freshness/dead-man's-switch check so a trigger that *stops firing* (quota-exhausted, disabled) is itself caught.

---

## 8. Testing — isolate pure logic from `SpreadsheetApp`/Gmail (mirror `testing.md`)

The core GAS testing problem: `SpreadsheetApp`, `GmailApp`, `DriveApp`, `UrlFetchApp` only exist inside the Apps Script runtime, so code that calls them directly is **untestable** off-platform. The fix is the same separation `testing.md` §1 demands — **unit tests do no I/O**:

- **Split the script into two layers.** Thin **adapter** functions touch the Google services (read the range, send the mail, fetch the URL) and do nothing else; **pure** functions take plain data in and return plain data out (parse a row, compute the summary, build the email body, decide an action). All the real logic lives in the pure layer.
  ```javascript
  // adapter — does I/O, stays trivial (not unit-tested off-platform)
  function runDailyReport() {
    const rows = SpreadsheetApp.getActiveSheet().getDataRange().getValues();
    const summary = buildSummary(rows);            // pure
    GmailApp.sendEmail(recipient, summary.subject, summary.body);
  }
  // pure — plain data in/out, fully unit-testable
  function buildSummary(rows) { /* no SpreadsheetApp/GmailApp here */ }
  ```
- **`clasp` makes the pure layer real-testable.** With the logic in committed `.js` files (§1), run the pure functions under a normal JS test runner (e.g. `jest`/`vitest`) in CI — no Google runtime needed. Assert invariants on parsers and formatters the way `testing.md` §6 drives parsers with generated input.
- **For the adapter layer, inject the service** rather than reaching for the global — pass a client object so a test can supply a fake (`{sendEmail: () => {...}}`), exactly as `testing.md` DIs a fake model client. A handful of GAS-side smoke tests (a `test_*` function run in the editor with simple asserts) covers the thin adapter; the heavy assertions live in the off-platform pure-logic suite.
- **The bugfix rule is unchanged** (SKILL.md / `testing.md` §3b): a fix lands with a regression test seen to FAIL on the pre-fix pure function, then pass. Test names state the behavior (`test_buildSummary_skips_blank_rows`), not the input.
