#!/usr/bin/env python3
"""PostToolUse hook for Edit/Write: auto-format the touched file. Never blocks; formatting failures are ignored."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys

try:
    data = json.load(sys.stdin)
    path = (data.get("tool_input") or {}).get("file_path", "")
except Exception:
    sys.exit(0)

cmds: list[list[str]] = []
if path.endswith(".py"):
    runner = ["uv", "run", "--quiet"] if shutil.which("uv") else []
    if runner or shutil.which("ruff"):
        cmds += [[*runner, "ruff", "format", path], [*runner, "ruff", "check", "--fix", "--quiet", path]]
elif path.endswith((".ts", ".tsx", ".js", ".jsx", ".css", ".json", ".md", ".yml", ".yaml")):
    if shutil.which("npx"):
        cmds.append(["npx", "--no-install", "prettier", "--write", "--log-level", "silent", path])

for c in cmds:
    try:
        subprocess.run(c, capture_output=True, timeout=30, check=False)
    except Exception:
        pass
sys.exit(0)
