#!/usr/bin/env python3
"""Offline stand-in for an agent CLI, for testing the factory without model calls.

Scenario via env STUB_SCENARIO:
  pass (default) · changes-once (code review fails round 1) · always-changes · escalate (approver) · blocked-spec
  · destructive (builder attempts a T3 migration)
Builder output file via STUB_BUILD_PATH (default docs/stub-feature.md → T0; use app/x.py for T1).
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

prompt = Path(sys.argv[1]).read_text()
role = re.search(r"^# Role: (\S+)", prompt, re.M).group(1)
rnd = int(re.search(r"round: (\d+)", prompt).group(1))
scenario = os.environ.get("STUB_SCENARIO", "pass")

if role == "spec-writer":
    p = Path("docs/specs/stub-spec.md")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("# Spec\n## Goal\nStub.\n## Acceptance criteria\n1. File exists.\n")
    blocked = scenario == "blocked-spec"
    print(json.dumps({"spec_path": str(p), "predicted_tier": "T1", "blocked": blocked,
                      "blocking_questions": ["Which tenant model?"] if blocked else []}))
elif role == "builder":
    target = Path(os.environ.get("STUB_BUILD_PATH", "docs/stub-feature.md"))
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a") as fh:
        fh.write(f"# change from builder round {rnd}\n")
    if scenario == "destructive":  # tries to sneak in a T3 migration; hooks must refuse the commit
        (Path("migrations/versions")).mkdir(parents=True, exist_ok=True)
        Path("migrations/versions/drop_legacy.py").write_text("op.drop_column('devices', 'legacy')\n")
        subprocess.run(["git", "add", "-A"], check=True)
        r = subprocess.run(["git", "commit", "-qm", "feat: drop legacy"], capture_output=True, text=True)
        print(json.dumps({"status": "done", "summary": "attempted", "notes": r.stderr[-200:]}))
        sys.exit(0)
    subprocess.run(["git", "add", "-A"], check=True)
    subprocess.run(["git", "commit", "-qm", f"feat: stub build round {rnd}"], check=True)
    print(json.dumps({"status": "done", "summary": f"round {rnd}", "acceptance_criteria_covered": [1]}))
elif role.endswith("-reviewer"):
    bad = (role == "code-reviewer" and ((scenario == "changes-once" and rnd == 1) or scenario == "always-changes"))
    findings = [{"severity": "blocker", "file": "x", "line": 1, "issue": "stub issue", "fix": "stub fix"}] if bad else []
    print("Some reviewer chatter first…")
    print(json.dumps({"reviewer": role, "verdict": "CHANGES" if bad else "PASS", "findings": findings}))
elif role == "approver":
    d = "ESCALATE" if scenario == "escalate" else "APPROVE"
    print(json.dumps({"decision": d, "reasons": [f"stub {d.lower()}"], "human_should_check": []}))
