#!/usr/bin/env python3
"""Software factory — model- and vendor-agnostic.

  feature → spec-writer → builder ⇄ parallel reviewers (max N fix rounds) → approver → merge | needs-human

Usage:
  python3 factory/run.py new "Add device status filter to /devices" [--runtime codex] [--slug device-filter]
  python3 factory/run.py status [RUN_ID]
  python3 factory/run.py approve RUN_ID        # HUMAN ONLY: promote a needs-human run to a mergeable PR
  python3 factory/run.py clean RUN_ID          # remove the run's worktree (keeps branch + run record)

Each run gets its own git worktree + branch (factory/<slug>-<id>), so several runs can go in parallel.
Agents are invoked through CLI templates in .agents/config.toml (claude, codex, gemini, opencode, aider, …).
The orchestrator — not the agents — runs checks, computes the risk tier, and decides merge eligibility.
Stdlib only, Python 3.11+.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import fnmatch
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / ".factory" / "runs"
WORKTREES = ROOT / ".factory" / "worktrees"
MAX_DIFF_CHARS = 60_000
AGENT_ENV_VARS = ("AI_AGENT", "CLAUDECODE", "CODEX_SANDBOX", "GEMINI_CLI")


# ----------------------------------------------------------------------------- helpers
def sh(cmd: str | list[str], cwd: Path, env: dict[str, str] | None = None, timeout: int | None = None,
       check: bool = False) -> subprocess.CompletedProcess[str]:
    shell = isinstance(cmd, str)
    r = subprocess.run(cmd, cwd=cwd, shell=shell, executable="/bin/bash" if shell else None, capture_output=True,
                       text=True, env=env, timeout=timeout)
    if check and r.returncode != 0:
        raise RuntimeError(f"command failed ({r.returncode}): {cmd}\n{r.stdout}\n{r.stderr}")
    return r


def git(*args: str, cwd: Path, check: bool = True) -> str:
    return sh(["git", *args], cwd=cwd, check=check).stdout.strip()


def log(msg: str) -> None:
    print(f"[factory] {msg}", flush=True)


def extract_json(text: str, required_key: str) -> dict[str, Any] | None:
    """Return the last JSON object in `text` that contains `required_key`."""
    dec = json.JSONDecoder()
    for i in range(len(text) - 1, -1, -1):
        if text[i] != "{":
            continue
        try:
            obj, _ = dec.raw_decode(text[i:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and required_key in obj:
            return obj
    return None


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "feature"


def matches_any(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, p) or fnmatch.fnmatch(path, p.removeprefix("**/")) for p in patterns)


# ----------------------------------------------------------------------------- config & roles
@dataclass
class Config:
    raw: dict[str, Any]
    runtime_override: str | None = None

    @property
    def factory(self) -> dict[str, Any]:
        return self.raw["factory"]

    def runtime_for(self, role: str) -> str:
        return self.runtime_override or self.raw.get("roles", {}).get(role) or self.raw["default_runtime"]


def load_config(runtime: str | None) -> Config:
    raw = tomllib.loads((ROOT / ".agents" / "config.toml").read_text())
    if runtime and runtime not in raw["runtimes"]:
        raise SystemExit(f"unknown runtime '{runtime}'. Known: {', '.join(raw['runtimes'])}")
    return Config(raw, runtime)


def load_role(name: str) -> tuple[dict[str, str], str]:
    text = (ROOT / ".agents" / "roles" / f"{name}.md").read_text()
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    assert m, f"role {name} has no frontmatter"
    meta = dict(line.split(": ", 1) for line in m.group(1).splitlines() if ": " in line)
    return meta, m.group(2).strip()


# ----------------------------------------------------------------------------- run state
@dataclass
class Run:
    id: str
    request: str
    branch: str
    worktree: str
    status: str = "running"           # running | merged | auto-merge-queued | needs-human | approved | failed
    stage: str = "spec"
    round: int = 0
    tier: str | None = None
    predicted_tier: str | None = None
    spec_path: str | None = None
    pr_url: str | None = None
    reason: str | None = None
    history: list[dict[str, Any]] = field(default_factory=list)

    @property
    def dir(self) -> Path:
        return RUNS / self.id

    @property
    def wt(self) -> Path:
        return Path(self.worktree)

    def event(self, stage: str, **data: Any) -> None:
        self.stage = stage
        self.history.append({"at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"), "stage": stage, **data})
        self.save()

    def save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "state.json").write_text(json.dumps(self.__dict__, indent=2))

    @classmethod
    def load(cls, run_id: str) -> Run:
        return cls(**json.loads((RUNS / run_id / "state.json").read_text()))


# ----------------------------------------------------------------------------- agent invocation
def invoke(cfg: Config, run: Run, role: str, task: str, tag: str) -> str:
    meta, body = load_role(role)
    rt_name = cfg.runtime_for(role)
    rt = cfg.raw["runtimes"][rt_name]
    model = rt.get("models", {}).get(meta["tier"], "")
    model_flag = rt["model_flag_template"].format(model=model) if model and rt.get("model_flag_template") else ""
    mode_flags = rt.get("write" if meta["access"].startswith("write") or meta["access"].startswith("docs") else "read_only", "")

    prompt = (
        f"# Role: {role}\n{body}\n\n"
        f"# Context\n- Read AGENTS.md in the repository root before anything else; it overrides your defaults.\n"
        f"- Factory run: {run.id} · branch: {run.branch} · round: {run.round}\n"
        f"- You are running unattended. Do not ask questions; state assumptions and follow your output contract.\n\n"
        f"# Task\n{task}\n"
    )
    pfile = run.dir / "prompts" / f"{tag}.md"
    pfile.parent.mkdir(parents=True, exist_ok=True)
    pfile.write_text(prompt)

    cmd = rt["command"].format(prompt_file=shlex.quote(str(pfile)), model_flag=model_flag, mode_flags=mode_flags)
    env = {**os.environ, "AI_AGENT": "1", "FACTORY_RUN_ID": run.id, "AGENT_ROLE": role}
    log(f"  → {role} via {rt_name}{f' ({model})' if model else ''}")
    try:
        r = sh(cmd, cwd=run.wt, env=env, timeout=cfg.factory.get("agent_timeout_seconds", 1800))
        out = r.stdout + ("\n[stderr]\n" + r.stderr if r.stderr.strip() else "")
    except subprocess.TimeoutExpired:
        out = f"[factory] {role} timed out"
    (run.dir / "logs").mkdir(exist_ok=True)
    (run.dir / "logs" / f"{tag}.log").write_text(out)
    return out


# ----------------------------------------------------------------------------- orchestrator steps
def commit_leftovers(run: Run, message: str) -> bool:
    """Commit anything the agent left uncommitted. Returns False if the commit hook refused (e.g. T3)."""
    if not git("status", "--porcelain", cwd=run.wt):
        return True
    git("add", "-A", cwd=run.wt)
    r = sh(["git", "commit", "-m", message], cwd=run.wt, env={**os.environ, "AI_AGENT": "1"})
    if r.returncode != 0:
        (run.dir / "uncommittable.patch").write_text(git("diff", "--cached", cwd=run.wt, check=False))
        run.reason = "commit refused by hooks: " + (r.stderr or r.stdout).strip()[-500:]
        return False
    return True


def assess(cfg: Config, run: Run) -> dict[str, Any]:
    """Orchestrator-owned facts: checks, tier, diff."""
    base = cfg.factory["base_branch"]
    check = sh(cfg.factory["check_command"], cwd=run.wt, env={**os.environ, "AI_AGENT": "1"}, timeout=1800)
    tier_raw = sh([sys.executable, "scripts/risk_tier.py", "--base", base, "--json"], cwd=run.wt).stdout
    tier = json.loads(tier_raw) if tier_raw.strip() else {"tier": "T3", "reasons": ["tier classifier failed"]}
    files = [f for f in git("diff", "--name-only", f"{base}...HEAD", cwd=run.wt).splitlines() if f]
    diff = git("diff", f"{base}...HEAD", cwd=run.wt)
    if len(diff) > MAX_DIFF_CHARS:
        diff = diff[:MAX_DIFF_CHARS] + f"\n… [diff truncated at {MAX_DIFF_CHARS} chars; read files directly]"
    run.tier = tier["tier"]
    return {
        "check_ok": check.returncode == 0,
        "check_tail": (check.stdout + check.stderr)[-4000:],
        "tier": tier,
        "files": files,
        "stat": git("diff", "--stat", f"{base}...HEAD", cwd=run.wt),
        "diff": diff,
    }


def facts_block(run: Run, facts: dict[str, Any]) -> str:
    spec = (run.wt / run.spec_path).read_text() if run.spec_path and (run.wt / run.spec_path).exists() else "(no spec file)"
    return (
        f"## Spec ({run.spec_path})\n{spec}\n\n"
        f"## Risk tier (computed by orchestrator)\n{json.dumps(facts['tier'])}\n\n"
        f"## Checks (`make check`, run by orchestrator): {'PASS' if facts['check_ok'] else 'FAIL'}\n"
        f"```\n{facts['check_tail'] if not facts['check_ok'] else 'ok'}\n```\n\n"
        f"## Diff stat\n```\n{facts['stat']}\n```\n\n## Diff\n```diff\n{facts['diff']}\n```\n"
    )


def run_reviews(cfg: Config, run: Run, facts: dict[str, Any]) -> list[dict[str, Any]]:
    selected = [r["role"] for r in cfg.factory["reviewers"] if any(matches_any(f, r["when"]) for f in facts["files"])]
    task = "Review this change against your checklist and the spec.\n\n" + facts_block(run, facts)
    results: list[dict[str, Any]] = []
    with cf.ThreadPoolExecutor(max_workers=max(1, len(selected))) as pool:
        futures = {pool.submit(invoke, cfg, run, role, task, f"r{run.round}-{role}"): role for role in selected}
        for fut in cf.as_completed(futures):
            role = futures[fut]
            parsed = extract_json(fut.result(), "verdict")
            if parsed is None or parsed.get("verdict") not in ("PASS", "CHANGES"):
                parsed = {"reviewer": role, "verdict": "ERROR", "findings": [{"severity": "blocker",
                          "issue": "reviewer output missing/unparseable — see logs"}]}
            parsed["role"] = role
            results.append(parsed)
    (run.dir / f"reviews-r{run.round}.json").write_text(json.dumps(results, indent=2))
    return sorted(results, key=lambda r: r["role"])


def summarize_reviews(reviews: list[dict[str, Any]]) -> str:
    parts = []
    for r in reviews:
        n = sum(1 for f in r.get("findings", []) if f.get("severity") == "blocker")
        parts.append(f"{r['role'].removesuffix('-reviewer')}:{r['verdict']}{f'({n} blockers)' if n else ''}")
    return " ".join(parts) or "(no reviewers matched the changed files)"


def publish(cfg: Config, run: Run, *, auto_merge: bool, draft: bool, body_extra: str) -> None:
    """Push branch and open PR. Degrades gracefully without a remote or gh."""
    if not cfg.factory.get("open_pr", True):
        run.reason = (run.reason or "") + " [open_pr=false: branch kept local]"
        return
    if not git("remote", cwd=run.wt, check=False) or not shutil.which("gh"):
        run.reason = (run.reason or "") + " [no git remote or gh CLI: branch kept local]"
        return
    env = {**os.environ, "AI_AGENT": "1"}
    sh(["git", "push", "-u", "origin", run.branch], cwd=run.wt, env=env, check=True)
    title = f"{'feat' if run.tier != 'T0' else 'docs'}: {run.request[:60]}"
    labels = [f"tier:{run.tier}", "factory" if auto_merge else "factory:needs-human"]
    body = (f"Factory run `{run.id}` · tier **{run.tier}** · spec: `{run.spec_path}`\n\n{body_extra}\n\n"
            f"Full record: `.factory/runs/{run.id}/` on the machine that ran it.")
    args = ["gh", "pr", "create", "--base", cfg.factory["base_branch"], "--head", run.branch, "--title", title, "--body", body]
    for lab in labels:
        args += ["--label", lab]
    if draft:
        args.append("--draft")
    r = sh(args, cwd=run.wt, env=env)
    if r.returncode != 0:  # labels may not exist yet — retry without them
        args = [a for i, a in enumerate(args) if a != "--label" and (i == 0 or args[i - 1] != "--label")]
        r = sh(args, cwd=run.wt, env=env, check=True)
    run.pr_url = r.stdout.strip().splitlines()[-1]
    if auto_merge:
        # Branch protection + required CI still apply; GitHub merges only when they pass.
        sh(["gh", "pr", "merge", run.pr_url, "--auto", "--squash"], cwd=run.wt, env=env, check=True)


def needs_human(cfg: Config, run: Run, reason: str, body_extra: str = "", publish_pr: bool = True) -> None:
    run.status, run.reason = "needs-human", reason
    log(f"NEEDS HUMAN — {reason}")
    if publish_pr:
        try:
            publish(cfg, run, auto_merge=False, draft=True, body_extra=f"**Escalated:** {reason}\n\n{body_extra}")
        except Exception as e:  # noqa: BLE001
            run.reason += f" [PR not opened: {e}]"
    run.event("needs-human", reason=run.reason, pr=run.pr_url)
    log(f"Review it, then a human runs: python3 factory/run.py approve {run.id}")


# ----------------------------------------------------------------------------- pipeline
def cmd_new(args: argparse.Namespace) -> int:
    cfg = load_config(args.runtime)
    f = cfg.factory
    slug = args.slug or slugify(args.request)
    run_id = f"{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}-{slug}"
    branch = f"factory/{slug}-{run_id[9:15]}"
    wt = WORKTREES / run_id
    WORKTREES.mkdir(parents=True, exist_ok=True)
    git("worktree", "add", "-b", branch, str(wt), f["base_branch"], cwd=ROOT)
    run = Run(id=run_id, request=args.request, branch=branch, worktree=str(wt))
    run.event("start", request=args.request)
    log(f"run {run_id} on branch {branch}")

    # 1. Spec
    out = invoke(cfg, run, "spec-writer", f"Feature request:\n\n{args.request}\n\nToday is {dt.date.today()}.", "spec")
    spec = extract_json(out, "spec_path") or {}
    run.spec_path, run.predicted_tier = spec.get("spec_path"), spec.get("predicted_tier")
    if not run.spec_path or not (wt / run.spec_path).exists():
        needs_human(cfg, run, "spec-writer produced no spec file", publish_pr=False)
        return 2
    commit_leftovers(run, f"docs(spec): {slug}")
    run.event("spec", path=run.spec_path, predicted_tier=run.predicted_tier)
    log(f"spec: {run.spec_path} (predicted {run.predicted_tier})")
    if spec.get("blocked"):
        needs_human(cfg, run, "spec blocked on questions: " + "; ".join(spec.get("blocking_questions", [])))
        return 2
    if run.predicted_tier == "T3":
        needs_human(cfg, run, "predicted tier T3 — propose-only; a human must build/execute this")
        return 2

    # 2. Build ⇄ review loop
    findings_for_builder = ""
    for rnd in range(1, f["max_fix_rounds"] + 2):
        run.round = rnd
        task = (f"Implement the spec at `{run.spec_path}` (read it first).\n"
                if rnd == 1 else
                f"Round {rnd}: address these review findings / check failures on the current branch.\n\n{findings_for_builder}")
        out = invoke(cfg, run, "builder", task, f"r{rnd}-builder")
        b = extract_json(out, "status") or {}
        if not commit_leftovers(run, f"chore(factory): uncommitted builder changes r{rnd}"):
            needs_human(cfg, run, run.reason or "commit refused", publish_pr=False)
            return 2
        if b.get("status") == "blocked":
            needs_human(cfg, run, "builder blocked: " + str(b.get("notes") or b.get("summary")))
            return 2

        facts = assess(cfg, run)
        log(f"build r{rnd}: checks {'PASS' if facts['check_ok'] else 'FAIL'} · tier {run.tier} · {len(facts['files'])} files")
        if run.tier == "T3":
            needs_human(cfg, run, "computed tier is T3 — agents may not ship this", publish_pr=False)
            return 2

        reviews = run_reviews(cfg, run, facts)
        log(f"review r{rnd}: {summarize_reviews(reviews)}")
        run.event("review", round=rnd, checks=facts["check_ok"], tier=run.tier, summary=summarize_reviews(reviews))

        if any(r["verdict"] == "ERROR" for r in reviews):
            needs_human(cfg, run, "a reviewer failed to produce a valid verdict")
            return 2
        escalations = [x for r in reviews for x in r.get("findings", []) if str(x.get("issue", "")).startswith("ESCALATE")]
        if escalations:
            needs_human(cfg, run, "reviewer escalated: " + escalations[0]["issue"])
            return 2
        if facts["check_ok"] and all(r["verdict"] == "PASS" for r in reviews):
            break
        findings_for_builder = json.dumps([r for r in reviews if r["verdict"] != "PASS"], indent=2)
        if not facts["check_ok"]:
            findings_for_builder += f"\n\n`make check` FAILED:\n```\n{facts['check_tail']}\n```"
    else:
        needs_human(cfg, run, f"still failing after {f['max_fix_rounds']} fix rounds", body_extra=summarize_reviews(reviews))
        return 2

    # 3. Approver
    task = ("Decide APPROVE or ESCALATE for this change.\n\n## Reviews\n```json\n" + json.dumps(reviews, indent=2)
            + f"\n```\n\nRounds used: {run.round}\n\n" + facts_block(run, facts))
    decision = extract_json(invoke(cfg, run, "approver", task, "approver"), "decision") or {"decision": "ESCALATE",
                                                                                         "reasons": ["approver output unparseable"]}
    (run.dir / "approver.json").write_text(json.dumps(decision, indent=2))
    run.event("approver", **decision)
    log(f"approver: {decision['decision']} — {'; '.join(decision.get('reasons', []))[:200]}")

    note = "\n".join(f"- {x}" for x in decision.get("human_should_check", [])) or ""
    if decision["decision"] != "APPROVE":
        needs_human(cfg, run, "approver escalated: " + "; ".join(decision.get("reasons", [])), body_extra=note)
        return 2
    if run.tier not in f.get("auto_merge_tiers", []):
        needs_human(cfg, run, f"approved by agents, but tier {run.tier} requires human review per autonomy policy",
                    body_extra=note)
        return 2

    run.status = "auto-merge-queued"
    try:
        publish(cfg, run, auto_merge=True, draft=False, body_extra="Approved by factory (tier allows auto-merge).")
    except Exception as e:  # noqa: BLE001
        needs_human(cfg, run, f"publishing failed: {e}", publish_pr=False)
        return 2
    run.event("merge-queued", pr=run.pr_url, note=run.reason)
    log(f"APPROVED · {run.pr_url or 'branch ' + run.branch} · auto-merge once CI passes")
    return 0


# ----------------------------------------------------------------------------- human commands
def cmd_status(args: argparse.Namespace) -> int:
    if args.run_id:
        print(json.dumps(Run.load(args.run_id).__dict__, indent=2))
        return 0
    if not RUNS.exists():
        print("no runs yet")
        return 0
    for d in sorted(RUNS.iterdir()):
        r = Run.load(d.name)
        print(f"{r.id:45} {r.status:18} tier={r.tier or '-':3} round={r.round} {r.pr_url or r.branch}")
        if r.status == "needs-human":
            print(f"{'':45} ↳ {r.reason}")
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    if any(os.environ.get(v) for v in AGENT_ENV_VARS):
        print("✋ `approve` is a human decision and cannot be run from an agent session.", file=sys.stderr)
        return 1
    run = Run.load(args.run_id)
    if run.status != "needs-human":
        print(f"run is '{run.status}', not needs-human — nothing to approve")
        return 1
    if run.tier == "T3":
        print("T3 runs are propose-only: apply the plan yourself, commit as a human, open the PR.")
        return 1
    cfg = load_config(None)
    if run.pr_url:
        sh(["gh", "pr", "ready", run.pr_url], cwd=ROOT, check=True)
        sh(["gh", "pr", "edit", run.pr_url, "--remove-label", "factory:needs-human"], cwd=ROOT)
        print(f"PR marked ready: {run.pr_url}\nIt still needs your GitHub approval (and code-owner review for T2) before merge.")
    else:
        publish(cfg, run, auto_merge=False, draft=False, body_extra="Human-approved factory run.")
        print(f"PR opened: {run.pr_url or '(local branch ' + run.branch + ')'}")
    run.status = "approved"
    run.event("human-approved", by=os.environ.get("USER", "human"))
    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    run = Run.load(args.run_id)
    git("worktree", "remove", "--force", run.worktree, cwd=ROOT, check=False)
    print(f"removed worktree for {run.id}; branch {run.branch} kept")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("new")
    p.add_argument("request")
    p.add_argument("--runtime", help="force one runtime for every role (overrides config)")
    p.add_argument("--slug")
    p.set_defaults(fn=cmd_new)
    p = sub.add_parser("status")
    p.add_argument("run_id", nargs="?")
    p.set_defaults(fn=cmd_status)
    p = sub.add_parser("approve")
    p.add_argument("run_id")
    p.set_defaults(fn=cmd_approve)
    p = sub.add_parser("clean")
    p.add_argument("run_id")
    p.set_defaults(fn=cmd_clean)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
