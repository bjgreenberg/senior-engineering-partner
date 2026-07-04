#!/usr/bin/env bash
#
# test-scripts.sh — fixture regression tests for the shipped gate scripts (plan item C6).
#
# The gate-construction rule these tests enforce (references/testing.md §3c): a gate must be
# ABLE to fail. Each shipped gate gets (a) a planted-violation fixture the gate must FAIL on,
# and (b) a clean fixture it must PASS on — so a regression that silently blinds a gate (the
# exact failure mode C6 names for leakage-guard) goes red here instead of shipping.
#
# Scope: leakage-guard.sh (Tier 1 — the generic class-patterns; the Tier-2 .local file is
# per-machine and deliberately untested here) and skill-lint.py. render-diagrams.sh and
# validate-citation.sh are NOT fixture-tested here: they need their docker images
# (mermaid-cli / cffconvert), and their CI jobs (docs-render / citation-validate) already
# exercise the pass path on every run while each fail path was proven at introduction; a
# docker pull in this quick suite would slow every run for little signal.
#
# Runs on stock bash 3.2 (no mapfile/associative arrays). No network, no docker.
# Usage: scripts/tests/test-scripts.sh   (exit 0 = all pass)
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
pass=0
fail=0

note() { printf '%s\n' "$*" >&2; }

check() { # check <description> <expected-exit> <actual-exit>
  local desc="$1" expected="$2" actual="$3"
  if [[ "$actual" -eq "$expected" ]]; then
    pass=$((pass + 1))
  else
    note "FAIL: ${desc} (expected exit ${expected}, got ${actual})"
    fail=$((fail + 1))
  fi
}

scratch="$(mktemp -d)"
cleanup() { rm -rf "$scratch"; }
trap cleanup EXIT

# --- leakage-guard.sh fixtures -------------------------------------------------------------
# The guard cd's to its own repo root, so each fixture is a throwaway git repo with the guard
# script copied in at scripts/leakage-guard.sh.
make_guard_fixture() { # make_guard_fixture <dir>
  local dir="$1"
  mkdir -p "$dir/scripts" "$dir/references"
  cp "$repo_root/scripts/leakage-guard.sh" "$dir/scripts/leakage-guard.sh"
  git -C "$dir" init -q
}

# (a) planted Tier-1 violations -> the guard must FAIL (exit 1) and name the file.
# NB: the violation strings are ASSEMBLED at runtime — a literal in this tracked file would
# (correctly!) trip the real leakage-guard on this repo. That near-miss happened during
# authoring: the guard scans TRACKED files, so this script passed pre-`git add` and failed
# right after — the exact class of gate-blinding subtlety this suite exists to catch.
violdir="$scratch/guard-violation"
make_guard_fixture "$violdir"
lb='['
{
  echo "# doc"
  printf 'the host lives at 100.%s on the tailnet\n' "71.2.3"   # CGNAT/Tailscale class pattern
  printf 'see %s%sproject-notes]] for details\n' "$lb" "$lb"    # wikilink class pattern
} > "$violdir/README.md"
git -C "$violdir" add -A
rc=0; (cd "$violdir" && bash scripts/leakage-guard.sh) >/dev/null 2>&1 || rc=$?
check "leakage-guard FAILS on planted Tier-1 identifiers" 1 "$rc"

# ...and the failure output names the offending file (verdict, not just exit code — §3c).
out="$( (cd "$violdir" && bash scripts/leakage-guard.sh) 2>&1 || true )"
rc=0; grep -q "README.md" <<<"$out" || rc=$?
check "leakage-guard failure output names the offending file" 0 "$rc"

# (b) clean fixture -> the guard must PASS (exit 0), warning that Tier 2 is absent.
cleandir="$scratch/guard-clean"
make_guard_fixture "$cleandir"
printf '# doc\nnothing environment-specific here.\n' > "$cleandir/README.md"
git -C "$cleandir" add -A
rc=0; out="$( (cd "$cleandir" && bash scripts/leakage-guard.sh) 2>&1 )" || rc=$?
check "leakage-guard PASSES on a clean tree" 0 "$rc"
rc=0; grep -q "Tier 1 only" <<<"$out" || rc=$?
check "leakage-guard WARNs Tier-1-only when the .local denylist is absent" 0 "$rc"

# --- skill-lint.py fixtures ------------------------------------------------------------------
lintdir="$scratch/skill-fixture/good-skill"
mkdir -p "$lintdir"
printf -- '---\nname: good-skill\ndescription: "A test skill."\n---\n# body\n' > "$lintdir/SKILL.md"
rc=0; python3 "$repo_root/scripts/skill-lint.py" "$lintdir/SKILL.md" >/dev/null 2>&1 || rc=$?
check "skill-lint PASSES a conforming SKILL.md" 0 "$rc"

badlintdir="$scratch/skill-fixture/bad-skill"
mkdir -p "$badlintdir"
long_desc="$(printf 'x%.0s' $(seq 1 1100))"
printf -- '---\nname: Mismatched_Name\ndescription: "%s"\n---\n# body\n' "$long_desc" > "$badlintdir/SKILL.md"
rc=0; python3 "$repo_root/scripts/skill-lint.py" "$badlintdir/SKILL.md" >/dev/null 2>&1 || rc=$?
check "skill-lint FAILS on bad name + oversize description" 1 "$rc"

rc=0; python3 "$repo_root/scripts/skill-lint.py" "$scratch/does-not-exist/SKILL.md" >/dev/null 2>&1 || rc=$?
check "skill-lint FAILS on a missing file" 1 "$rc"

# Block-scalar bypass (a Copilot-review catch): an oversize description written as a
# multi-line block must still trip the length gate — the parser accumulates continuation
# content instead of counting a sentinel.
blockdir="$scratch/skill-fixture/block-skill"
mkdir -p "$blockdir"
{
  printf -- '---\nname: block-skill\ndescription: >-\n'
  for _ in 1 2 3 4 5 6; do printf '  %s\n' "$(printf 'y%.0s' $(seq 1 200))"; done
  printf -- '---\n# body\n'
} > "$blockdir/SKILL.md"
rc=0; python3 "$repo_root/scripts/skill-lint.py" "$blockdir/SKILL.md" >/dev/null 2>&1 || rc=$?
check "skill-lint FAILS on an oversize block-scalar description (bypass closed)" 1 "$rc"

# --- the real repo passes its own gates (precondition assert, not print — §3c) --------------
rc=0; python3 "$repo_root/scripts/skill-lint.py" "$repo_root/SKILL.md" >/dev/null 2>&1 || rc=$?
check "skill-lint PASSES the real SKILL.md" 0 "$rc"

note "test-scripts: ${pass} passed, ${fail} failed"
[[ "$fail" -eq 0 ]]
