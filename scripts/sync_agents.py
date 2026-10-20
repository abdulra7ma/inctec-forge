#!/usr/bin/env python3
"""Generate tool-specific copies from the neutral `.agents/` source of truth.

  .agents/roles/*.md   -> .claude/agents/*.md (Claude Code sub-agents, with model + tool list)
  .agents/skills/*     -> each dir in [sync].skill_mirrors (e.g. .claude/skills)
  AGENTS.md            -> .gemini/settings.json contextFileName (Gemini CLI)

Codex, Cursor, Copilot, opencode and others read AGENTS.md directly; many read SKILL.md skills from
.agents/skills natively. Run after editing anything in .agents/. Use --check in CI to fail on drift.
Stdlib only (Python 3.11+).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / ".agents"
HEADER = "<!-- GENERATED from .agents/roles/{name}.md by scripts/sync_agents.py — edit the source, not this file -->\n"

CLAUDE_TOOLS = {
    "read": "Read, Grep, Glob, Bash",
    "write": "Read, Grep, Glob, Edit, Write, Bash",
    "docs": "Read, Grep, Glob, Write",
}


def parse_role(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text()
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    if not m:
        raise SystemExit(f"{path}: missing frontmatter")
    meta = dict(line.split(": ", 1) for line in m.group(1).splitlines() if ": " in line)
    for key in ("name", "description", "tier", "access"):
        if key not in meta:
            raise SystemExit(f"{path}: frontmatter missing '{key}'")
    return meta, m.group(2)


def claude_agent(meta: dict[str, str], body: str, models: dict[str, str]) -> str:
    access = meta["access"]
    tools = CLAUDE_TOOLS[access.split("+")[0]]
    if "+web" in access:
        tools += ", WebSearch, WebFetch"
    lines = ["---", f"name: {meta['name']}", f"description: {meta['description']}", f"tools: {tools}"]
    if model := models.get(meta["tier"], ""):
        lines.append(f"model: {model}")
    return "\n".join(lines) + "\n---\n" + HEADER.format(name=meta["name"]) + body


def planned_outputs(cfg: dict) -> dict[Path, str | Path]:
    """Return {target_path: text_or_source_dir}."""
    out: dict[Path, str | Path] = {}
    sync = cfg.get("sync", {})
    if sync.get("claude_agents", True):
        models = cfg["runtimes"]["claude"]["models"]
        for role in sorted((AGENTS / "roles").glob("*.md")):
            meta, body = parse_role(role)
            out[ROOT / ".claude" / "agents" / f"{meta['name']}.md"] = claude_agent(meta, body, models)
    for mirror in sync.get("skill_mirrors", []):
        for skill in sorted((AGENTS / "skills").iterdir()):
            if skill.is_dir():
                out[ROOT / mirror / skill.name] = skill
    if sync.get("gemini_context", True):
        out[ROOT / ".gemini" / "settings.json"] = json.dumps({"contextFileName": "AGENTS.md"}, indent=2) + "\n"
    return out


def same(target: Path, src: str | Path) -> bool:
    if isinstance(src, str):
        return target.is_file() and target.read_text() == src
    if not target.is_dir():
        return False
    a = {p.relative_to(src): p.read_bytes() for p in src.rglob("*") if p.is_file()}
    b = {p.relative_to(target): p.read_bytes() for p in target.rglob("*") if p.is_file()}
    return a == b


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="exit 1 if generated files are out of date")
    args = ap.parse_args()
    cfg = tomllib.loads((AGENTS / "config.toml").read_text())
    outputs = planned_outputs(cfg)

    stale = [t for t, s in outputs.items() if not same(t, s)]
    if args.check:
        for t in stale:
            print(f"out of date: {t.relative_to(ROOT)}")
        return 1 if stale else 0

    # remove generated Claude agents whose source role was deleted
    agents_dir = ROOT / ".claude" / "agents"
    if agents_dir.is_dir():
        for f in agents_dir.glob("*.md"):
            if f not in outputs and "GENERATED from .agents/roles" in f.read_text():
                f.unlink()
                print(f"  - {f.relative_to(ROOT)}")

    for target, src in outputs.items():
        if target in stale:
            target.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(src, str):
                target.write_text(src)
            else:
                shutil.rmtree(target, ignore_errors=True)
                shutil.copytree(src, target)
            print(f"  + {target.relative_to(ROOT)}")
    print(f"sync complete ({len(stale)} updated, {len(outputs) - len(stale)} unchanged)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
