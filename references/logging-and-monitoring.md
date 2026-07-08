# Log Location, Rotation & Unattended-Job Monitoring

Companion reference for the senior-engineering-partner skill. The **rules** live in SKILL.md (*Structured Logging & Failure Alerting*); this file holds the implementation detail — the rotation code, the launchd open-fd gotcha, and the monitor design — kept out of the always-loaded core. Read it before writing a log-rotating script, a structured logger, or a monitor for any scheduled/unattended job. The rotation/monitor detail is macOS-centric (the proving ground is the `team-handbook` fleet health-monitor); the *Structured logging in Python* section below is cross-platform.

---

## Log location, rotation & retention (mandatory)

Every log a script or daemon writes **must** have a size/retention cap unless the user explicitly opts out — unbounded logs are a disk-exhaustion and log-noise liability.

- **Location (macOS).** Write logs to `~/Library/Logs/` — the idiomatic macOS location (Console.app reads it; keeps `$HOME` clean). Do not scatter logs in `$HOME` root or invent `~/logs` / XDG-style dirs. One flat file per tool (`~/Library/Logs/<tool>.log`); the plist `StandardOutPath`/`StandardErrorPath` and the script's `$LOG` must agree on that path. Corollary: keep the log path out of any **compiled** launcher — hardcoding it there means a recompile + re-sign + re-grant FDA just to move a file. Do logging in the script the launcher `exec`s, so paths stay editable.
- **Cap it — by size, not lines.** House default: **1 MB per log file**. Shell scripts truncate to the most recent bytes at the start of each run —
  ```bash
  readonly LOG_MAX_BYTES=$((1024 * 1024))   # 1 MB house default
  if [[ -f "$LOG" && $(wc -c < "$LOG") -gt "$LOG_MAX_BYTES" ]]; then
    tmp=$(mktemp) && tail -c "$LOG_MAX_BYTES" "$LOG" > "$tmp" && command mv -f "$tmp" "$LOG" || true
  fi
  ```
  (The `wc -c` guard skips the copy while under the cap; `wc -c`/`tail -c` are portable where `stat -f%z` vs `stat -c%s` are not; after a truncation the first line may be partial — cosmetic.) For long-lived Python processes, prefer `logging.handlers.RotatingFileHandler(maxBytes=1_048_576, backupCount=1)`.
  *Why bytes, not a line count:* both things the cap protects — disk and the incident-evidence window — are byte-denominated, and a line cap fails worst exactly when the log matters most: multi-line tracebacks burn a line-capped window fastest, so an incident evicts its own evidence. A 500-line cap is ~5 hours of history at a 15-minute polling cadence (less during a crash loop); 1 MB is weeks.
- **The launchd `StandardOutPath`/`StandardErrorPath` gotcha.** launchd holds an open fd to those files for the entire run, so a bare `mv` rotation leaves all subsequent writes going to the stale, unlinked inode (silently lost). Rotate at the very top, THEN rebind your own descriptors so they point at the fresh inode:
  ```bash
  cap_log "$LOG"            # size-guarded tail -c + mv, as above
  exec >> "$LOG" 2>&1       # abandons the stale launchd fd; writes hit the new inode
  ```
- **Permissions.** Create/keep logs `chmod 600` — they routinely capture hostnames, paths, package names, and occasionally tokens; never world-readable.
- **Don't rotate a file mid-write from two owners.** If launchd and the script both target the same file, use the rotate-then-`exec`-rebind sequence above; do not `mv`-rotate a launchd-held log from inside the run without rebinding.

## Structured logging in Python — the JSON + correlation-id mechanism

SKILL.md mandates JSON structured logs with a threaded correlation id; this is *how* you produce them in Python without f-stringing fields into an opaque string or passing the id through every function signature. The principle is portable; *verify current package names/APIs before pinning.*

- **Emit JSON, don't hand-format.** Use either **`structlog`** (processor pipeline, ergonomic context binding) or **stdlib `logging` + a JSON formatter** (`python-json-logger`'s `JsonFormatter`). Configure once via `logging.config.dictConfig`; application code just calls `logger.info("job.finished", extra={...})` (stdlib) or `log.info("job.finished", job_id=…)` (structlog). Don't reinvent a formatter.
- **Bind the correlation id with `contextvars`, not arguments.** Set the request/job id (and `tenant_id`) into a `ContextVar` (or `structlog.contextvars.bind_contextvars`) once at the API edge / job entry; a logging filter or structlog processor injects it into **every** subsequent line automatically. This is what makes "grep one id across the whole lifecycle" work without threading the id through every call. (Cross-ref the request→Job→model-call threading in `observability-and-incident-response.md`.)
- **Timestamps: UTC, ISO-8601 / RFC-3339.** Emit timezone-aware UTC timestamps (`datetime.now(timezone.utc).isoformat()`, or the formatter's ISO option) — never naive local-time strings. Cloud Logging stamps its own `timestamp`, but a portable JSON line (a `~/Library/Logs` file, a non-GCP sink) must carry an unambiguous one of its own.
- **Log exceptions with the traceback, scrubbed.** Use `logger.exception(...)` or `exc_info=True` so the stack trace is captured (Error Reporting groups on it) — never just `str(e)`, which discards the trace. But an exception's args/message can contain the very PII/secret the *Secrets Management* rule forbids; scrub or omit untrusted exception detail, and never return the trace to the client (cross-ref `compliance.md` A05/A10).
- **Sanitize external fields against log forging (CWE-117).** Log injection is the same never-trust-external-data rule as SQL/shell/prompt injection, applied to the log sink. JSON encoding neutralizes CR/LF and control characters structurally — which is a second reason to prefer it over plain-text lines. If a plain-text sink is unavoidable, strip/replace `\r`, `\n`, and other control chars in any externally-influenced value first. (SKILL.md *Structured Logging* states the rule; this is the implementation.)
- **Level is env-configurable (12-factor).** Read the level from `LOG_LEVEL` (default `INFO`); production never runs at `DEBUG`, and there should be **no code path that logs full prompts/responses/content even at DEBUG** — prefer to not have that path rather than gate it (cross-ref `observability-and-incident-response.md`).

### Other stacks (use the native structured logger, same posture)
- **Node/JS:** **`pino`** (fast, JSON-first) or `winston`; JSON to stdout, the same correlation-id-in-context discipline (`pino`'s child loggers / `AsyncLocalStorage`), never `console.log` for app logs in production.
- **Google Apps Script:** `console.log`/`console.error` route to the GCP project's **Cloud Logging** (Stackdriver) when the script is associated with a standard GCP project — prefer them over the legacy `Logger.log` (which only feeds the transient Executions view). Same no-secrets/no-PII rule; Apps Script has no rotation concern (managed), but watch quota.
- **Bash:** plain-text to `~/Library/Logs/<tool>.log` is fine for unattended scripts (JSON is overkill); still prefix each line with a UTC ISO-8601 timestamp and a level, and apply the rotation + `chmod 600` rules above.

## Monitoring & alerting for unattended automation

Any scheduled/unattended job (LaunchAgent, cron, daemon) needs a way to surface trouble — logs nobody reads are not monitoring. Prefer alerting **at the source** (the script already knows when it failed: non-zero exit, caught exception → emit a notification/exit code then). A periodic log-scanner is a **catch-all safety net**, not the primary mechanism. When you build one:

- **Track state — alert only on what's NEW.** Persist a per-log byte-offset or last-seen timestamp (local, un-synced). Re-scanning whole files re-alerts on the same old lines every run and trains the user to ignore it.
- **Allowlist known-benign noise (make-or-break).** Classify and suppress expected patterns (deprecation warnings, headless `LaunchServices` noise, etc.) so only new/real errors surface. A noisy alerter gets muted within a week and becomes worthless.
- **Summarize, don't itemize.** One digest ("job X: 1 error, 137 warnings since HH:MM"), not one notification per line.
- **Add a dead-man's-switch (freshness check).** The worst failures are silent — a job that stops running emits no error string at all. Check "did each job run on schedule?" (last-run timestamp vs. expected cadence); this catches what error-grepping cannot.
- **Be conservative about auto-remediation.** Default to detect → de-dupe → notify → write a rotating digest. Add targeted auto-actions only per specific, well-understood failure — never as a general "act on any error" capability.
- **Deliver durably.** macOS notifications are ephemeral; pair them with a persistent rotating digest log, and escalate genuinely critical events to email. The monitor must rotate its own log and never alert on its own output.
