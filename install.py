#!/usr/bin/env python3
"""IncTec Forge installer — sets up the engineering system in a repo for the coding agent(s) you use.

  python3 install.py --agent claude                       # into the current repo
  python3 install.py --agent claude,codex --target ../my-service
  python3 install.py                                      # interactive: asks which agent(s)
  python3 install.py --agent cursor --no-commit           # leave changes uncommitted
  python3 install.py --update                             # re-apply the latest forge over an existing install

From anywhere (no local clone needed; uses your GitHub login for the private repo):
  bash <(gh api repos/abdulra7ma/inctec-forge/contents/bootstrap.sh -H "Accept: application/vnd.github.raw") --agent claude

What it does:
  1. copies the core system (AGENTS.md, .agents/, docs, scripts, factory, CI, dev stack) — never overwriting
     your files: on conflict it writes <file>.forge-new for you to merge (use --force to overwrite)
  2. adds what your agent(s) need (e.g. Claude: CLAUDE.md, hooks, sub-agents; Gemini: settings; Aider: config)
  3. records your agents in .agents/config.toml and builds the adapters (scripts/sync_agents.py)
  4. turns on the git hooks, ignores .factory/, writes .agents/forge.lock.json
  5. commits everything on branch chore/forge-setup:  "chore: add IncTec Forge setup (agents: …)"
Stdlib only, Python 3.11+.
"""
from __future__ import annotations

import argparse
import datetime as dt
import filecmp
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

if sys.version_info < (3, 11):
    sys.exit("IncTec Forge needs Python 3.11+")

SRC = Path(__file__).resolve().parent
AGENTS = ("claude", "codex", "gemini", "cursor", "copilot", "opencode", "aider")
AGENT_INFO = {
    "claude": "Claude Code — CLAUDE.md, sub-agents, slash-command skills, command guard hook",
    "codex": "OpenAI Codex CLI — reads AGENTS.md and .agents/skills natively",
    "gemini": "Gemini CLI — settings.json pointing at AGENTS.md; reads .agents/skills natively",
    "cursor": "Cursor — reads AGENTS.md and .agents/skills natively",
    "copilot": "GitHub Copilot — reads AGENTS.md and .agents/skills natively",
    "opencode": "opencode — reads AGENTS.md and .agents/skills natively",
    "aider": "Aider — .aider.conf.yml that loads AGENTS.md",
}
# Agents with a headless runtime the factory can drive (see [runtimes] in .agents/config.toml)
FACTORY_RUNTIMES = ("claude", "codex", "gemini", "opencode", "aider")

# (source path in forge, destination path in target). Directories copy recursively.
CORE: list[tuple[str, str]] = [
    ("AGENTS.md", "AGENTS.md"),
    (".agents", ".agents"),
    ("docs/engineering", "docs/engineering"),
    ("docs/adr/0000-template.md", "docs/adr/0000-template.md"),
    ("docs/design/_template.md", "docs/design/_template.md"),
    ("scripts", "scripts"),
    ("factory", "factory"),
    (".github/workflows/ci.yml", ".github/workflows/ci.yml"),
    (".github/pull_request_template.md", ".github/pull_request_template.md"),
    (".github/CODEOWNERS.example", ".github/CODEOWNERS.example"),
    ("templates/Makefile", "Makefile"),
    ("templates/.pre-commit-config.yaml", ".pre-commit-config.yaml"),
    ("templates/docker-compose.dev.yml", "docker-compose.dev.yml"),
    ("templates/observability", "observability"),
    ("templates/pyproject.tooling.toml", "docs/engineering/pyproject.tooling.toml"),
]
PER_AGENT: dict[str, list[tuple[str, str]]] = {
    "claude": [("CLAUDE.md", "CLAUDE.md"), (".claude/settings.json", ".claude/settings.json"),
               (".claude/hooks", ".claude/hooks")],
}
# Files whose content is managed by the forge — overwritten on --update instead of producing .forge-new
MANAGED_PREFIXES = (".agents/roles/", ".agents/skills/", "scripts/", "factory/", "docs/engineering/",
                    ".claude/hooks/", "docs/adr/0000-template.md", "docs/design/_template.md")
# Files the team customises per repo — never overwritten, even on --update
USER_OWNED = (".agents/config.toml", ".agents/risk-rules.json")


# ----------------------------------------------------------------------------- helpers
def git(*args: str, cwd: Path, check: bool = True) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed:\n{r.stderr.strip()}")
    return r.stdout.strip()


def say(msg: str = "") -> None:
    print(msg, flush=True)


def files_under(rel: str) -> list[tuple[Path, str]]:
    """Expand a source path into (absolute source file, relative suffix) pairs."""
    p = SRC / rel
    if p.is_file():
        return [(p, "")]
    if not p.is_dir():
        raise SystemExit(f"forge source is missing {rel} — is {SRC} a complete inctec-forge checkout?")
    return [(f, str(f.relative_to(p))) for f in sorted(p.rglob("*"))
            if f.is_file() and "__pycache__" not in f.parts and not f.name.endswith(".pyc")]


def choose_agents_interactively() -> list[str]:
    say("Which coding agent(s) will this repo use? (comma-separated numbers or names)\n")
    for i, a in enumerate(AGENTS, 1):
        say(f"  {i}. {a:9} {AGENT_INFO[a]}")
    raw = input("\nagents [1]: ").strip() or "1"
    picked = []
    for tok in re.split(r"[,\s]+", raw):
        if tok.isdigit() and 1 <= int(tok) <= len(AGENTS):
            picked.append(AGENTS[int(tok) - 1])
        elif tok:
            picked.append(tok.lower())
    return picked


def parse_agents(value: str | None) -> list[str]:
    agents = [a.strip().lower() for a in value.split(",")] if value else choose_agents_interactively()
    agents = list(dict.fromkeys(a for a in agents if a))
    bad = [a for a in agents if a not in AGENTS]
    if bad or not agents:
        raise SystemExit(f"unknown agent(s): {', '.join(bad) or '(none)'}. Choose from: {', '.join(AGENTS)}")
    return agents


# ----------------------------------------------------------------------------- install steps
class Installer:
    def __init__(self, target: Path, agents: list[str], force: bool, update: bool) -> None:
        self.target, self.agents, self.force, self.update = target, agents, force, update
        self.written: list[str] = []
        self.conflicts: list[str] = []
        self.unchanged = 0

    def place(self, src: Path, rel: str) -> None:
        dst = self.target / rel
        if dst.exists():
            if dst.is_file() and filecmp.cmp(src, dst, shallow=False):
                self.unchanged += 1
                return
            managed = self.update and rel.startswith(MANAGED_PREFIXES) and rel not in USER_OWNED
            if not (self.force or managed) or rel in USER_OWNED:
                shutil.copy2(src, dst.with_name(dst.name + ".forge-new"))
                self.conflicts.append(rel)
                return
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        self.written.append(rel)

    def copy_set(self, pairs: list[tuple[str, str]]) -> None:
        for src_rel, dst_rel in pairs:
            for f, suffix in files_under(src_rel):
                self.place(f, f"{dst_rel}/{suffix}" if suffix else dst_rel)

    def configure_agents(self) -> None:
        cfg_path = self.target / ".agents" / "config.toml"
        text = cfg_path.read_text()
        listed = ", ".join(f'"{a}"' for a in self.agents)
        text = re.sub(r"(?m)^agents = \[.*\]", f"agents = [{listed}]", text, count=1)
        runtime = next((a for a in self.agents if a in FACTORY_RUNTIMES), None)
        if runtime:
            text = re.sub(r'(?m)^default_runtime = "\w+"', f'default_runtime = "{runtime}"', text, count=1)
        if text != cfg_path.read_text():
            cfg_path.write_text(text)
            if ".agents/config.toml" not in self.written:
                self.written.append(".agents/config.toml")

    def wire_repo(self) -> list[str]:
        notes = []
        gi = self.target / ".gitignore"
        lines = gi.read_text().splitlines() if gi.exists() else []
        if ".factory/" not in lines:
            gi.write_text("\n".join([*lines, "# IncTec Forge", ".factory/", ""]).lstrip("\n"))
            self.written.append(".gitignore")
        current = git("config", "--get", "core.hooksPath", cwd=self.target, check=False)
        if (self.target / ".husky").exists() or (current and current != "scripts/githooks"):
            notes.append(f"Existing git hooks setup found ({current or '.husky'}) — not changed. Call "
                         "scripts/githooks/pre-commit and pre-push from your hooks to get the forge guardrails.")
        else:
            git("config", "core.hooksPath", "scripts/githooks", cwd=self.target)
        for p in [*self.target.joinpath("scripts").rglob("*.py"), *self.target.joinpath("scripts/githooks").glob("*"),
                  *self.target.joinpath("factory").glob("*.py"), *self.target.joinpath(".claude/hooks").glob("*.py")]:
            if p.is_file():
                p.chmod(p.stat().st_mode | 0o111)
        return notes

    def build_adapters(self) -> None:
        r = subprocess.run([sys.executable, "scripts/sync_agents.py", "--quiet"], cwd=self.target,
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"building agent adapters failed:\n{r.stdout}{r.stderr}")

    def write_lock(self) -> None:
        sha = git("rev-parse", "--short", "HEAD", cwd=SRC, check=False) or "unknown"
        path = self.target / ".agents" / "forge.lock.json"
        old = json.loads(path.read_text()) if path.exists() else {}
        if old.get("forge_commit") == sha and old.get("agents") == self.agents and not self.written:
            return  # nothing changed — keep the file identical so re-runs are a no-op
        lock = {"forge_commit": sha, "agents": self.agents,
                "installed_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds")}
        path.write_text(json.dumps(lock, indent=2) + "\n")

    def commit(self, branch: str) -> str | None:
        """Commit the forge files on `branch`. Returns the branch name, or None if nothing to commit."""
        t = self.target
        current = git("rev-parse", "--abbrev-ref", "HEAD", cwd=t, check=False)
        has_commits = bool(git("rev-parse", "--verify", "HEAD", cwd=t, check=False))
        if has_commits and current != branch:
            exists = git("rev-parse", "--verify", f"refs/heads/{branch}", cwd=t, check=False)
            git("switch", branch, cwd=t) if exists else git("switch", "-c", branch, cwd=t)
        elif not has_commits:
            git("switch", "-c", branch, cwd=t, check=False)
        # Stage only what the installer produced, never the user's unrelated work.
        paths = ["AGENTS.md", ".agents", "docs/engineering", "docs/adr/0000-template.md", "docs/design/_template.md",
                 "scripts", "factory", ".github", "Makefile", ".pre-commit-config.yaml", "docker-compose.dev.yml",
                 "observability", ".gitignore", "CLAUDE.md", ".claude", ".gemini", ".aider.conf.yml"]
        existing = [p for p in paths if (t / p).exists()]
        git("add", "--", *existing, cwd=t)
        conflict_copies = [str(p.relative_to(t)) for p in t.rglob("*.forge-new") if ".git" not in p.parts]
        if conflict_copies:  # never call `git reset --` with no paths: that unstages everything
            git("reset", "-q", "--", *conflict_copies, cwd=t, check=False)
        if not git("diff", "--cached", "--name-only", cwd=t):
            return None
        verb = "update" if self.update else "add"
        msg = (f"chore: {verb} IncTec Forge setup (agents: {', '.join(self.agents)})\n\n"
               f"Installed from inctec-forge {json.loads((t / '.agents/forge.lock.json').read_text())['forge_commit']}.\n"
               "Engineering constitution (AGENTS.md), roles and skills (.agents/), autonomy tiers with git hooks\n"
               "and CI, the software factory, and the dev/observability stack. See docs/engineering/.")
        r = subprocess.run(["git", "commit", "-q", "-m", msg], cwd=t, capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"commit was refused:\n{r.stderr or r.stdout}\nFiles are installed and staged; "
                             f"commit them yourself on '{branch}'.")
        return branch


# ----------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description="Install IncTec Forge into a git repository.")
    ap.add_argument("--agent", help=f"comma-separated: {', '.join(AGENTS)} (asks if omitted)")
    ap.add_argument("--target", default=".", help="repository to install into (default: current directory)")
    ap.add_argument("--branch", default="chore/forge-setup", help="branch to commit on (default: chore/forge-setup)")
    ap.add_argument("--no-commit", action="store_true", help="install but don't commit")
    ap.add_argument("--force", action="store_true", help="overwrite existing files instead of writing *.forge-new")
    ap.add_argument("--update", action="store_true",
                    help="re-apply the forge: refresh managed files (roles, skills, scripts, factory, docs); "
                         "your config.toml and risk-rules.json are kept")
    ap.add_argument("--list-agents", action="store_true", help="show supported agents and exit")
    a = ap.parse_args()

    if a.list_agents:
        for name in AGENTS:
            say(f"{name:9} {AGENT_INFO[name]}")
        return 0

    target = Path(a.target).resolve()
    if not (target / ".git").exists():
        raise SystemExit(f"{target} is not a git repository (run `git init` first or pass --target).")
    if target == SRC:
        raise SystemExit("Run this against your project repo, not the forge checkout itself (use --target).")

    if a.update and not a.agent and (target / ".agents/forge.lock.json").exists():
        agents = json.loads((target / ".agents/forge.lock.json").read_text())["agents"]
    else:
        agents = parse_agents(a.agent)

    say(f"\nIncTec Forge → {target}\nagents: {', '.join(agents)}\n")
    inst = Installer(target, agents, a.force, a.update)
    inst.copy_set(CORE)
    for agent in agents:
        inst.copy_set(PER_AGENT.get(agent, []))
    inst.configure_agents()
    notes = inst.wire_repo()
    inst.build_adapters()
    inst.write_lock()

    say(f"  {len(inst.written)} files written, {inst.unchanged} already up to date")
    for agent in agents:
        say(f"  ✓ {agent:9} {AGENT_INFO[agent]}")
    if inst.conflicts:
        say(f"\n  {len(inst.conflicts)} file(s) already existed — the forge version is next to them as *.forge-new:")
        for c in inst.conflicts[:15]:
            say(f"    {c}")
        if len(inst.conflicts) > 15:
            say(f"    … and {len(inst.conflicts) - 15} more")
    for n in notes:
        say(f"\n  ! {n}")

    if a.no_commit:
        say("\nNot committed (--no-commit). Review with `git status`.")
    else:
        branch = inst.commit(a.branch)
        if branch:
            say(f"\nCommitted on branch '{branch}'. Next:\n  git push -u origin {branch}   # then open a PR")
        else:
            say("\nNothing new to commit — this repo already has this forge version.")

    say("\nThen, once merged:")
    say("  • Merge docs/engineering/pyproject.tooling.toml into pyproject.toml; rename .github/CODEOWNERS.example")
    say("  • Protect main on GitHub: require PR + review + checks (lint, test, risk-tier, agents-sync)")
    say("  • Try the factory offline:  python3 factory/run.py new \"smoke test\" --runtime stub")
    if not any(x in FACTORY_RUNTIMES for x in agents):
        say("  • Your agent has no headless CLI preset, so the factory keeps its default runtime — set "
            "default_runtime in .agents/config.toml if you want to run it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
