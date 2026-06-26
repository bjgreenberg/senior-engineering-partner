#!/usr/bin/env bash
#
# render-diagrams.sh — render-check every ```mermaid block in the given Markdown files.
#
# An un-rendered Mermaid block degrades to a red "Unable to render" box for every reader —
# a broken deliverable, like a failing test (SKILL.md "Diagrams & visual documentation",
# v5.3/v5.7). This is the house pattern behind the REQUIRED `docs-render` status check:
# one self-contained script, run verbatim locally (pre-commit) AND in CI. It fails on the
# first block that does not render.
#
# Usage:   scripts/render-diagrams.sh FILE.md [FILE2.md ...]
#          scripts/render-diagrams.sh $(git ls-files '*.md')
#
# Rendering uses the mermaid-cli container so no host toolchain is needed.
#   IMPORTANT: pin MMDC_IMAGE to a DIGEST (image@sha256:...), never a moving tag, so the
#   gate is reproducible. Set the digest for your repo and commit it — this script does NOT
#   ship a digest because a fabricated one would be worse than none (verify it yourself:
#   `docker pull <image:tag>` then read the digest it reports).
MMDC_IMAGE="${MMDC_IMAGE:-ghcr.io/mermaid-js/mermaid-cli/mermaid-cli@sha256:cc56b1ed2c15f9d72ef02fe71c04d129f4291ca1ce587b9d03da8fbfbf50e072}"  # tag 11.x; bump deliberately + re-pin

set -euo pipefail

if [[ $# -eq 0 ]]; then
  echo "usage: render-diagrams.sh FILE.md [FILE2.md ...]" >&2
  exit 2
fi
if ! command -v docker >/dev/null 2>&1; then
  echo "render-diagrams.sh: docker not found (needed to run mermaid-cli). Install it or set up mmdc." >&2
  exit 127
fi

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

total=0
for md in "$@"; do
  [[ -f "$md" ]] || { echo "render-diagrams.sh: no such file: $md" >&2; exit 1; }

  # Extract each fenced ```mermaid block into its own .mmd file.
  awk -v dir="$workdir" -v src="$md" '
    /^```mermaid[[:space:]]*$/ { inblock=1; n++; fn=sprintf("%s/%s.%03d.mmd", dir, "block", n); next }
    /^```[[:space:]]*$/ && inblock { inblock=0; next }
    inblock { print > fn }
  ' "$md"

  while IFS= read -r -d '' block; do
    total=$((total+1))
    echo "==> rendering $(basename "$block") from $md"
    # Render to SVG; mmdc exits non-zero on a syntax error → the gate fails.
    docker run --rm -v "$workdir:/data" "$MMDC_IMAGE" \
      -i "/data/$(basename "$block")" -o "/data/$(basename "$block").svg" >/dev/null
  done < <(find "$workdir" -maxdepth 1 -name 'block.*.mmd' -print0)
  # Clear extracted blocks before the next file so counts/names don't collide.
  find "$workdir" -maxdepth 1 -name 'block.*' -delete
done

echo "render-diagrams.sh: all ${total} Mermaid block(s) rendered cleanly."
