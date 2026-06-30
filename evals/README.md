# Evals for senior-engineering-partner

Last updated: 2026-06-29 07:21 PM CDT

A regression suite for the skill itself. Each scenario encodes a **real miss** the skill exists to
prevent — most are drawn straight from the SKILL.md changelog — so the suite is the executable form of
"this must never happen again." Anthropic's own most-emphasized authoring practice is *build evaluations
first*; this brings the skill into line with it (the changelog was the spec; these are the tests).

## Why this exists

The changelog is a list of lessons in prose. Prose doesn't fail a build. An eval scenario is the same
lesson as a **checkable expectation**: run the query against a fresh Claude with the skill loaded, and
confirm the `expected_behavior` holds. When a future skill edit (or a model change) regresses a discipline,
the matching scenario catches it instead of a production incident re-teaching the lesson.

## Structure

`scenarios/*.json` — one scenario per file, in Anthropic's evaluation shape:

```json
{
  "skills": ["senior-engineering-partner"],
  "query": "the user prompt to run",
  "files": [],
  "expected_behavior": [
    "an observable, checkable thing the response must do",
    "..."
  ],
  "anti_behavior": ["things the response must NOT do"],
  "source": "changelog vX.Y / discipline it guards"
}
```

`anti_behavior` and `source` are local extensions (Anthropic's base shape is `skills`/`query`/`files`/
`expected_behavior`); they make the "never do this again" framing explicit and trace each scenario to its
origin.

> **Note on the `source` version tokens.** Some `source` fields cite internal pre-release revisions
> (e.g. `v4.0`, `v5.4`) that predate the public `v1.0.0` release and intentionally do **not** appear in
> the SKILL.md changelog — treat them as provenance notes, not resolvable versions.

## How to run (no built-in runner exists)

There is no first-party eval runner today, so run them as a structured manual/LLM-judge loop:

1. **Baseline first.** Run each `query` against a fresh Claude **without** the skill. Record what it misses —
   that gap is what the skill must close. (Anthropic: measure baseline before writing/justifying content.)
2. **With the skill.** Run the same `query` with the skill loaded. Check the response against every
   `expected_behavior` and confirm no `anti_behavior` appears. Score pass/partial/fail.
3. **Iterate (Claude-A / Claude-B).** When a scenario fails or a real new miss appears: bring the specifics
   back to the skill (Claude-A), strengthen the relevant rule/reference, add or sharpen the scenario, re-run.
   This is the observe→refine→test loop from Anthropic's best-practices guide.
4. **Test across models** you actually use (Opus / Sonnet / Haiku) — a rule that's obvious to Opus may need
   to be more prominent for a smaller model.

A thin scorer (feed `query` + response + `expected_behavior` to an LLM judge returning pass/fail+reason) is a
reasonable future addition; keep the JSON shape stable so it stays machine-runnable.

## Maintenance

**Every new changelog entry written from a real miss should add (or extend) a scenario here, in the same
spirit as the same-commit docs rule.** A lesson without a guarding eval is a lesson that can silently
regress. Keep ≥3 scenarios per major discipline as coverage grows.
