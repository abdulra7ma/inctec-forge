#!/usr/bin/env python3
"""Classify a git change into autonomy tiers T0-T3 (see docs/engineering/autonomy.md).

Usage:
  python3 scripts/risk_tier.py                     # working tree vs HEAD (staged + unstaged)
  python3 scripts/risk_tier.py --staged            # what `git commit` would commit
  python3 scripts/risk_tier.py --base origin/main  # branch vs base (what a PR contains)
  add --json for machine-readable output. Exit code = tier number (0-3).
Rules live in .agents/risk-rules.json. Stdlib only.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RULES_PATH = ROOT / ".agents" / "risk-rules.json"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False).stdout


def diff_args(base: str | None, staged: bool) -> list[str]:
    if staged:
        return ["--cached"]
    if base:
        return [f"{base}...HEAD"]
    return ["HEAD"]


def matches(path: str, patterns: list[str]) -> str | None:
    for pat in patterns:
        candidates = {pat, pat.removeprefix("**/")}
        if any(fnmatch.fnmatch(path, c) for c in candidates):
            return pat
        if pat.startswith("**/") and fnmatch.fnmatch(Path(path).name, pat.removeprefix("**/")):
            return pat
    return None


def added_lines(diff_text: str, skip: list[str]) -> str:
    """Added lines from the diff, excluding files matching `skip` (docs/prose, where words like DROP TABLE are harmless)."""
    out, current_skipped = [], False
    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            path = line[4:].removeprefix("b/")
            current_skipped = path == "/dev/null" or matches(path, skip) is not None
        elif line.startswith("+") and not current_skipped:
            out.append(line[1:])
    return "\n".join(out)


def classify(files: list[str], changed_lines: int, added: str, rules: dict) -> tuple[int, list[str]]:
    reasons: list[str] = []
    tier = 1

    for f in files:
        if pat := matches(f, rules["T3"]["paths"]):
            reasons.append(f"T3 path: {f} (rule {pat})")
    for rx in rules["T3"]["diff_patterns"]:
        if re.search(rx, added, flags=re.IGNORECASE):
            reasons.append(f"T3 destructive pattern in diff: /{rx}/")
    if reasons:
        return 3, reasons

    for f in files:
        if pat := matches(f, rules["T2"]["paths"]):
            reasons.append(f"T2 path: {f} (rule {pat})")
    if changed_lines > rules["T2"]["max_changed_lines"]:
        reasons.append(f"T2 size: {changed_lines} changed lines > {rules['T2']['max_changed_lines']}")
    if reasons:
        return 2, reasons

    if files and all(matches(f, rules["T0"]["paths"]) for f in files):
        return 0, ["T0: only docs/tests/generated files changed"]

    if not files:
        return 0, ["no changes"]
    return tier, [f"T1: {len(files)} file(s), {changed_lines} changed lines, no T0/T2/T3 rules matched"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base")
    ap.add_argument("--staged", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    rules = json.loads(RULES_PATH.read_text())
    d = diff_args(a.base, a.staged)
    files = [f for f in git("diff", "--name-only", *d).splitlines() if f]
    if not a.staged and not a.base:  # include untracked files in working-tree mode
        files += [f for f in git("ls-files", "--others", "--exclude-standard").splitlines() if f]
    changed = 0
    for row in git("diff", "--numstat", *d).splitlines():
        parts = row.split("\t")
        if len(parts) == 3 and parts[0].isdigit():
            changed += int(parts[0]) + int(parts[1])
    prose = rules["T3"].get("diff_patterns_ignore", ["**/*.md", "docs/**", ".agents/skills/**", ".agents/roles/**"])
    tier, reasons = classify(sorted(set(files)), changed, added_lines(git("diff", *d), prose), rules)

    if a.json:
        print(json.dumps({"tier": f"T{tier}", "reasons": reasons, "files": len(set(files)), "changed_lines": changed}))
    else:
        print(f"Tier: T{tier}")
        for r in reasons:
            print(f"  - {r}")
    return tier


if __name__ == "__main__":
    sys.exit(main())
