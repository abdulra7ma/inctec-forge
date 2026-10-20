#!/usr/bin/env bash
# One-command install of IncTec Forge into the current repo, without cloning the forge yourself.
#
#   bash <(gh api repos/abdulra7ma/inctec-forge/contents/bootstrap.sh -H "Accept: application/vnd.github.raw") --agent claude
#
# All arguments are passed to install.py (--agent, --target, --no-commit, --update, …).
# Uses your existing GitHub login (gh or git credentials), so it works with the private repo.
set -euo pipefail
FORGE_REPO="${FORGE_REPO:-abdulra7ma/inctec-forge}"
FORGE_REF="${FORGE_REF:-main}"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "Fetching IncTec Forge ($FORGE_REPO@$FORGE_REF)…"
if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  gh repo clone "$FORGE_REPO" "$TMP/forge" -- --depth 1 --branch "$FORGE_REF" --quiet
else
  git clone --depth 1 --branch "$FORGE_REF" --quiet "https://github.com/$FORGE_REPO.git" "$TMP/forge"
fi

# Default target is the directory you ran this from.
has_target=0
for arg in "$@"; do [[ "$arg" == "--target" || "$arg" == --target=* ]] && has_target=1; done
if [[ $has_target == 0 ]]; then set -- "$@" --target "$PWD"; fi

python3 "$TMP/forge/install.py" "$@"
