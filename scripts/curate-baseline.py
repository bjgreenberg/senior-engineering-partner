#!/usr/bin/env python3
"""curate-baseline.py — slim a run-evals results dir into a committable baseline JSON.

Committed baselines keep statuses, per-item judgments, judge reasons, cost and duration —
and strip the bulky per-run payloads (`response`, `workspace_evidence`, `tool_trail`),
exactly the shape the 2026-07-05 baseline established. Re-run the sweep to regenerate the
full transcripts; the committed JSON is the record of verdicts, not of prose.

Splices (a scenario re-run after a harness error) are applied explicitly and must be
disclosed in the accompanying BASELINE.md: `--splice <scenario>=<results-dir>` replaces
that scenario's entry with the one from the given (re-run) results dir.

Usage:
  scripts/curate-baseline.py <results-dir> <out.json> [--splice name=dir ...]
Exit 0 on success; 1 on missing inputs or an unresolved error-status entry (a baseline
must not silently contain harness errors — re-run and splice, or investigate).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

STRIP_KEYS = ("response", "workspace_evidence", "tool_trail")


def load_results(results_dir: Path) -> list[dict]:
    summary = results_dir / "summary.json"
    if not summary.is_file():
        print(f"FAIL: {summary} not found", file=sys.stderr)
        sys.exit(1)
    return json.loads(summary.read_text())["results"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("results_dir", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument(
        "--splice",
        action="append",
        default=[],
        metavar="SCENARIO=RESULTS_DIR",
        help="replace SCENARIO's entry with the one from RESULTS_DIR (disclose in BASELINE.md)",
    )
    args = ap.parse_args()

    results = load_results(args.results_dir)
    by_name = {r["scenario"]: r for r in results}

    for spec in args.splice:
        name, _, src = spec.partition("=")
        if not src:
            print(f"FAIL: --splice needs SCENARIO=RESULTS_DIR, got {spec!r}", file=sys.stderr)
            return 1
        spliced = {r["scenario"]: r for r in load_results(Path(src))}
        if name not in spliced:
            print(f"FAIL: splice source {src} has no scenario {name!r}", file=sys.stderr)
            return 1
        if name not in by_name:
            print(f"FAIL: base run has no scenario {name!r} to splice over", file=sys.stderr)
            return 1
        by_name[name] = spliced[name]
        print(f"spliced: {name} <- {src}")

    slim = []
    for name in sorted(by_name):
        entry = {k: v for k, v in by_name[name].items() if k not in STRIP_KEYS}
        if entry.get("status") == "error":
            print(
                f"FAIL: {name} is status=error — a baseline must not contain harness"
                " errors; re-run it and --splice, or investigate",
                file=sys.stderr,
            )
            return 1
        slim.append(entry)

    tally: dict[str, int] = {"pass": 0, "partial": 0, "fail": 0, "error": 0}
    for entry in slim:
        tally[entry["status"]] = tally.get(entry["status"], 0) + 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"tally": tally, "results": slim}, indent=1) + "\n")
    print(f"PASS: {args.out} — {len(slim)} scenarios, tally {tally}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
