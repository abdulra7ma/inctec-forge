#!/usr/bin/env python3
"""PreToolUse hook for Bash: blocks commands that violate the autonomy policy.

Exit 2 + stderr = blocked; Claude sees the reason and must ask the human instead.
Seatbelt, not a sandbox: it catches the common mistakes, the policy still applies everywhere.
"""
from __future__ import annotations

import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

BLOCK_RULES: list[tuple[str, str]] = [
    (r"git\s+push\b.*(\s--force\b|\s-f\b|--force-with-lease)", "Force-push is never allowed for agents."),
    (r"--no-verify\b", "Skipping hooks (--no-verify) is not allowed."),
    (r"git\s+reset\s+--hard\b", "`git reset --hard` discards work. Ask the human first."),
    (r"git\s+clean\s+-\w*f", "`git clean -f` deletes untracked files. Ask the human first."),
    (r"git\s+branch\s+-D\b", "Force-deleting branches needs a human."),
    (r"factory/run\.py\s+approve\b", "Approving a factory run is a human decision."),
    (r"gh\s+pr\s+merge\b", "Agents never merge PRs. A human merges (CI may auto-merge T0)."),
    (r"gh\s+pr\s+review\b.*--approve", "Agents never approve PRs."),
    (r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f?[a-zA-Z]*\s+(/|~|\$HOME|\.\.|\*)", "Recursive delete outside the repo or of everything is blocked."),
    (r"\bterraform\s+(apply|destroy|import|state\s+rm)\b", "Terraform apply/destroy is T3: human only. `terraform plan` is fine."),
    (r"\bkubectl\s+(apply|delete|replace|patch|scale|rollout\s+undo|drain|cordon|exec)\b", "Mutating kubectl is T3: human only. `kubectl get/describe/diff` is fine."),
    (r"\bhelm\s+(install|upgrade|uninstall|rollback)\b", "Helm release changes are T3: human only. `helm template/diff` is fine."),
    (r"\balembic\s+downgrade\b", "alembic downgrade is destructive: human only."),
    (r"\b(psql|pgcli)\b.*\b(DROP|TRUNCATE|DELETE\s+FROM|ALTER\s+TABLE)\b", "DDL/destructive SQL via psql is T3: human only."),
    (r"(curl|wget)[^|]*\|\s*(sudo\s+)?(ba|z)?sh\b", "Piping downloads into a shell is blocked."),
    (r"(cat|less|head|tail|more|bat|cp|scp)\s+[^|;&]*\.env(\.|\s|$)", "Reading/copying .env files is not allowed."),
    (r"\b(printenv|env)\s*($|\|)", "Dumping the environment can leak secrets."),
    (r"\bdocker\s+(push|login)\b", "Pushing images / registry login is done by CI, not agents."),
]


def load_protected() -> list[str]:
    try:
        return json.loads((ROOT / ".agents" / "risk-rules.json").read_text())["protected_branches"]
    except Exception:
        return ["main", "master", "release/*"]


def current_branch() -> str:
    r = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    return r.stdout.strip()


def is_protected(branch: str, protected: list[str]) -> bool:
    return any(fnmatch.fnmatch(branch, p) for p in protected)


def block(msg: str) -> None:
    print(f"BLOCKED by autonomy policy: {msg}\nSee docs/engineering/autonomy.md. If this is truly needed, ask the human to do it.", file=sys.stderr)
    sys.exit(2)


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    cmd: str = (data.get("tool_input") or {}).get("command", "") or ""
    if not cmd.strip():
        sys.exit(0)

    for rx, msg in BLOCK_RULES:
        if re.search(rx, cmd, flags=re.IGNORECASE):
            block(msg)

    protected = load_protected()

    # Pushing to a protected branch, explicitly or implicitly
    for push in re.finditer(r"\bgit\s+push\b([^;&|]*)", cmd):
        tokens = [t for t in push.group(1).split() if not t.startswith("-")]
        refs = [t.split(":")[-1].removeprefix("refs/heads/") for t in tokens[1:]]  # tokens[0] is the remote
        if any(is_protected(r, protected) for r in refs) or is_protected(current_branch(), protected):
            block("Pushing to a protected branch is not allowed. Work on feat/…, fix/…, chore/… and open a PR.")

    # Committing: protected branch check + T3 check on the staged diff
    if re.search(r"\bgit\s+commit\b", cmd):
        if is_protected(current_branch(), protected):
            block(f"You are on protected branch '{current_branch()}'. Create a branch: git checkout -b feat/<slug>")
        # Commands like `git add -A && git commit` stage inside the same call; check staged + working tree to be safe.
        for mode in (["--staged"], []):
            r = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "risk_tier.py"), *mode, "--json"],
                cwd=ROOT, capture_output=True, text=True,
            )
            try:
                res = json.loads(r.stdout)
            except Exception:
                continue
            if res.get("tier") == "T3":
                block(
                    "This change is tier T3 (" + "; ".join(res.get("reasons", [])) + "). "
                    "Agents may not commit T3 changes. Write the plan/patch into docs/design/ and hand it to the human."
                )
    sys.exit(0)


if __name__ == "__main__":
    main()
