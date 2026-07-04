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

Requires: the ``claude`` CLI on PATH, authenticated. No API key and no third-party deps
(stdlib only) — the runner rides the existing CLI auth.

Scenario runner is pluggable; the judge is not. ``--runner claude`` (default) is the
fully-supported path above. ``--runner generic`` runs each scenario through any other
agent CLI via a ``--runner-cmd`` template ("{prompt}"/"{model}" placeholders, substituted
AFTER shell-style tokenization so a hostile prompt can never inject extra arguments), with
the response taken as the command's raw stdout. In with-skill mode the generic runner
materializes the SKILL.md body as ``--runner-instructions-file <name>`` (e.g. AGENTS.md
for Codex, GEMINI.md for Gemini CLI) in the scenario's scratch cwd — the instruction-file
mechanism those CLIs already read — since foreign CLIs have no --append-system-prompt.
The JUDGE always runs on the ``claude`` CLI regardless of runner, so verdicts stay
comparable across runners; a cross-CLI sweep still requires ``claude`` on PATH. Verify the
template against your installed CLI's --help before a sweep — flags drift across versions,
and this repo deliberately ships no hardcoded foreign-CLI flags it cannot test.

Usage examples:
  scripts/run-evals.py --filter spec-first-gate            # one scenario, quick check
  scripts/run-evals.py --mode baseline --model opus        # full baseline sweep
  scripts/run-evals.py --model opus --judge-model opus     # full with-skill sweep
  scripts/run-evals.py --runner generic \\
      --runner-cmd 'codex exec --model {model} {prompt}' \\
      --runner-instructions-file AGENTS.md                 # cross-CLI sweep (verify flags!)

Results land under evals/results/<UTC-stamp>-<mode>-<model>/ (git-ignored): one JSON per
scenario plus summary.md / summary.json. Curate a run worth keeping into evals/baselines/.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime
import json
import logging
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, TypedDict

log = logging.getLogger("run-evals")

SKILL_DIR = Path(__file__).resolve().parent.parent
SCENARIOS_DIR = SKILL_DIR / "evals" / "scenarios"
RESULTS_DIR = SKILL_DIR / "evals" / "results"


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


class RunnerSpec(TypedDict, total=False):
    """How scenario responses are produced. kind='claude' is the default first-class path;
    kind='generic' shells out to any agent CLI via cmd_template (see the module docstring)."""

    kind: str  # "claude" | "generic"
    cmd_template: str  # generic only: shell-style template with {prompt}/{model} placeholders
    instructions_file: str  # generic only: with-skill body lands here in the scenario cwd


class ScenarioResult(TypedDict, total=False):
    """Everything recorded for one scenario run."""

    scenario: str
    mode: str
    model: str
    runner: str
    judge_model: str
    status: str  # "pass" | "partial" | "fail" | "error"
    expected: list[ItemJudgment]
    anti: list[ItemJudgment]
    judge_reason: str
    response: str
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


def build_runner_cmd(template: str, prompt: str, model: str) -> list[str]:
    """Tokenize the --runner-cmd template shell-style, THEN substitute placeholders.

    Order matters for safety: because {prompt} lands inside an already-split argv token
    and the command runs without a shell, a prompt containing quotes, `;`, `$(...)`, or
    spaces stays one argument — it can never grow extra flags or commands (the same
    no-string-interpolation rule the skill's Bash injection discipline mandates)."""
    tokens = shlex.split(template)
    if not any("{prompt}" in t for t in tokens):
        raise ValueError("--runner-cmd template must contain a {prompt} placeholder")
    return [t.replace("{model}", model).replace("{prompt}", prompt) for t in tokens]


def run_generic(
    prompt: str, model: str, timeout: int, cwd: Path, cmd_template: str
) -> tuple[str, float | None]:
    """One headless run through a foreign agent CLI; response = raw stdout. No cost data —
    there is no cross-CLI cost envelope to parse, so cost_usd is honestly None."""
    cmd = build_runner_cmd(cmd_template, prompt, model)
    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd, check=False
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"{cmd[0]} exited {proc.returncode}: {proc.stderr.strip()[:500]}"
        )
    return proc.stdout.strip(), None


def run_scenario_prompt(
    runner: RunnerSpec,
    prompt: str,
    model: str,
    timeout: int,
    cwd: Path,
    system_prompt: str | None,
) -> tuple[str, float | None]:
    """Produce one scenario response via the selected runner.

    claude: system_prompt rides --append-system-prompt (unchanged legacy path).
    generic: system_prompt is materialized as the CLI's instruction file (AGENTS.md /
    GEMINI.md / ...) in the scenario's scratch cwd before the run — the mechanism those
    CLIs already read project guidance from. main() has already validated that with-skill
    + generic carries an instructions_file, so a missing one here is a programming error."""
    if runner.get("kind", "claude") == "claude":
        return run_claude(prompt, model, timeout, cwd, system_prompt)
    if system_prompt is not None:
        (cwd / runner["instructions_file"]).write_text(system_prompt, encoding="utf-8")
    return run_generic(prompt, model, timeout, cwd, runner["cmd_template"])


JUDGE_INSTRUCTIONS = """You are grading an AI assistant's response against a checklist. Be strict and literal:
grade only what the response actually does, not what it gestures at.

Return ONLY a JSON object (no markdown fence, no prose) with this exact shape:
{
  "expected": [{"behavior": "<verbatim item>", "verdict": "pass|fail|unclear", "evidence": "<short quote or note>"}, ...],
  "anti": [{"behavior": "<verbatim item>", "verdict": "violated|clean", "evidence": "<short quote or note>"}, ...],
  "reason": "<one-sentence overall summary>"
}
Include every expected_behavior and every anti_behavior item exactly once, in order."""


def judge_response(
    scenario: Scenario, response: str, judge_model: str, timeout: int, cwd: Path
) -> dict[str, Any]:
    """LLM-judge one response; returns the parsed judgment JSON."""
    prompt = (
        f"{JUDGE_INSTRUCTIONS}\n\n"
        f"## The user's query\n{scenario['query']}\n\n"
        f"## expected_behavior checklist\n{json.dumps(scenario.get('expected_behavior', []), indent=1)}\n\n"
        f"## anti_behavior checklist\n{json.dumps(scenario.get('anti_behavior', []), indent=1)}\n\n"
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
    path: Path,
    mode: str,
    model: str,
    judge_model: str,
    timeout: int,
    system_prompt: str | None,
    runner: RunnerSpec,
) -> ScenarioResult:
    """Execute + judge one scenario file; never raises (errors land in the result)."""
    name = path.stem
    scenario: Scenario = json.loads(path.read_text(encoding="utf-8"))
    started = datetime.datetime.now(datetime.timezone.utc)
    result: ScenarioResult = {
        "scenario": name,
        "mode": mode,
        "model": model,
        "runner": runner.get("kind", "claude"),
        "judge_model": judge_model,
        "status": "error",
    }
    try:
        if scenario.get("files"):
            # No scenario ships files today; fail loudly rather than half-support it.
            raise RuntimeError("scenario declares 'files' — materialization not implemented")
        with tempfile.TemporaryDirectory(prefix=f"eval-{name}-") as tmp:
            workdir = Path(tmp)
            response, cost = run_scenario_prompt(
                runner, scenario["query"], model, timeout, workdir, system_prompt
            )
            # The judge deliberately stays on the claude CLI for every runner, so
            # cross-runner verdicts are graded by the same instrument.
            judgment = judge_response(scenario, response, judge_model, timeout, workdir)
        expected = list(judgment.get("expected", []))
        anti = list(judgment.get("anti", []))
        result.update(
            status=overall_status(expected, anti),
            expected=expected,
            anti=anti,
            judge_reason=str(judgment.get("reason", "")),
            response=response,
            cost_usd=cost,
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
    parser.add_argument("--judge-model", default="opus", help="model for the judge runs (always the claude CLI)")
    parser.add_argument("--filter", default="", help="substring filter on scenario filenames")
    parser.add_argument("--jobs", type=int, default=2, help="concurrent scenarios")
    parser.add_argument("--timeout", type=int, default=600, help="seconds per claude run")
    parser.add_argument("--out", default="", help="output dir (default: evals/results/<stamp>)")
    parser.add_argument(
        "--runner", choices=["claude", "generic"], default="claude",
        help="scenario-response producer; the judge always runs on the claude CLI",
    )
    parser.add_argument(
        "--runner-cmd", default="",
        help="generic runner command template with {prompt} (required) and {model} "
             "placeholders, e.g. 'codex exec --model {model} {prompt}' — verify against "
             "your installed CLI's --help",
    )
    parser.add_argument(
        "--runner-instructions-file", default="",
        help="generic runner + with-skill mode: filename (e.g. AGENTS.md, GEMINI.md) the "
             "SKILL.md body is written to in each scenario's scratch cwd",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s", stream=sys.stderr)

    runner: RunnerSpec = {"kind": args.runner}
    if args.runner == "generic":
        if not args.runner_cmd:
            parser.error("--runner generic requires --runner-cmd")
        try:
            build_runner_cmd(args.runner_cmd, "probe", args.model)  # fail fast on a bad template
        except ValueError as exc:
            parser.error(str(exc))
        if args.mode == "with-skill" and not args.runner_instructions_file:
            parser.error(
                "--runner generic in with-skill mode requires --runner-instructions-file "
                "(the CLI's instruction file, e.g. AGENTS.md) — foreign CLIs have no "
                "--append-system-prompt"
            )
        runner["cmd_template"] = args.runner_cmd
        runner["instructions_file"] = args.runner_instructions_file

    paths = sorted(p for p in SCENARIOS_DIR.glob("*.json") if args.filter in p.name)
    if not paths:
        log.error("no scenarios match filter %r under %s", args.filter, SCENARIOS_DIR)
        return 2
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    # Legacy dir naming is preserved for the default runner; a generic run is tagged so a
    # foreign-CLI sweep can never be mistaken for (or overwrite) a claude one.
    runner_tag = "" if args.runner == "claude" else f"-{args.runner}"
    out_dir = Path(args.out) if args.out else RESULTS_DIR / f"{stamp}-{args.mode}-{args.model}{runner_tag}"
    out_dir.mkdir(parents=True, exist_ok=True)
    system_prompt = build_skill_system_prompt() if args.mode == "with-skill" else None
    log.info("%d scenario(s) → %s (mode=%s model=%s runner=%s judge=%s jobs=%d)",
             len(paths), out_dir, args.mode, args.model, args.runner, args.judge_model, args.jobs)

    results: list[ScenarioResult] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {
            pool.submit(run_scenario, p, args.mode, args.model, args.judge_model,
                        args.timeout, system_prompt, runner): p
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
