#!/usr/bin/env python3
"""skill-lint.py — validate SKILL.md against the Agent Skills packaging constraints.

Checks the constraints that are deterministic and documented (Anthropic's Agent Skills
format — the same shape Codex CLI / Gemini CLI consume; see README "Using it with other
AI tools"):

  1. YAML frontmatter exists and is well-formed enough to carry `name` + `description`
     (parsed with a minimal stdlib reader — no third-party deps, so CI == local).
  2. `name`: present; lowercase letters/digits/hyphens only; <= 64 chars; matches the
     repository/skill directory name.
  3. `description`: present, non-empty, <= 1024 characters (the documented limit this
     repo has tripped over before — see CHANGELOG v1.1.0).
  4. Unknown frontmatter keys are WARNED, not failed (the spec allows optional fields;
     a typo'd required key still fails via checks 2-3).

Exit 0 = all checks pass (warnings allowed). Exit 1 = any check failed.
Usage: scripts/skill-lint.py [path-to-SKILL.md]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

KNOWN_KEYS = {"name", "description", "license", "allowed-tools", "metadata", "version"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DESCRIPTION_LIMIT = 1024
NAME_LIMIT = 64


def parse_frontmatter(text: str) -> dict[str, str] | None:
    """Minimal single-level YAML frontmatter reader (stdlib-only).

    Handles the subset this repo uses: `key: value` lines with optional double-quoted
    values. Multi-line/nested values are recorded with a sentinel so key presence still
    registers without a YAML dependency.
    """
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not m:
        return None
    fields: dict[str, str] = {}
    current_key: str | None = None
    for line in m.group(1).splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        if line[0] in " \t":  # continuation / nested value under the last key
            if current_key:
                fields[current_key] += " <nested>"
            continue
        km = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not km:
            return None  # a top-level line that isn't key:value = malformed frontmatter
        key, value = km.group(1), km.group(2).strip()
        if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
            value = value[1:-1]
        fields[key] = value
        current_key = key
    return fields


def main() -> int:
    skill_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("SKILL.md")
    if not skill_path.is_file():
        print(f"FAIL: {skill_path} not found", file=sys.stderr)
        return 1
    fields = parse_frontmatter(skill_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    warnings: list[str] = []

    if fields is None:
        print("FAIL: SKILL.md has no well-formed YAML frontmatter block", file=sys.stderr)
        return 1

    name = fields.get("name", "")
    if not name:
        failures.append("frontmatter `name` is missing/empty")
    else:
        if not NAME_RE.match(name):
            failures.append(f"`name` must be lowercase letters/digits/hyphens: {name!r}")
        if len(name) > NAME_LIMIT:
            failures.append(f"`name` exceeds {NAME_LIMIT} chars ({len(name)})")
        expected = skill_path.resolve().parent.name
        if name != expected:
            failures.append(f"`name` ({name!r}) != skill directory name ({expected!r})")

    description = fields.get("description", "")
    if not description:
        failures.append("frontmatter `description` is missing/empty")
    elif len(description) > DESCRIPTION_LIMIT:
        failures.append(
            f"`description` exceeds {DESCRIPTION_LIMIT} chars ({len(description)})"
        )

    for key in sorted(set(fields) - KNOWN_KEYS):
        warnings.append(f"unknown frontmatter key {key!r} (not failed; verify against the spec)")

    for w in warnings:
        print(f"WARN: {w}", file=sys.stderr)
    if failures:
        for f_ in failures:
            print(f"FAIL: {f_}", file=sys.stderr)
        return 1
    print(
        f"PASS: skill-lint — name OK, description {len(description)}/{DESCRIPTION_LIMIT} chars"
        + (f", {len(warnings)} warning(s)" if warnings else "")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
