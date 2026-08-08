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
  5. Reference link integrity: every `references/<file>.md` path the SKILL.md body names
     exists on disk, and every `references/*.md` file on disk is named somewhere in the
     body (no dead pointers, no orphans a reader can never reach). The private
     environment profile (`my-environment.md`) is exempt in both directions — it is
     deliberately untracked, so it is absent in CI and unnamed-on-disk locally.
  6. Core word budget: the SKILL.md body (frontmatter excluded) stays within
     CORE_WORD_BUDGET words. The body is loaded wholesale into context on every
     invocation, so its size is a per-session cost and an instruction-salience risk —
     the budget is a RATCHET: it may be lowered as the core is compressed, never raised
     without a maintainer decision recorded in the CHANGELOG.
  7. README documentation integrity (only when a README.md sits beside SKILL.md):
     every `references/*.md` on disk and every helper in `scripts/` (top-level .sh/.py/
     .md) is NAMED somewhere in the README — the catalogue/prose must not silently lag
     the tree (the 2026-08-08 docs audit found two references and four scripts missing;
     this is that audit's LOW-11 "mechanize it", the same move that created check 5).

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
# A CEILING against unbounded growth, not a diet target: the tranche-5 core diet was
# REFUTED by its own eval sweep (docs/adr/0001-core-density-over-token-cost.md) — the
# core keeps its density, and any future compression pays section-by-section against
# that section's guarding scenarios. Raise only via a recorded maintainer decision.
CORE_WORD_BUDGET = 12_700
CORE_WORD_WARN = 12_000
# The private environment profile: named by SKILL.md but deliberately untracked (absent in
# CI), and locally present but not required to be named — exempt from check 5 both ways.
PRIVATE_REFS = {"my-environment.md"}
REF_LINK_RE = re.compile(r"references/([A-Za-z0-9._-]+\.md)")


def parse_frontmatter(text: str) -> dict[str, str] | None:
    """Minimal single-level YAML frontmatter reader (stdlib-only).

    Handles the subset this repo uses: `key: value` lines with optional double-quoted
    values, plus indented continuation / block-scalar content (`>`/`|` styles), which is
    ACCUMULATED into the key's value — so the description length check measures the real
    content and cannot be bypassed by writing the description as a multi-line block.
    """
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not m:
        return None
    fields: dict[str, str] = {}
    current_key: str | None = None
    for line in m.group(1).splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        if line[0] in " \t":  # continuation / block-scalar content under the last key
            if current_key:
                fields[current_key] = (fields[current_key] + " " + line.strip()).strip()
            continue
        km = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not km:
            return None  # a top-level line that isn't key:value = malformed frontmatter
        key, value = km.group(1), km.group(2).strip()
        if value in {">", "|", ">-", "|-", ">+", "|+"}:
            value = ""  # block-scalar indicator — the real content follows indented
        elif len(value) >= 2 and value[0] == '"' and value[-1] == '"':
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

    # Check 5 — reference link integrity (both directions), rooted at the skill dir.
    text = skill_path.read_text(encoding="utf-8")
    body = re.sub(r"^---\r?\n.*?\r?\n---\r?\n", "", text, count=1, flags=re.S)
    skill_dir = skill_path.resolve().parent
    refs_dir = skill_dir / "references"
    named = set(REF_LINK_RE.findall(body))
    for ref in sorted(named - PRIVATE_REFS):
        if not (refs_dir / ref).is_file():
            failures.append(f"SKILL.md names references/{ref} but the file does not exist")
    if refs_dir.is_dir():
        on_disk = {p.name for p in refs_dir.glob("*.md")}
        for ref in sorted(on_disk - named - PRIVATE_REFS):
            failures.append(
                f"references/{ref} exists but SKILL.md never names it (orphan — unreachable"
                " by progressive disclosure; name it or remove it)"
            )

    # Check 7 — README documentation integrity (see module docstring). Conditional on a
    # README existing beside SKILL.md so fixture skills without one still lint clean.
    readme_path = skill_dir / "README.md"
    if readme_path.is_file():
        readme = readme_path.read_text(encoding="utf-8")
        if refs_dir.is_dir():
            for ref in sorted({p.name for p in refs_dir.glob("*.md")} - PRIVATE_REFS):
                if ref not in readme:
                    failures.append(
                        f"references/{ref} exists but README.md never names it — update the"
                        " reference catalogue (a doc that lags the tree is a wrong doc)"
                    )
        scripts_dir = skill_dir / "scripts"
        if scripts_dir.is_dir():
            helpers = sorted(
                p.name
                for p in scripts_dir.iterdir()
                if p.is_file() and p.suffix in {".sh", ".py", ".md"}
            )
            for helper in helpers:
                if helper not in readme:
                    failures.append(
                        f"scripts/{helper} exists but README.md never names it — document"
                        " the helper (or remove it)"
                    )

    # Check 6 — core word budget (ratchet; see module docstring).
    words = len(body.split())
    if words > CORE_WORD_BUDGET:
        failures.append(
            f"SKILL.md body is {words} words, over the CORE_WORD_BUDGET of"
            f" {CORE_WORD_BUDGET} — compress to a reference trigger instead of growing the"
            " always-loaded core (the budget only ratchets down)"
        )
    elif words > CORE_WORD_WARN:
        warnings.append(
            f"SKILL.md body is {words} words (> {CORE_WORD_WARN} warning floor,"
            f" budget {CORE_WORD_BUDGET}) — nearing the core budget"
        )

    for w in warnings:
        print(f"WARN: {w}", file=sys.stderr)
    if failures:
        for f_ in failures:
            print(f"FAIL: {f_}", file=sys.stderr)
        return 1
    print(
        f"PASS: skill-lint — name OK, description {len(description)}/{DESCRIPTION_LIMIT} chars,"
        f" body {words}/{CORE_WORD_BUDGET} words, {len(named - PRIVATE_REFS)} reference links OK"
        + (f", {len(warnings)} warning(s)" if warnings else "")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
