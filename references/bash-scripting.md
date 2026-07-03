# Bash Scripting — robustness, portability & testing

Companion reference for the senior-engineering-partner skill.

**Scope:** the deep discipline behind SKILL.md's Bash floor. The floor itself lives there and
is not repeated: strict error handling, quote every expansion, ShellCheck-clean, and the
injection-prevention rules (SKILL.md *Strict Security Protocols*).
This file is what a *senior* Bash author knows beyond the floor: where strict mode lies to
you, how to clean up reliably, what stock-shell portability actually requires, and how to
test shell code. Logging/rotation mechanics stay in `logging-and-monitoring.md`; the
per-language harness assignment (BATS for Bash) is SKILL.md *Automated QA & Testing*.

---

## 1. When Bash — and when not

Bash is the right tool for **orchestration**: gluing commands, pipelines, environment setup,
small deterministic checks (the five-line `grep -c`/`jq` scripts the deterministic-first rule
reaches for), CI gate wrappers, and install/bootstrap glue. It is the wrong tool the moment
the *logic* outgrows the glue. Rewrite triggers — any one is enough:

- You need real data structures (nested records, maps of lists), not lines of text.
- Error handling needs a taxonomy (retryable vs fatal vs partial), not just exit codes.
- The script needs unit tests of *business logic*, not just end-to-end runs.
- You're parsing JSON/CSV/XML with `sed`/`awk` regexes — hand that to `jq` first, and to
  Python when `jq` stops being enough.
- It passes ~200 lines of non-glue logic, or a second contributor joins.

The move is the single-file-Python pattern (`python-typing-and-packaging.md`), not a bigger
Bash file. Conversely: don't write 80 lines of Python `subprocess` plumbing to do what a
12-line pipeline does — that's the same mismatch in reverse.

## 2. Strict mode is a seatbelt, not a try/catch

`set -euo pipefail` is mandatory (the floor) — but knowing where `-e` **does not fire** is
what separates working scripts from scripts that only look safe:

- **`-e` is suspended in condition contexts.** Inside `if cmd`, `while cmd`, `cmd && x`,
  `cmd || x`, and any function *called from* one of those, a non-zero exit does not abort —
  the entire function body runs with `-e` effectively off. Don't bury must-not-fail work in
  a function that's ever called from a condition; check its exit explicitly. (ShellCheck
  flags this only as optional SC2310/SC2311 under `--enable=all`.)
- **`local`/`declare`/`export` masks command-substitution failure.** In
  `local out=$(cmd)`, the exit status of `local` (0) wins and `cmd`'s failure vanishes —
  under `set -e`, silently (ShellCheck SC2155). Declare and assign in two steps:
  `local out; out=$(cmd)`.
- **`pipefail` tells you *that* a pipeline failed, not *which* stage** — read
  `"${PIPESTATUS[@]}"` (bash) immediately after when the stage matters. And a pipe into a
  consumer that exits early (`… | head -1`) can make the producer die of SIGPIPE — a
  pipeline that is *correct* can still trip `pipefail`. Tolerate it explicitly
  (`cmd | head -1 || [ "${PIPESTATUS[0]}" -eq 141 ]`) or restructure so the consumer reads
  everything (`awk 'NR==1'`).
- **`set -u` + optional inputs:** expand optionals as `${VAR:-}`/`${VAR:-default}`
  deliberately, not by turning `-u` off. An empty `"$@"` is safe under `-u` on current bash
  *and* on stock 3.2.57 (verified) — but some pre-4.4 releases errored on it; `${1+"$@"}`
  spans them if you must. Quote them anyway (the floor).
- **An unmatched glob passes through as the literal pattern** — `for f in *.log` with no
  logs iterates once over the string `*.log`; neither strict mode nor ShellCheck catches it.
  `shopt -s nullglob` (empty loop) or `failglob` (hard error) — choose one deliberately.
- **Failure must be loud** (SKILL.md *fail closed*): `die() { printf '%s\n' "$*" >&2; exit 1; }`
  and use it — an error message on stderr plus a non-zero exit is the script's contract with
  its caller and its monitor.

## 3. Cleanup, temp files & atomic output

- **One `trap cleanup EXIT` near the top,** after defining `cleanup()`. On bash, `EXIT`
  fires on normal end, on `-e` aborts, *and* on fatal INT/TERM — it is the `finally` block.
  **Never add a bare `trap cleanup INT TERM` on top of it:** the handler *returns*, the
  script keeps running past the kill, and it exits 0 — a killed job reporting success. If
  callers must see death-by-signal, re-raise — `trap 'trap - TERM; kill -TERM $$' TERM` —
  and let `EXIT` do the cleanup. Nothing fires on SIGKILL or power loss. Create scratch with
  `mktemp -d`, store the path in a variable `cleanup` removes, and never write scratch into
  the source tree or a shared `/tmp` name.
- **Never leave a half-written artifact.** Write to a temp file *in the destination's
  directory*, then `mv -f tmp final` — `mv` within a filesystem is atomic: a reader (or a
  crashed re-run) sees the old file or the new one, never a torn one. (Atomic against a
  crashed *process*, not power loss — rename doesn't flush file data.) This is also what
  makes re-runs idempotent (SKILL.md *Reliability for Automation*).
- **Single-instance scripts take a lock.** `flock` on Linux; stock macOS has no `flock`
  binary — the portable idiom is `mkdir "$lockdir"` (atomic create-or-fail) with the removal
  in `cleanup` — knowing its residual: a SIGKILL'd holder never runs `cleanup`, and the
  stale dir then blocks every later run. Write `$$` into the lockdir and treat a dead-PID
  lock as stale, or at minimum alert on repeated skips. A cron/launchd job that can overlap
  itself *will* eventually overlap itself.

## 4. Robust command execution

- **Preflight the dependencies:** `command -v jq >/dev/null 2>&1 || die "jq required"` for
  every non-POSIX tool, up front, before any work happens — and document them at the top of
  the script (the Bash dependency rule in SKILL.md *Dependency Management*).
- **`curl` exits 0 on an HTTP 500.** Without `-f`/`--fail` a failed request "succeeds" and
  the error page lands in your output file — the classic silent corruption. House pattern:
  `curl -fsSL --max-time <n> --retry <k> --retry-all-errors -o tmp && mv tmp final` —
  fail on HTTP errors, bound the hang, retry only when the operation is idempotent
  (`resilience-engineering.md`), download to temp, rename into place.
  (`--retry-all-errors` needs curl 7.71+ — on an older build drop it and bare `--retry`
  covers only transient errors; the §5 rule applies to curl versions too.)
- **Give every network/long command a timeout** — `curl --max-time`, `timeout <secs> cmd`
  where available — an automation script with an unbounded hang is a stuck LaunchAgent/cron
  slot that alerts no one (its dead-man's-switch never fires because it never *stops*).
- **stdout is the script's API; stderr is its diary.** Diagnostics, progress, and warnings go
  to stderr so the caller can pipe stdout clean; anything a downstream pipe consumes is
  stdout. Mixing them makes a script unusable in the pipelines Bash exists for.

## 5. Portability — the stock-shell floor

The bash you develop on is not the bash the script runs on:

- **Stock macOS `/bin/bash` is 3.2** (frozen at GPLv2, since 2007). Anything from bash 4+ —
  `mapfile`/`readarray`, associative arrays (`declare -A`), `${var,,}`/`${var^^}`,
  `&>>` — dies on a stock Mac, in non-interactive SSH (where your interactive PATH's
  Homebrew bash isn't first), and in `sh`-invoked contexts. Portable array fill:
  `while IFS= read -r line; do arr+=("$line"); done < <(cmd)` — the `< <(cmd)` form matters:
  `cmd | while …` runs the loop in a pipeline subshell whose variable writes vanish. (A
  shipped gate script in this very repo once broke exactly this way on `mapfile` —
  works-on-my-shell is not portability.)
- **Declare the interpreter you actually need.** `#!/usr/bin/env bash` for bash scripts
  (never `#!/bin/sh` with bashisms); if the script must run on stock macOS, write to bash
  3.2 and say so in the header; if it genuinely needs 4+, preflight-check
  `BASH_VERSINFO` and fail with a clear message instead of a cryptic `command not found`.
- **GNU vs BSD userland:** `sed -i`, `date -d`, `grep -P`, `stat -c` differ or don't exist on
  macOS/BSD. For a cross-platform script, stick to POSIX flags, feature-detect, or require
  the GNU tool explicitly by name (`gsed`, `gdate`) — don't ship a script that works only on
  the userland you happened to write it on (`debugging.md` has the `grep -P` tell).
- ShellCheck catches most bashisms-in-`sh` automatically — but it does **not** version-check
  bash (`mapfile` under a bash shebang passes clean), so the 3.2 floor above stays on you.
  One more reason the zero-warning gate is the floor, not the ceiling.

## 6. Testing Bash — BATS, stubs & the source-guard pattern

Shell code gets tested like any other code (`testing.md` owns the general taxonomy; this is
the Bash mechanics):

- **Make functions testable by making the script sourceable.** End the script with the
  source guard — the Python `if __name__ == "__main__"` twin:

  ```bash
  main "$@"          # becomes:
  if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then main "$@"; fi
  ```

  A test can then `source script.sh` to load pure functions without executing `main`, the
  same isolate-logic-from-I/O move as everywhere else in this skill.
- **BATS** (`bats-core`) is the harness: each `@test` runs `run <fn-or-script>` and asserts
  on `$status` and `$output`; `setup()`/`teardown()` build and remove a per-test `mktemp -d`
  fixture dir. Name tests by expected behavior, same rule as pytest.
- **Stub external commands by PATH-prepending a fixture bin-dir** — a `stub/git` script that
  echoes its args and exits per the test's need beats mocking frameworks; assert afterwards
  on what the stub recorded. Never let a unit-level BATS test hit the network or the real
  `$HOME` (`dev-environment-isolation.md`).
- **Gate what a test can't reach.** ShellCheck-zero-warnings (documented
  `# shellcheck disable=SCnnnn` directives only, each with a justification — the `nosemgrep`
  rule), plus `bash -n` syntax-check in pre-commit for fast feedback. For fixture-style
  regression tests of shipped gate scripts, a tiny fixture tree + assertion script in CI is
  enough — the gate must be *able to fail* (`testing.md` §3c).

## Sources

- GNU Bash Reference Manual (gnu.org/software/bash/manual) — strict-mode semantics,
  `PIPESTATUS`, traps.
- ShellCheck wiki (shellcheck.net) — SC2155 and the per-rule rationale behind the gate.
- bats-core documentation (bats-core.readthedocs.io).
