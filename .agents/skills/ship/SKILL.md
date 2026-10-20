---
name: ship
description: Commit and open a PR according to the autonomy tier of the actual diff. Use when work is reviewed and ready, or when asked to commit, push, open a PR, or ship.
---
# /ship

1. Preconditions: on a non-protected branch; `make check` green; `/review` verdict APPROVE (or fixes applied).
2. Classify the real change:
   ```
   python3 scripts/risk_tier.py --base origin/main
   ```
3. Act by tier:

| Tier | Commit | Push | PR |
|---|---|---|---|
| T0 | yes | yes | `gh pr create` (ready), label `tier:T0` |
| T1 | yes | yes | `gh pr create` (ready), label `tier:T1`, request reviewer from CODEOWNERS |
| T2 | yes | yes | `gh pr create --draft`, label `tier:T2`, link design note, tag code owner, include rollback plan |
| T3 | **no** | **no** | write `docs/design/<slug>.patch` or the plan in a draft PR from a human; tell the human exactly what to run and verify |

4. Commits: Conventional Commits (`feat(alerts): dedupe webhook retries`), imperative, ≤ 72 chars subject, body says *why*.
   One logical change per commit. Never `--no-verify`, never amend pushed commits, never force-push.
5. PR body: use `.github/pull_request_template.md`; fill every section — especially Tier reasons, How tested, Risk & rollback.
6. Never merge. Report the PR URL and what the human needs to do next.
