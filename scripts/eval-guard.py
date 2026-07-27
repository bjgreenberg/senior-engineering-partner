#!/usr/bin/env python3
"""eval-guard.py — a rule change to SKILL.md must ship a guarding eval, or say why not.

The self-improvement loop (references/skill-self-improvement.md) requires that a new or
sharpened rule arrive with a guarding eval scenario, but until this gate that arrival was
post-hoc (the agentic-AI rules of v1.22.0 got their scenarios weeks later, in #108). This
mechanizes the contract at the PR boundary:

  PASS when any of:
    - SKILL.md is not in the diff;
    - the diff also touches evals/scenarios/ (a guarding eval rides along);
    - the SKILL.md changes are metadata-only (the release-please Version row, the
      Last-updated row, whitespace) — release PRs must not need waivers;
    - the PR body carries an explicit waiver line:  Eval-waiver: <reason>
      (an auditable decision, same posture as a dismissed review finding).
  FAIL otherwise, naming the contract and the two ways to satisfy it.

Inputs (all optional): $BASE_REF (default origin/main), $HEAD_REF (default HEAD) — the
diff range is BASE_REF...HEAD_REF; $PR_BODY — the pull-request body to scan for a waiver.
Stdlib-only; CI and a local run are byte-identical:
  BASE_REF=origin/main PR_BODY="$(gh pr view --json body -q .body)" scripts/eval-guard.py
Exit 0 = pass, 1 = fail, 2 = git plumbing error.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

METADATA_LINE_RE = re.compile(
    r"^[+-](\s*$"                                  # blank / whitespace-only
    r"|\|\s*\*\*(Version|Last updated)\*\*\s*\|)"  # the two metadata table rows
)
WAIVER_RE = re.compile(r"^eval-waiver:\s*\S", re.IGNORECASE | re.MULTILINE)


def git(*args: str) -> str:
    """Run a git command and return stdout; exit 2 on plumbing failure."""
    proc = subprocess.run(
        ["git", *args], capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        print(f"FAIL: git {' '.join(args)}: {proc.stderr.strip()}", file=sys.stderr)
        sys.exit(2)
    return proc.stdout


def main() -> int:
    base = os.environ.get("BASE_REF", "origin/main")
    head = os.environ.get("HEAD_REF", "HEAD")
    rng = f"{base}...{head}"

    changed = set(git("diff", "--name-only", rng).splitlines())
    if "SKILL.md" not in changed:
        print(f"PASS: eval-guard — SKILL.md untouched in {rng}")
        return 0
    if any(f.startswith("evals/scenarios/") for f in changed):
        print("PASS: eval-guard — SKILL.md change ships with an evals/scenarios/ change")
        return 0

    diff_lines = git("diff", "-U0", rng, "--", "SKILL.md").splitlines()
    substantive = [
        line
        for line in diff_lines
        if (line.startswith("+") or line.startswith("-"))
        and not line.startswith(("+++", "---"))
        and not METADATA_LINE_RE.match(line)
    ]
    if not substantive:
        print("PASS: eval-guard — SKILL.md changes are metadata-only (version/date rows)")
        return 0

    if WAIVER_RE.search(os.environ.get("PR_BODY", "")):
        print(
            "PASS: eval-guard — explicit Eval-waiver present in the PR body"
            f" ({len(substantive)} substantive SKILL.md line(s) waived)"
        )
        return 0

    print(
        f"FAIL: eval-guard — {len(substantive)} substantive SKILL.md line(s) changed with"
        " no evals/scenarios/ change. A rule change must ship its guarding eval"
        " (references/skill-self-improvement.md), or the PR body must carry an explicit"
        " 'Eval-waiver: <reason>' line.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
