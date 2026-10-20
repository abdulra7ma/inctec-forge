@AGENTS.md

## Claude Code specifics
- Roles are available as sub-agents in `.claude/agents/` and skills as slash commands in `.claude/skills/`.
  Both are GENERATED from `.agents/` by `python3 scripts/sync_agents.py` — edit `.agents/`, never the generated copies.
- `.claude/hooks/guard_bash.py` adds a pre-execution guard on shell commands, on top of the git hooks and CI.
