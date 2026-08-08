#!/usr/bin/env bash
#
# actions-lint.sh — gate .github/workflows/ with actionlint (correctness) + zizmor (security).
#
# Why two tools (complementarity, per SKILL.md "name the complementarity"): actionlint checks
# workflow *correctness* — schema, expression types, shellcheck inside run: blocks; zizmor
# checks workflow *security* — template/expression injection, unpinned uses:, credential
# persistence, dangerous pull_request_target triggers. Neither covers the other's ground.
#
# House pattern: one self-contained script, run verbatim locally AND in CI (the actions-lint
# workflow). Both tools are version-pinned; actionlint is additionally sha256-verified against
# its release's published checksums (the SKILL.md supply-chain canonical pattern). zizmor is
# version-pinned from PyPI (prebuilt wheel; not hash-locked — stated per the pin-vs-integrity
# rule). ZIZMOR_OFFLINE=true keeps the run deterministic (no network audits).
#
# Exit-code discipline: zizmor exits 10-14 when findings exist (encoding max severity) and
# other non-zero on tool error — both fail this gate, but are REPORTED differently so a tool
# crash is never mistaken for "findings" (or vice versa). Never gate zizmor through a pipeline
# ($? would be the tail's — the $pipestatus trap).
#
# Usage:  scripts/actions-lint.sh
set -euo pipefail

ZIZMOR_VERSION="${ZIZMOR_VERSION:-1.29.0}"
ACTIONLINT_VERSION="${ACTIONLINT_VERSION:-1.7.12}"
# sha256 per platform, copied from the release's published actionlint_<v>_checksums.txt.
# When bumping the version, re-copy BOTH from the new checksums file — never fabricate.
ACTIONLINT_SHA_DARWIN_ARM64="aba9ced2dee8d27fecca3dc7feb1a7f9a52caefa1eb46f3271ea66b6e0e6953f"
ACTIONLINT_SHA_LINUX_AMD64="8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if [[ ! -d .github/workflows ]]; then
  echo "actions-lint.sh: no .github/workflows directory — nothing to lint." >&2
  exit 0
fi

# --- actionlint: PATH binary if it matches the pin, else checksum-verified download ----------
get_actionlint() {
  if command -v actionlint >/dev/null 2>&1; then
    local v
    v="$(actionlint --version 2>/dev/null | head -1)"
    if [[ "$v" == "$ACTIONLINT_VERSION" ]]; then
      echo "actionlint"
      return 0
    fi
    echo "actions-lint.sh: PATH actionlint is ${v:-unknown}, pin is ${ACTIONLINT_VERSION} — using verified download." >&2
  fi

  local os arch sha plat cache bin
  case "$(uname -s)" in
    Darwin) os="darwin" ;;
    Linux)  os="linux" ;;
    *) echo "actions-lint.sh: unsupported OS $(uname -s)" >&2; return 1 ;;
  esac
  case "$(uname -m)" in
    arm64|aarch64) arch="arm64" ;;
    x86_64)        arch="amd64" ;;
    *) echo "actions-lint.sh: unsupported arch $(uname -m)" >&2; return 1 ;;
  esac
  plat="${os}_${arch}"
  case "$plat" in
    darwin_arm64) sha="$ACTIONLINT_SHA_DARWIN_ARM64" ;;
    linux_amd64)  sha="$ACTIONLINT_SHA_LINUX_AMD64" ;;
    *) echo "actions-lint.sh: no pinned sha for platform ${plat} — add it from the release checksums file." >&2; return 1 ;;
  esac

  cache="${XDG_CACHE_HOME:-$HOME/.cache}/actions-lint/actionlint-${ACTIONLINT_VERSION}-${plat}"
  bin="$cache/actionlint"
  if [[ ! -x "$bin" ]]; then
    mkdir -p "$cache"
    local tgz="$cache/actionlint.tar.gz"
    curl -fsSL -o "$tgz" \
      "https://github.com/rhysd/actionlint/releases/download/v${ACTIONLINT_VERSION}/actionlint_${ACTIONLINT_VERSION}_${plat}.tar.gz"
    # Verify BEFORE extracting — never run/unpack an unverified download.
    if command -v sha256sum >/dev/null 2>&1; then
      echo "${sha}  ${tgz}" | sha256sum -c - >/dev/null
    else
      echo "${sha}  ${tgz}" | shasum -a 256 -c - >/dev/null
    fi
    tar -xzf "$tgz" -C "$cache" actionlint
    rm -f "$tgz"
  fi
  echo "$bin"
}

actionlint_bin="$(get_actionlint)"

echo "== actionlint ${ACTIONLINT_VERSION} (correctness)"
al_rc=0
"$actionlint_bin" || al_rc=$?
if [[ "$al_rc" -ne 0 ]]; then
  echo "actions-lint.sh: actionlint found problems (exit ${al_rc})." >&2
fi

# --- zizmor: pinned from PyPI via uvx (fast, cached) or a throwaway venv --------------------
run_zizmor() {
  if command -v uvx >/dev/null 2>&1; then
    ZIZMOR_OFFLINE=true uvx "zizmor==${ZIZMOR_VERSION}" --format=plain .github/workflows/
  else
    local venv
    venv="$(mktemp -d)/zv"
    python3 -m venv "$venv"
    "$venv/bin/pip" install --quiet --disable-pip-version-check "zizmor==${ZIZMOR_VERSION}"
    ZIZMOR_OFFLINE=true "$venv/bin/zizmor" --format=plain .github/workflows/
  fi
}

echo "== zizmor ${ZIZMOR_VERSION} (security)"
zz_rc=0
run_zizmor || zz_rc=$?
case "$zz_rc" in
  0) ;;
  1[0-4])
    echo "actions-lint.sh: zizmor found security issues (exit ${zz_rc} encodes max severity)." >&2 ;;
  *)
    echo "actions-lint.sh: zizmor TOOL ERROR (exit ${zz_rc}) — this is not a findings result; fix the tool run." >&2 ;;
esac

if [[ "$al_rc" -ne 0 || "$zz_rc" -ne 0 ]]; then
  echo "FAIL: actions-lint (actionlint=${al_rc}, zizmor=${zz_rc})." >&2
  exit 1
fi
echo "PASS: workflows clean under actionlint + zizmor."
