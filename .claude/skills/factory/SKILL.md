---
name: factory
description: Run the software factory — spec-writer → builder → parallel reviewers (code, security, UX, UI) with up to 2 fix rounds → approver → merge or needs-human. Use when asked to "run the factory", hand off a feature to be built unattended, or process a queue of features.
---
# Software factory

```
feature → spec-writer → builder ⇄ reviewers [code · security · ux* · ui*] (max 2 fix rounds) → approver
                                                                         ├─ APPROVE + tier allows → PR with auto-merge
                                                                         └─ ESCALATE / tier too high → needs-human (draft PR)
* UX/UI reviewers run only when frontend files change.
```

## Two ways to run it

### A. Headless orchestrator (any tool, any model, CI-friendly) — preferred for unattended work
```bash
make factory f="Add status filter to GET /devices"            # uses .agents/config.toml
python3 factory/run.py new "…" --runtime codex                # force one runtime for all roles
python3 factory/run.py status                                 # list runs; needs-human ones show the reason
python3 factory/run.py approve <run-id>                       # HUMAN ONLY — promotes a needs-human run
```
Mix vendors per role in `.agents/config.toml` → `[roles]` (e.g. build with Claude, review with Codex — a different model family catches different mistakes).
Each run gets its own git worktree and branch, so several features can run in parallel. Records live in `.factory/runs/<id>/`.

### B. Native, inside an interactive agent session
If you were asked to run the factory and your tool supports sub-agents, run the same pipeline yourself:
1. Delegate to `spec-writer` → read the spec. Blocked or predicted T3 → stop, report questions to the human.
2. Create branch `factory/<slug>`. Delegate to `builder` with the spec path.
3. Run `make check` and `python3 scripts/risk_tier.py --base main` **yourself** — don't trust the builder's claim.
4. Delegate **in parallel** to `code-reviewer`, `security-reviewer`, and (if frontend changed) `ux-reviewer`, `ui-reviewer`.
   Give them the spec, diff, tier and check result — not your opinion of the work.
5. Any CHANGES or failed checks → send findings back to `builder`. Max 2 fix rounds, then needs-human.
6. All PASS → delegate to `approver` with everything. Then apply the policy:
   APPROVE and tier ∈ auto-merge tiers (default T0) → `ship`; otherwise open a draft PR labelled `factory:needs-human`.
No sub-agent support? Prefer option A — playing every role in one context defeats the fresh-eyes reviews.

## Rules
- The orchestrator owns facts (checks, tier, diff); agents own judgment. The approver never overrides the autonomy policy.
- Never run `approve` from an agent; it refuses agent sessions. Merging stays a human/CI decision.
- Same finding twice across rounds → escalate; don't loop.
