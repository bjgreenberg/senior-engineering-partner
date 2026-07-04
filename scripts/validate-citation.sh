#!/usr/bin/env bash
#
# validate-citation.sh — validate CITATION.cff against the Citation File Format schema.
#
# An invalid CITATION.cff silently breaks GitHub's "Cite this repository" button and the
# Zenodo release integration — a broken deliverable, like a failing test. A citation file
# is also a *claim* (version, date), so it is validated as a gate, not trusted: this is the
# house pattern — one self-contained script, run verbatim locally AND in CI (the
# `citation-validate` workflow). release-please bumps `version`/`date-released` in place
# (`x-release-please-version` / `x-release-please-date` annotations); this gate proves the
# file stays schema-valid through those bumps.
#
# Usage:   scripts/validate-citation.sh [CITATION.cff]
#
# Validation uses the official cffconvert container so no host toolchain is needed.
#   IMPORTANT: CFFCONVERT_IMAGE is pinned to a DIGEST (image@sha256:...), not a moving tag,
#   so the gate is reproducible. The default below is the published cffconvert digest
#   (tag 2.0.0); override via the CFFCONVERT_IMAGE env var. When you bump it, re-pin to the
#   exact digest `docker pull` reports for the new tag — never a fabricated one.
#   No docker (e.g. a sandboxed session)? Same validator, pinned from PyPI:
#     pip install cffconvert==2.0.0 && cffconvert --validate -i CITATION.cff
CFFCONVERT_IMAGE="${CFFCONVERT_IMAGE:-citationcff/cffconvert@sha256:f8c5dc5fa8013e5c3635b1c2695bf54eac4d319719f8acdbb7b7ad7a778e46ea}"  # tag 2.0.0; bump deliberately + re-pin

set -euo pipefail

cff="${1:-CITATION.cff}"
if [[ ! -f "$cff" ]]; then
  echo "validate-citation.sh: no such file: $cff" >&2
  exit 1
fi
if ! command -v docker >/dev/null 2>&1; then
  echo "validate-citation.sh: docker not found (needed to run cffconvert). Install it, or run the PyPI fallback in this script's header." >&2
  exit 127
fi

dir="$(cd "$(dirname "$cff")" && pwd)"
base="$(basename "$cff")"

# cffconvert exits non-zero on a schema violation → the gate fails.
# Read-only mount: validation never writes, so the container gets no write path.
docker run --rm -v "$dir:/app:ro" "$CFFCONVERT_IMAGE" --validate -i "/app/$base"
echo "validate-citation.sh: $cff is valid CFF."
