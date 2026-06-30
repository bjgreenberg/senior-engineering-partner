# Systematic Debugging (root cause, not symptom)

Companion reference for the senior-engineering-partner skill — the method behind `DEBUG:` mode.

> **Rigor tier:** this method holds at every tier. Depth scales — a Tier-0 spike may stop at "reproduced and fixed"; a Tier-2 incident adds a regression test, a blameless postmortem, and (for a tenant-boundary suspicion) the SEV1 path in `observability-and-incident-response.md`.

Debugging is where the *deterministic-first* and *verify-before-asserting* disciplines earn their keep. The dangerous failure mode is **guess-and-check**: changing a plausible-looking line, seeing the symptom move, and declaring victory — having actually masked the bug or introduced a second one. A senior engineer narrows the search space deliberately and fixes the *cause*. Resist the urge to patch the symptom; an unexplained green is not a fix, it's a deferred recurrence.

**The cardinal rule: do not change code until you can explain the bug.** A fix you can't explain is a guess, and a guess that works once will fail differently later.

---

## The four phases

### 1. Reproduce — make the bug happen on demand

You cannot fix what you cannot reproduce, and you cannot prove a fix against a bug you can't trigger.

- **Get a deterministic, minimal repro.** Pin the exact inputs, environment, and steps. Where the bug is data-shaped (a parser, a regex, a transform), capture the offending input and write a *script* that triggers it (the *deterministic-first* rule) — that script becomes the RED regression test in phase 4. Strip the repro down to the smallest case that still fails; the noise you remove is search space eliminated.
- **If it's intermittent, find what varies.** Flaky ≠ random — something differs between the passing and failing runs (timing, ordering, a shared resource, an unseeded clock/RNG, test pollution). Make the variable explicit before chasing the symptom. Never "retry to green" (`testing.md` zero-tolerance flaky policy) — a quarantined flaky test is an open bug, not a closed one.
- **Quote the actual error.** The real stack trace / log line / exit code, observed this run — not a remembered or paraphrased one. The believable-but-wrong recollection sends you down the wrong path (the *cite uncertainty honestly* rule).
- **When an error names a symbol you *know* is defined, suspect the bytes.** A bash `unbound variable` on a variable you clearly set (under `set -u`), an "undefined name" on a correct identifier — look for a smuggled **non-ASCII character**: a "smart" quote, em-dash, or ellipsis pasted into source. Adjacent to a `$var` (e.g. `"$attr…"`) its leading UTF-8 byte can fold into the variable name and produce a baffling error about a name that *looks* right. `cat -v` / `hexdump -C` / `LC_ALL=C grep -nP '[^\x00-\x7f]'` reveals it. Keep shell scripts ASCII; reach for the encoding explanation when the symbol on screen is unimpeachable but the interpreter disagrees.

### 2. Hypothesize — form one falsifiable explanation at a time

- **State a specific, testable hypothesis.** "The tenant id is null because the resolver runs before the session GUC is set" — something a single observation can confirm or kill. Not "something's wrong with auth."
- **Predict what you'd see if it were true,** then go look. Reading the relevant code and the actual runtime state (logs, a debugger, a targeted print) beats theorizing — *verify before asserting* applies to your own hunches.
- **One variable at a time.** Changing several things at once destroys the signal: when the symptom moves you won't know which change did it, and you may have introduced a new bug while masking the old.

### 3. Isolate — bisect the search space

- **Halve the problem repeatedly.** Is the bad value already wrong when it enters this function, or does this function corrupt it? Each answer eliminates half the code path. Binary search beats linear scanning.
- **Use the tools that collapse the space:** `git bisect` to find the introducing commit (then read *that* diff — the bug is usually in it); a debugger/breakpoint or a logged correlation id (`observability-and-incident-response.md`) to watch state flow; comment-out / feature-flag to confirm which layer owns the fault.
- **Check your assumptions explicitly.** The bug is most often in the thing you were *sure* was correct — the "obviously fine" config, the library you trust, the value you "know" is set. Verify it rather than skipping past it.

### 4. Fix the root cause — and prove it

**Descend the iceberg: event → pattern → structure.** The symptom is the *event*; ask what *pattern* recurs and what *structure* (a default, a missing constraint, an unguarded resolver) produces it. The highest-leverage fix changes the structure, not the visible event — a structural fix retires a whole class of events; a symptom patch buys one quiet recurrence.

**Match the method to the bug's nature** (Cynefin): a clear/complicated bug — known mechanism, reproducible — yields to *analyze and bisect* (§3); a novel or irreproducible one is *probe-sense-respond* — run small safe experiments to surface the pattern before theorizing; an active incident is *act-to-stabilize-first* — mitigate (roll back / flip the flag — `observability-and-incident-response.md`) before you root-cause. *Read [the Cynefin framework](https://en.wikipedia.org/wiki/Cynefin_framework) for the full domains.*

- **Fix the cause, not the symptom.** A null check that hides a value that should never have been null is a symptom patch — it converts a loud crash into a silent wrong-result, which is worse (SKILL.md *never fail silently*). Ask "why did this value get here?" until you reach the actual origin.
- **Regression test, red first.** Write (or promote the phase-1 repro into) a test that **fails before the fix and passes after** — seen failing red, exactly as in iron-law TDD (`engineering-workflow.md` §3). A bugfix without a failing-first test is the *per-change-class merge contract* violation in `testing.md`: nothing stops the bug returning.
- **Confirm against the original repro,** then sweep for siblings — the same root cause often manifests in more than one place (the same unguarded resolver, the same missing `WITH CHECK`). Fix them together.
- **Explain it in the commit/PR.** Root cause → fix → the test that proves it. For a Tier-2 incident, that explanation seeds the blameless postmortem; a suspected tenant-boundary breach is SEV1 on sight with the 72h clock (`observability-and-incident-response.md`, `data-protection.md`).

---

## Anti-patterns (the guess-and-check tells)

- **Changing code before explaining the bug** — the cardinal-rule violation; everything else follows from it.
- **Shotgun debugging** — changing several things at once "to see what happens." You lose the signal and risk stacking a new bug on the old.
- **Symptom suppression** — a `try/except: pass`, a broad null-guard, a retry, a bumped timeout that makes the symptom disappear without explaining it. The bug is still there, now quieter.
- **Trusting the remembered error** over the one in front of you — re-run and read the real output.
- **Declaring victory without a red-first regression test** — if you can't make it fail on demand, you can't prove you fixed it, and you can't stop it returning.

---

## Naming the structure (the anti-patterns above, as systems archetypes)

The tells above are recurring *system archetypes* (Senge, *The Fifth Discipline*). Naming the one you're in tells you the fix is structural, not local:

| Archetype | The anti-pattern it names | Where in this skill |
|---|---|---|
| **Shifting the Burden** | retry-to-green / quarantine-not-fix — the symptomatic relief that atrophies the real fix | §1 flaky policy; `testing.md` zero-tolerance |
| **Fixes that Fail** | the symptom null-check that converts a loud crash into a silent wrong-result | §4 *fix the cause, not the symptom* |
| **Limits to Growth** | a scaling ceiling — adding load stops helping past a constraint | `scalability-and-system-design.md` §3 |
| **Tragedy of the Commons** | a shared pool / noisy-neighbour exhausting a common resource | bulkhead — `resilience-engineering.md` §2 |
| **Eroding Goals** | flaky/debt tolerance creep — the bar quietly lowered to keep merging | §1; `engineering-workflow.md` *don't relax the floor* |

*Source: Senge, [system archetypes](https://en.wikipedia.org/wiki/System_archetype) — verify the canonical names against the source before citing in prose.*

---

## Profile before you optimize

Performance debugging is the same method as correctness debugging — measure, don't guess. The guess-and-check tell here is **optimizing on a hunch**: rewriting the loop you *assume* is slow, seeing no change, and having burned effort on code that wasn't the bottleneck. **Make it correct, then make it fast** — never trade a passing test for speed; a fast wrong answer is still wrong (SKILL.md *never fail silently*).

- **Measure the hot path first.** Profile before touching code: `python -m cProfile -s cumulative myscript.py` (deterministic, function-level, in-process) or sample a *running* process with `py-spy top --pid <pid>` / `py-spy record -o profile.svg --pid <pid>` (no code change, works on prod) — *verify invocation against current docs*. The bottleneck is reliably *not* where you'd have guessed.
- **Read the flame graph.** Width = total time spent in a frame (self + callees); a wide bar is where the time goes. Hunt the widest box, not the deepest stack — depth is call nesting, not cost.
- **Memory growth → `tracemalloc`.** `start()`, then `take_snapshot()` before and after the suspect work and `snapshot2.compare_to(snapshot1, 'lineno')` — the top `size_diff` lines are where allocation accumulates. This is the leak-hunt analogue of bisecting the search space.
- **DB hot path → `EXPLAIN ANALYZE`.** Read *actual* vs. estimated rows and the chosen plan before adding an index or rewriting the query (`databases.md` §indexes-by-EXPLAIN-ANALYZE; the queue/latency-budget framing is in `scalability-and-system-design.md`).
- **Baseline → target → re-measure.** Write down the current number and the goal (p95 latency or throughput) *before* changing code, then re-run the same measurement after to prove the win. An optimization you can't show in the profile is a guess — back it out.
