#!/usr/bin/env python3
"""Build tool-specific adapters from the neutral `.agents/` source of truth.

Which adapters get built is decided by `[sync].agents` in `.agents/config.toml` (set by install.py --agent).

  agent      what it reads natively                      what this script generates
  ---------  ------------------------------------------  --------------------------------------------------
  claude     CLAUDE.md, .claude/skills, .claude/agents   .claude/agents/*.md (roles → sub-agents), .claude/skills/ mirror
  codex      AGENTS.md, .agents/skills                   nothing
  gemini     GEMINI.md (configurable), .agents/skills    .gemini/settings.json → context.fileName includes AGENTS.md
  cursor     AGENTS.md, .agents/skills                   nothing
  copilot    AGENTS.md, .agents/skills, .github/skills   nothing
  opencode   AGENTS.md, .agents/skills                   nothing
  aider      files passed via `read:`                    .aider.conf.yml → read AGENTS.md

Run after editing anything in `.agents/` (or `make agents-sync`). `--check` exits 1 on drift (used in CI).
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
SUPPORTED = ("claude", "codex", "gemini", "cursor", "copilot", "opencode", "aider")
HEADER = "<!-- GENERATED from .agents/roles/{name}.md by scripts/sync_agents.py — edit the source, not this file -->\n"
CLAUDE_TOOLS = {
    "read": "Read, Grep, Glob, Bash",
    "write": "Read, Grep, Glob, Edit, Write, Bash",
    "docs": "Read, Grep, Glob, Write",
}


def parse_role(path: Path) -> tuple[dict[str, str], str]:
    m = re.match(r"---\n(.*?)\n---\n(.*)", path.read_text(), re.S)
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


def gemini_settings() -> str:
    path = ROOT / ".gemini" / "settings.json"
    data = json.loads(path.read_text()) if path.exists() else {}
    data.pop("contextFileName", None)  # legacy key
    ctx = data.setdefault("context", {})
    names = ctx.get("fileName", [])
    names = [names] if isinstance(names, str) else list(names)
    for n in ("AGENTS.md", "GEMINI.md"):
        if n not in names:
            names.append(n)
    ctx["fileName"] = names
    return json.dumps(data, indent=2) + "\n"


NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def validate_skills() -> list[str]:
    """Check every skill against the Agent Skills spec (agentskills.io/specification)."""
    errors = []
    for d in sorted(p for p in (AGENTS / "skills").iterdir() if p.is_dir()):
        f = d / "SKILL.md"
        if not f.exists():
            errors.append(f"{d.name}: missing SKILL.md")
            continue
        m = re.match(r"---\n(.*?)\n---\n", f.read_text(), re.S)
        meta = dict(line.split(": ", 1) for line in (m.group(1) if m else "").splitlines() if ": " in line)
        name, desc = meta.get("name", ""), meta.get("description", "")
        if not m:
            errors.append(f"{d.name}: SKILL.md has no frontmatter")
        elif not NAME_RE.match(name) or len(name) > 64:
            errors.append(f"{d.name}: name '{name}' must be lowercase letters/digits/single hyphens, ≤64 chars")
        elif name != d.name:
            errors.append(f"{d.name}: name '{name}' must match its folder name")
        if m and not (0 < len(desc) <= 1024):
            errors.append(f"{d.name}: description must be 1–1024 characters (is {len(desc)})")
    for r in sorted((AGENTS / "roles").glob("*.md")):
        meta, _ = parse_role(r)
        if meta["name"] != r.stem:
            errors.append(f"roles/{r.name}: name '{meta['name']}' must match the file name")
        if meta["tier"] not in ("reasoning", "fast"):
            errors.append(f"roles/{r.name}: tier must be 'reasoning' or 'fast'")
        if meta["access"].split("+")[0] not in CLAUDE_TOOLS:
            errors.append(f"roles/{r.name}: access must be read, write or docs (optionally +web)")
    return errors


def planned_outputs(cfg: dict) -> dict[Path, str | Path]:
    sync = cfg.get("sync", {})
    agents = sync.get("agents", ["claude"])
    unknown = [a for a in agents if a not in SUPPORTED]
    if unknown:
        raise SystemExit(f"unknown agent(s) in [sync].agents: {unknown}. Supported: {', '.join(SUPPORTED)}")
    out: dict[Path, str | Path] = {}
    skills = sorted(p for p in (AGENTS / "skills").iterdir() if p.is_dir())
    mirrors = list(sync.get("extra_skill_mirrors", []))

    if "claude" in agents:
        models = cfg["runtimes"]["claude"]["models"]
        for role in sorted((AGENTS / "roles").glob("*.md")):
            meta, body = parse_role(role)
            out[ROOT / ".claude" / "agents" / f"{meta['name']}.md"] = claude_agent(meta, body, models)
        mirrors.append(".claude/skills")
    if "gemini" in agents:
        out[ROOT / ".gemini" / "settings.json"] = gemini_settings()
    if "aider" in agents:
        out[ROOT / ".aider.conf.yml"] = "# GENERATED by scripts/sync_agents.py\nread:\n  - AGENTS.md\n"

    for mirror in dict.fromkeys(mirrors):
        for skill in skills:
            out[ROOT / mirror / skill.name] = skill
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
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    cfg = tomllib.loads((AGENTS / "config.toml").read_text())
    if errors := validate_skills():
        print("Invalid skills/roles:\n  " + "\n  ".join(errors), file=sys.stderr)
        return 1
    outputs = planned_outputs(cfg)
    stale = [t for t, s in outputs.items() if not same(t, s)]

    if args.check:
        for t in stale:
            print(f"out of date: {t.relative_to(ROOT)}")
        return 1 if stale else 0

    agents_dir = ROOT / ".claude" / "agents"
    if agents_dir.is_dir():  # remove generated sub-agents whose role was deleted
        for f in agents_dir.glob("*.md"):
            if f not in outputs and "GENERATED from .agents/roles" in f.read_text():
                f.unlink()
                print(f"  - {f.relative_to(ROOT)}")

    for target in stale:
        src = outputs[target]
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(src, str):
            target.write_text(src)
        else:
            shutil.rmtree(target, ignore_errors=True)
            shutil.copytree(src, target)
        if not args.quiet:
            print(f"  + {target.relative_to(ROOT)}")
    if not args.quiet:
        print(f"sync complete for {', '.join(cfg.get('sync', {}).get('agents', ['claude']))} "
              f"({len(stale)} updated, {len(outputs) - len(stale)} unchanged)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
