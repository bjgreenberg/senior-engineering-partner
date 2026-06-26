#!/usr/bin/env bash
#
# leakage-guard.sh — fail if any environment-specific / personal identifier leaks into the
# public skill. The universal core must stay universal; anything specific belongs in your
# (un-committed) references/my-environment.md.
#
# Run locally before a PR and as a required CI check. Exits non-zero (printing every hit) if
# a denylisted identifier appears anywhere in the tracked tree.
#
# Allowed by design: author attribution ("Brian Greenberg" / the contact email) in README.md
# and SKILL.md's metadata table — these are intentional and matched out below. The private
# references/my-environment.md is .gitignore'd and never scanned.
#
# Usage:  scripts/leakage-guard.sh
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

# Denylist of identifiers that must NEVER appear in the public skill (ERE, case-insensitive).
# Grouped: hosts · employer · vendor stack · products/repos · cloud projects · secret-mgr
# account · machine-fleet tooling · multi-machine phrasing · Obsidian-style [[wikilinks]].
denylist='REDACTED|REDACTED|REDACTED|REDACTED'
denylist+='|\bREDACTED\b|REDACTED'
denylist+='|\bREDACTED\b|\bREDACTED\b|\bREDACTED\b|REDACTED|REDACTED|REDACTED|REDACTED|REDACTED|REDACTED|Monday\.com|REDACTED'
denylist+='|REDACTED|REDACTED|REDACTED|REDACTED|\bREDACTED\b|REDACTED|REDACTED|REDACTED|REDACTED|REDACTED|REDACTED|REDACTED'
denylist+='|REDACTED|REDACTED|REDACTED'
denylist+='|my\.1password'
denylist+='|\bREDACTED\b|REDACTED|REDACTED'
denylist+='|REDACTED|REDACTED|REDACTED'
denylist+='|REDACTED|REDACTED|REDACTED|REDACTED'   # product-domain fingerprints
denylist+='|\[\[[A-Za-z]'   # [[wikilink]] — NOT a Bash [[ test (which has a space after [[)

# Files to scan: tracked Markdown/JSON/shell, excluding this script and the private profile.
mapfile -t files < <(
  { git ls-files '*.md' '*.json' '*.sh' 2>/dev/null \
      || find . -type f \( -name '*.md' -o -name '*.json' -o -name '*.sh' \) -not -path './.git/*'; } \
    | grep -vE '^(\./)?(scripts/leakage-guard\.sh|references/my-environment\.md)$' | sort -u
)

# Allowlist: lines that legitimately contain a denylisted-looking token (author attribution).
allow='Brian Greenberg|REDACTEDbriangreenberg\.net'

hits=0
for f in "${files[@]}"; do
  [[ -f "$f" ]] || continue
  while IFS= read -r line; do
    # Strip the allowed-attribution substrings, then test the remainder for denylist tokens.
    stripped="$(printf '%s' "$line" | sed -E "s/${allow}//g")"
    if printf '%s' "$stripped" | grep -qEi "$denylist"; then
      if [[ "$hits" -eq 0 ]]; then echo "LEAKAGE-GUARD: environment-specific identifiers found:" >&2; fi
      printf '  %s: %s\n' "$f" "$line" >&2
      hits=$((hits + 1))
    fi
  done < <(grep -nEi "$denylist" "$f" || true)
done

if [[ "$hits" -ne 0 ]]; then
  echo "FAIL: ${hits} leak(s). Move environment-specific detail into references/my-environment.md (un-committed)." >&2
  exit 1
fi
echo "PASS: no environment-specific identifiers in the public skill."
