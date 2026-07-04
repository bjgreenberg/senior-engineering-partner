#!/usr/bin/env bash
# Manifest-level dependency audit: every manifest, every severity.
# The same script runs locally and as the merge-blocking CI gate — pip-audit exits
# non-zero on any finding, so set -e makes it a real gate.
set -euo pipefail
cd -- "$(dirname -- "$0")/.." || exit 1
pip-audit -r requirements-server.txt
pip-audit .
