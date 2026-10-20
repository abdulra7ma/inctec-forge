---
name: review
description: Self-review the current branch before shipping by spawning the reviewer agent (and security-reviewer when relevant) in a fresh context. Use after implementing, or when asked to review a branch or PR.
---
# /review

1. Make sure work is committed on a feature branch and `make check` passes.
2. Spawn the `code-reviewer` agent with: the task statement, link to design note (if any), and "review `origin/main...HEAD`".
   It has not seen your work — that's the point. Don't pre-justify your choices in the prompt.
3. If the diff touches frontend files → also spawn `ux-reviewer` and `ui-reviewer` (in parallel).
   No sub-agents in your tool? Run `python3 factory/run.py` instead, or ask the human to run a second tool as reviewer —
   self-review in the same context is the weakest option.
4. If the diff touches auth, permissions, input parsing, uploads, secrets, external integrations or exports →
   also spawn `security-reviewer`.
5. Triage the result:
   - Blockers → fix, re-run `make check`, re-run `/review` (max 2 loops, then escalate to the human with both reviews).
   - Should-fix → fix, or record in the PR under "Deferred" with reason.
   - Nits → fix if trivial.
   - ESCALATE TO HUMAN → stop and surface the review verbatim.
6. Paste the final verdict summary into the PR description.

Reviewing someone else's PR: `gh pr checkout <n>`, then the same steps; post findings with `gh pr review --comment` (never `--approve` — approval is human).
