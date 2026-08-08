#!/usr/bin/env bash
#
# leakage-guard.sh — fail if any environment-specific / personal identifier leaks into the
# public skill. The universal core must stay universal; anything specific belongs in your
# (un-committed) references/my-environment.md.
#
# TWO-TIER denylist, so the PUBLIC repo never has to publish your personal identifiers in
# order to block them:
#   Tier 1 — GENERIC class-patterns below (a CGNAT/Tailscale IP range, [[wikilinks]]). These
#            name nothing personal, so they ship in this public file and run in CI.
#   Tier 2 — your LITERAL identifiers (hostnames, employer, repo/project names, private IPs)
#            live in references/leakage-denylist.local — an UN-COMMITTED file created from
#            leakage-denylist.local.template and sourced here if present. So your fingerprints
#            guard the tree LOCALLY without ever being written into the public repo or its
#            history. (CI, which has no .local file, enforces only the generic Tier-1 patterns;
#            the local pre-PR run is the primary gate — see CONTRIBUTING.md.)
#
# Run locally before a PR (Tier 1 + Tier 2) and as a CI check (Tier 1 only). Exits non-zero
# (printing every hit) if a denylisted identifier appears anywhere in the tracked tree.
#
# Allowed by design: author attribution ("Brian Greenberg" / the website URL) in README.md and
# SKILL.md's metadata table — matched out below. references/my-environment.md and
# references/leakage-denylist.local are never scanned (the latter has a non-scanned extension).
#
# Tier-2 sectioning: a `[hand-authored-only]` line in the .local file starts a section whose
# patterns are enforced everywhere EXCEPT evals/baselines/ (recorded model outputs). Rationale:
# broad domain-fingerprint words (generic English that merely *hints* at a product domain)
# recur legitimately in baseline transcripts whose sanitized scenarios use that vocabulary —
# an every-branch false positive that trains reviewers to wave the guard through. Literal
# identifiers (hosts, employer, repo names) stay in the default section: those are enforced in
# baselines too, because a baseline containing a real hostname IS a leak.
#
# Usage:  scripts/leakage-guard.sh
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

# --- Tier 1: GENERIC class-patterns (safe to ship; reveal nothing personal). ERE, case-insensitive.
denylist='100\.(6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])\.[0-9]{1,3}\.[0-9]{1,3}'  # CGNAT/Tailscale 100.64.0.0/10
denylist+='|\[\[[A-Za-z]'   # [[wikilink]] — NOT a Bash [[ test (which has a space after [[)

# --- Tier 2: your private LITERAL identifiers, sourced from an un-committed file (if present).
#     One POSIX-ERE fragment per line; '#' lines and blanks are ignored. A `[hand-authored-only]`
#     line starts the section whose patterns skip evals/baselines/ (see header).
local_list="references/leakage-denylist.local"
denylist_ho=''   # [hand-authored-only] patterns — enforced everywhere except evals/baselines/
section='all'
if [[ -f "$local_list" ]]; then
  while IFS= read -r frag; do
    frag="${frag%$'\r'}"                                 # strip a trailing CR
    if [[ "$frag" =~ ^\[hand-authored-only\][[:space:]]*$ ]]; then
      section='ho'; continue                             # section directive, not a pattern
    fi
    [[ "$frag" =~ ^[[:space:]]*(#.*)?$ ]] && continue    # skip blank / comment lines
    frag="${frag#"${frag%%[![:space:]]*}"}"              # ltrim
    frag="${frag%"${frag##*[![:space:]]}"}"              # rtrim
    if [[ "$section" == 'ho' ]]; then
      denylist_ho+="${denylist_ho:+|}${frag}"
    else
      denylist+="|${frag}"
    fi
  done < "$local_list"
else
  # A missing local list silently downgrades this run to Tier-1 only — say so loudly, so a
  # worktree/fresh-clone run is never mistaken for the full pre-PR gate (CONTRIBUTING.md).
  echo "WARN: $local_list not found — Tier 2 (private identifiers) NOT checked; this run covers Tier 1 only." >&2
fi

# Files to scan: tracked Markdown/JSON/shell, excluding this script and the private profile.
# Portable array fill — `mapfile`/`readarray` is bash 4+, but macOS ships bash 3.2, so a
# stock-bash run (or a non-login shell) would die with "mapfile: command not found".
files=()
while IFS= read -r _f; do
  files+=("$_f")
done < <(
  { git ls-files '*.md' '*.json' '*.sh' 2>/dev/null \
      || find . -type f \( -name '*.md' -o -name '*.json' -o -name '*.sh' \) -not -path './.git/*'; } \
    | grep -vE '^(\./)?(scripts/leakage-guard\.sh|references/my-environment\.md)$' | sort -u
)

# Allowlist: lines that legitimately contain a denylisted-looking token (author attribution).
# Stripped from the line before the denylist test, so a real fingerprint on the same line is
# still caught. NB: use this only for *unavoidable* collisions. If a denylist PATTERN is
# over-broad — a bare substring that also matches inside a longer, legitimate word — fix the
# pattern at its source (anchor / word-boundary it) instead of accreting allowlist entries.
allow='Brian Greenberg|briangreenberg\.net'

hits=0
for f in "${files[@]}"; do
  [[ -f "$f" ]] || continue
  # Effective pattern for THIS file: recorded eval baselines are exempt from the
  # [hand-authored-only] section; every other file gets both sections.
  eff="$denylist"
  case "$f" in
    evals/baselines/*|./evals/baselines/*) ;;
    *) if [[ -n "$denylist_ho" ]]; then eff+="|${denylist_ho}"; fi ;;
  esac
  while IFS= read -r line; do
    # Strip the allowed-attribution substrings, then test the remainder for denylist tokens.
    stripped="$(printf '%s' "$line" | sed -E "s/${allow}//g")"
    if printf '%s' "$stripped" | grep -qEi "$eff"; then
      if [[ "$hits" -eq 0 ]]; then echo "LEAKAGE-GUARD: environment-specific identifiers found:" >&2; fi
      printf '  %s: %s\n' "$f" "$line" >&2
      hits=$((hits + 1))
    fi
  done < <(grep -nEi "$eff" "$f" || true)
done

if [[ "$hits" -ne 0 ]]; then
  echo "FAIL: ${hits} leak(s). Move environment-specific detail into references/my-environment.md (un-committed)" >&2
  echo "      or add the identifier to references/leakage-denylist.local — never into a tracked file." >&2
  exit 1
fi
echo "PASS: no environment-specific identifiers in the public skill."
