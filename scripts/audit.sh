#!/usr/bin/env bash
#
# audit.sh — manifest-level dependency audit gate (the SKILL.md "Dependency-audit gate").
#
# Audits EVERY pinned Python manifest at ALL severities, so a known-vulnerable pin —
# or a vulnerable pin hiding in a manifest that never reaches a built image, or in a
# manifest that has drifted out of lockstep with another — FAILS at the source.
# This is the complement to image scanning (Trivy/grype), which only sees packages
# that land in an image and is usually floored at HIGH/CRITICAL.
#
# Run the SAME script locally and in CI (one gate, two places). pip-audit exits
# non-zero on a finding, so `set -euo pipefail` makes this a real, merge-blocking gate.
#
# Usage:   scripts/audit.sh [repo_root]   (defaults to the current directory)
# Requires: pip-audit  (pipx install pip-audit  — verify availability before relying on it)
#
# Ships with the senior-engineering-partner skill as a starting point; adapt the
# manifest discovery to the repo. For non-Python ecosystems use the native auditor with
# the same posture (npm audit / cargo audit / govulncheck / bundler-audit) or osv-scanner
# as the polyglot fallback — see SKILL.md "Dependency-audit gate".

set -euo pipefail

ROOT="${1:-.}"
cd "$ROOT"

if ! command -v pip-audit >/dev/null 2>&1; then
  echo "audit.sh: pip-audit not found. Install it (e.g. 'pipx install pip-audit') and re-run." >&2
  exit 127
fi

found_manifest=0

# 1) Every requirements*.txt, audited with -r (covers requirements-server.txt, -dev, etc.).
#    -print0/-d '' handles paths with spaces; null-delimited per SKILL.md Bash standards.
while IFS= read -r -d '' req; do
  found_manifest=1
  echo "==> pip-audit -r ${req}"
  pip-audit --strict -r "$req"
done < <(find . -type f -name 'requirements*.txt' -not -path '*/node_modules/*' -print0)

# 2) pyproject.toml in project mode (`pip-audit .`) so pyproject↔requirements drift
#    cannot hide a CVE in whichever file the image build doesn't read.
if [[ -f pyproject.toml ]]; then
  found_manifest=1
  echo "==> pip-audit . (pyproject.toml project mode)"
  pip-audit --strict .
fi

if [[ "$found_manifest" -eq 0 ]]; then
  echo "audit.sh: no requirements*.txt or pyproject.toml found under '${ROOT}'." >&2
  exit 1
fi

echo "audit.sh: all manifests clean (no known vulnerabilities at any severity)."
