#!/usr/bin/env bash
# Install the engineering system into a target repo without overwriting anything that already exists.
# Usage: ./install.sh /path/to/your/repo
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
DST="${1:?usage: ./install.sh /path/to/repo}"
[ -d "$DST/.git" ] || { echo "Not a git repo: $DST"; exit 1; }
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' || { echo "Python 3.11+ required"; exit 1; }

place() {  # place <source-rel> <dest-rel>: copy if absent, else write <dest>.devkit for a manual merge
  local src="$SRC/$1" dst="$DST/$2"
  mkdir -p "$(dirname "$dst")"
  if [ -e "$dst" ]; then cp "$src" "$dst.devkit"; echo "  ~ $2 exists -> wrote $2.devkit (merge by hand)"
  else cp "$src" "$dst"; echo "  + $2"; fi
}

cd "$SRC"
place AGENTS.md AGENTS.md
place CLAUDE.md CLAUDE.md
while IFS= read -r f; do place "$f" "$f"; done < <(find .agents .claude/hooks .claude/settings.json docs scripts factory .github -type f | sort)
for f in Makefile .pre-commit-config.yaml docker-compose.dev.yml; do place "templates/$f" "$f"; done
while IFS= read -r f; do place "$f" "${f#templates/}"; done < <(find templates/observability -type f | sort)
chmod +x "$DST"/scripts/*.py "$DST"/scripts/githooks/* "$DST"/factory/*.py "$DST"/.claude/hooks/*.py

cd "$DST"
grep -qxF ".factory/" .gitignore 2>/dev/null || echo ".factory/" >> .gitignore
git config core.hooksPath scripts/githooks
python3 scripts/sync_agents.py >/dev/null && echo "  + generated .claude/agents, .claude/skills, .gemini/settings.json"

cat <<'EOF'

Installed. Git hooks are active (core.hooksPath=scripts/githooks). Finish setup:
  1. Merge templates/pyproject.tooling.toml (from the kit) into your pyproject.toml
  2. Rename .github/CODEOWNERS.example -> .github/CODEOWNERS and set real teams
  3. GitHub branch protection on main: require PR, 1 approval, code-owner review,
     required checks: lint, test, risk-tier, agents-sync; no force-push; no direct pushes
  4. Pick runtimes/models in .agents/config.toml (claude, codex, gemini, opencode, aider…)
  5. Tune .agents/risk-rules.json to this repo's layout, then: python3 scripts/risk_tier.py
  6. Try the factory offline first:  python3 factory/run.py new "smoke test" --runtime stub
EOF
