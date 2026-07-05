#!/usr/bin/env bash
# Dependency audit over the project's manifests.
set -euo pipefail
cd -- "$(dirname -- "$0")/.." || exit 1
pip-audit -r requirements-server.txt
pip-audit .
