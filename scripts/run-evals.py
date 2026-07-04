#!/usr/bin/env python3
"""run-evals.py — execute the evals/scenarios/*.json regression suite against a live model.

Each scenario's ``query`` is run headlessly through the ``claude`` CLI (``claude -p``),
then an LLM judge grades the response against the scenario's ``expected_behavior`` and
``anti_behavior`` lists. The overall verdict is computed deterministically in Python from
the per-item judgments (the judge grades items; it does not decide the verdict).

Two run modes:
  --mode with-skill   (default) inject the SKILL.md body via --append-system-prompt, with a
                      preamble pinning the skill's base directory so read-on-demand
                      references resolve. Explicit injection — not auto-activation — so the
                      suite tests the skill's *content* deterministically.
  --mode baseline     run the bare model (no injection). The Skill tool is disallowed in
                      BOTH modes so a user-level skill install cannot auto-activate and
                      contaminate either run.

A scenario may declare ``files``: workspace-relative paths materialized from
``evals/fixtures/<scenario>/`` into the scratch cwd before the run, so a scenario can
demand real edits against real code instead of grading a refusal to fabricate. Scenario
runs (both modes) are granted ``Bash,Edit,Write``; the judge gets no tool grants.

Requires: the ``claude`` CLI on PATH, authenticated. No API key and no third-party deps
(stdlib only) — the runner rides the existing CLI auth.

Usage examples:
  scripts/run-evals.py --filter spec-first-gate            # one scenario, quick check
  scripts/run-evals.py --mode baseline --model opus        # full baseline sweep
  scripts/run-evals.py --model opus --judge-model opus     # full with-skill sweep

Results land under evals/results/<UTC-stamp>-<mode>-<model>/ (git-ignored): one JSON per
scenario plus summary.md / summary.json. Curate a run worth keeping into evals/baselines/.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime
import difflib
import json
import logging
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, TypedDict

log = logging.getLogger("run-evals")

SKILL_DIR = Path(__file__).resolve().parent.parent
SCENARIOS_DIR = SKILL_DIR / "evals" / "scenarios"
RESULTS_DIR = SKILL_DIR / "evals" / "results"
FIXTURES_DIR = SKILL_DIR / "evals" / "fixtures"

# Tools granted to SCENARIO runs only (never the judge): a scenario whose expected_behavior
# demands real edits or a test seen to fail red needs Write/Edit/Bash — headless `claude -p`
# denies them by default, which made every act-on-the-workspace scenario grade as "described
# a plan, did nothing." The Skill tool stays disallowed in both modes regardless.
SCENARIO_ALLOWED_TOOLS = "Bash,Edit,Write"


class Scenario(TypedDict, total=False):
    """The scenario shape documented in evals/README.md."""

    skills: list[str]
    query: str
    files: list[str]
    expected_behavior: list[str]
    anti_behavior: list[str]
    source: str


class ItemJudgment(TypedDict, total=False):
    """One judged expected/anti behavior."""

    behavior: str
    verdict: str  # "pass" | "fail" | "unclear" (expected) / "violated" | "clean" (anti)
    evidence: str


class ScenarioResult(TypedDict, total=False):
    """Everything recorded for one scenario run."""

    scenario: str
    mode: str
    model: str
    judge_model: str
    status: str  # "pass" | "partial" | "fail" | "error"
    expected: list[ItemJudgment]
    anti: list[ItemJudgment]
    judge_reason: str
    response: str
    workspace_evidence: str
    duration_s: float
    cost_usd: float | None
    error: str


def build_skill_system_prompt() -> str:
    """SKILL.md body (frontmatter stripped) plus a base-dir preamble for the references."""
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"^---\n.*?\n---\n", text, re.DOTALL)
    body = text[match.end() :] if match else text
    preamble = (
        f"The following skill is ACTIVE for this session. Its base directory is "
        f"{SKILL_DIR} — when the skill says to read `references/<name>.md`, read "
        f"{SKILL_DIR}/references/<name>.md.\n\n"
    )
    return preamble + body


def run_claude(
    prompt: str,
    model: str,
    timeout: int,
    cwd: Path,
    system_prompt: str | None = None,
    allowed_tools: str | None = None,
) -> tuple[str, float | None]:
    """One headless claude run; returns (response_text, cost_usd). Raises on failure."""
    cmd = [
        "claude",
        "-p",
        prompt,
        "--model",
        model,
        "--output-format",
        "json",
        # Block skill loading in every run: with-skill injects the body itself, and the
        # baseline must not let a user-level install auto-activate.
        "--disallowedTools",
        "Skill",
    ]
    if allowed_tools is not None:
        cmd += ["--allowedTools", allowed_tools]
    if system_prompt is not None:
        cmd += ["--append-system-prompt", system_prompt]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd, check=False
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"claude exited {proc.returncode}: {proc.stderr.strip()[:500]}"
        )
    wrapper: dict[str, Any] = json.loads(proc.stdout)
    if wrapper.get("subtype") != "success":
        raise RuntimeError(f"claude result subtype={wrapper.get('subtype')}")
    return str(wrapper.get("result", "")), wrapper.get("total_cost_usd")


JUDGE_INSTRUCTIONS = """You are grading an AI assistant's response against a checklist. Be strict and literal:
grade only what the response actually does, not what it gestures at.

Return ONLY a JSON object (no markdown fence, no prose) with this exact shape:
{
  "expected": [{"behavior": "<verbatim item>", "verdict": "pass|fail|unclear", "evidence": "<short quote or note>"}, ...],
  "anti": [{"behavior": "<verbatim item>", "verdict": "violated|clean", "evidence": "<short quote or note>"}, ...],
  "reason": "<one-sentence overall summary>"
}
Include every expected_behavior and every anti_behavior item exactly once, in order."""


def materialize_files(name: str, files: list[str], workdir: Path) -> None:
    """Copy a scenario's fixture tree into the scratch workspace.

    Each ``files`` entry is a workspace-relative path, sourced from
    ``evals/fixtures/<scenario>/<path>`` — the JSON manifest documents the workspace
    layout and the fixture dir mirrors it. Fails loudly on an unsafe path, a missing
    fixture, or manifest/fixture-dir drift (a fixture file nobody lists, or a listed
    file that doesn't exist, would silently change what the scenario tests).
    """
    fixture_root = FIXTURES_DIR / name
    for rel in files:
        rel_path = Path(rel)
        if rel_path.is_absolute() or ".." in rel_path.parts:
            raise RuntimeError(f"unsafe fixture path {rel!r} in scenario {name}")
        src = fixture_root / rel_path
        if not src.is_file():
            raise RuntimeError(f"fixture missing for scenario {name}: {src}")
        dst = workdir / rel_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
    on_disk = {
        p.relative_to(fixture_root).as_posix()
        for p in fixture_root.rglob("*")
        # Finder drops .DS_Store uninvited; don't let it read as fixture drift.
        if p.is_file() and p.name != ".DS_Store"
    }
    if on_disk != set(files):
        raise RuntimeError(
            f"fixture drift for scenario {name}: on disk but unlisted "
            f"{sorted(on_disk - set(files))}, listed but missing {sorted(set(files) - on_disk)}"
        )


def collect_workspace_evidence(
    name: str, files: list[str], workdir: Path, limit_bytes: int = 60_000
) -> str:
    """Diff the post-run workspace against the fixtures so the judge grades real edits.

    A model granted tools does the work in the workspace and often doesn't restate it in
    prose — judging the response text alone under-credits exactly the scenarios the
    fixtures exist to sharpen (e.g. a behavior-stating test *name* that only exists in the
    written test file). Returns unified diffs for changed fixture files, full contents for
    new files, and a marker for deletions; bounded by ``limit_bytes``.
    """
    fixture_root = FIXTURES_DIR / name
    skip_dirs = {".git", "__pycache__", ".pytest_cache", "node_modules", ".venv"}
    parts: list[str] = []
    after = sorted(
        p
        for p in workdir.rglob("*")
        if p.is_file()
        and not any(seg in skip_dirs for seg in p.relative_to(workdir).parts)
        and p.name != ".DS_Store"
    )
    listed = set(files)
    for path in after:
        rel = path.relative_to(workdir).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            parts.append(f"### {rel}: binary or unreadable ({path.stat().st_size} bytes)")
            continue
        if rel in listed:
            before = (fixture_root / rel).read_text(encoding="utf-8")
            if text == before:
                continue
            parts.append(
                "".join(
                    difflib.unified_diff(
                        before.splitlines(keepends=True),
                        text.splitlines(keepends=True),
                        fromfile=f"a/{rel}",
                        tofile=f"b/{rel}",
                    )
                )
            )
        else:
            parts.append(f"### NEW FILE {rel}\n{text}")
    for rel in sorted(listed - {p.relative_to(workdir).as_posix() for p in after}):
        parts.append(f"### DELETED {rel}")
    evidence = "\n".join(parts)
    if not evidence:
        return "(no workspace changes — the assistant edited nothing)"
    if len(evidence) > limit_bytes:
        evidence = evidence[:limit_bytes] + "\n… (truncated at limit)"
    return evidence


def judge_response(
    scenario: Scenario,
    response: str,
    judge_model: str,
    timeout: int,
    cwd: Path,
    workspace_evidence: str | None = None,
) -> dict[str, Any]:
    """LLM-judge one response; returns the parsed judgment JSON."""
    workspace_section = ""
    if workspace_evidence is not None:
        workspace_section = (
            "\n\n## Workspace changes made by the assistant (harness-collected)\n"
            "Unified diffs vs the fixture files the assistant was given; new files shown in "
            "full. Treat these edits as actions the assistant actually performed, even where "
            "the prose response does not restate them.\n"
            f"<workspace_changes>\n{workspace_evidence}\n</workspace_changes>"
        )
    prompt = (
        f"{JUDGE_INSTRUCTIONS}\n\n"
        f"## The user's query\n{scenario['query']}\n\n"
        f"## expected_behavior checklist\n{json.dumps(scenario.get('expected_behavior', []), indent=1)}\n\n"
        f"## anti_behavior checklist\n{json.dumps(scenario.get('anti_behavior', []), indent=1)}"
        f"{workspace_section}\n\n"
        f"## The assistant's response to grade\n<response>\n{response}\n</response>"
    )
    raw, _cost = run_claude(prompt, judge_model, timeout, cwd)
    # Defensive extraction: the judge is told "JSON only," but don't trust it blindly.
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise RuntimeError(f"judge returned no JSON object: {raw[:300]}")
    parsed: dict[str, Any] = json.loads(match.group(0))
    return parsed


def overall_status(expected: list[ItemJudgment], anti: list[ItemJudgment]) -> str:
    """Deterministic verdict: any anti violation fails; all expected passing passes."""
    if any(item.get("verdict") == "violated" for item in anti):
        return "fail"
    verdicts = [item.get("verdict") for item in expected]
    if all(v == "pass" for v in verdicts):
        return "pass"
    if all(v == "fail" for v in verdicts):
        return "fail"
    return "partial"


def run_scenario(
    path: Path, mode: str, model: str, judge_model: str, timeout: int, system_prompt: str | None
) -> ScenarioResult:
    """Execute + judge one scenario file; never raises (errors land in the result)."""
    name = path.stem
    scenario: Scenario = json.loads(path.read_text(encoding="utf-8"))
    started = datetime.datetime.now(datetime.timezone.utc)
    result: ScenarioResult = {
        "scenario": name,
        "mode": mode,
        "model": model,
        "judge_model": judge_model,
        "status": "error",
    }
    try:
        with tempfile.TemporaryDirectory(prefix=f"eval-{name}-") as tmp:
            workdir = Path(tmp)
            if scenario.get("files"):
                materialize_files(name, scenario["files"], workdir)
            response, cost = run_claude(
                scenario["query"], model, timeout, workdir, system_prompt,
                allowed_tools=SCENARIO_ALLOWED_TOOLS,
            )
            # Every scenario gets workspace evidence — a tool-granted model can act in an
            # empty workspace too, and "edited nothing" is itself gradeable information.
            evidence = collect_workspace_evidence(
                name, list(scenario.get("files", [])), workdir
            )
            judgment = judge_response(
                scenario, response, judge_model, timeout, workdir, evidence
            )
        expected = list(judgment.get("expected", []))
        anti = list(judgment.get("anti", []))
        result.update(
            status=overall_status(expected, anti),
            expected=expected,
            anti=anti,
            judge_reason=str(judgment.get("reason", "")),
            response=response,
            cost_usd=cost,
            workspace_evidence=evidence,
        )
    except (RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        log.error("[%s] %s", name, result["error"])
    result["duration_s"] = round(
        (datetime.datetime.now(datetime.timezone.utc) - started).total_seconds(), 1
    )
    log.info("[%s] %s (%.0fs)", name, result["status"], result["duration_s"])
    return result


def write_summary(out_dir: Path, results: list[ScenarioResult]) -> str:
    """Write summary.json + summary.md; returns the one-line tally."""
    tally = {s: sum(1 for r in results if r["status"] == s) for s in ("pass", "partial", "fail", "error")}
    line = " · ".join(f"{k}: {v}" for k, v in tally.items())
    (out_dir / "summary.json").write_text(
        json.dumps({"tally": tally, "results": results}, indent=1), encoding="utf-8"
    )
    rows = "\n".join(
        f"| {r['scenario']} | {r['status']} | {r.get('judge_reason') or r.get('error', '')} |"
        for r in sorted(results, key=lambda r: r["scenario"])
    )
    (out_dir / "summary.md").write_text(
        f"# Eval run — {out_dir.name}\n\n**{line}**\n\n"
        f"| Scenario | Status | Reason |\n|---|---|---|\n{rows}\n",
        encoding="utf-8",
    )
    return line


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mode", choices=["with-skill", "baseline"], default="with-skill")
    parser.add_argument("--model", default="opus", help="model for the scenario runs")
    parser.add_argument("--judge-model", default="opus", help="model for the judge runs")
    parser.add_argument("--filter", default="", help="substring filter on scenario filenames")
    parser.add_argument("--jobs", type=int, default=2, help="concurrent scenarios")
    parser.add_argument("--timeout", type=int, default=600, help="seconds per claude run")
    parser.add_argument("--out", default="", help="output dir (default: evals/results/<stamp>)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s", stream=sys.stderr)

    paths = sorted(p for p in SCENARIOS_DIR.glob("*.json") if args.filter in p.name)
    if not paths:
        log.error("no scenarios match filter %r under %s", args.filter, SCENARIOS_DIR)
        return 2
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out) if args.out else RESULTS_DIR / f"{stamp}-{args.mode}-{args.model}"
    out_dir.mkdir(parents=True, exist_ok=True)
    system_prompt = build_skill_system_prompt() if args.mode == "with-skill" else None
    log.info("%d scenario(s) → %s (mode=%s model=%s judge=%s jobs=%d)",
             len(paths), out_dir, args.mode, args.model, args.judge_model, args.jobs)

    results: list[ScenarioResult] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {
            pool.submit(run_scenario, p, args.mode, args.model, args.judge_model,
                        args.timeout, system_prompt): p
            for p in paths
        }
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            # Checkpoint per scenario so an interrupted sweep loses nothing.
            (out_dir / f"{result['scenario']}.json").write_text(
                json.dumps(result, indent=1), encoding="utf-8"
            )

    line = write_summary(out_dir, results)
    log.info("done: %s", line)
    print(f"{line}\nresults: {out_dir}")
    return 0 if all(r["status"] == "pass" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
