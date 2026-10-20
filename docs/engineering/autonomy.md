# Autonomy Policy — when agents act alone and when humans decide

The goal: agents move fast on cheap, reversible work and slow down exactly where mistakes are expensive.
The tier is computed from the **actual diff** by `scripts/risk_tier.py` (rules in `.agents/risk-rules.json`),
then CI labels the PR `tier:T0`…`tier:T3`. An agent may argue a tier *up*, never *down*.

## The two questions behind every tier
1. **Blast radius** — if this is wrong, who notices? (one function → one team → customers → everyone)
2. **Reversibility** — can we undo it with a revert in minutes, or does it leave a mark (data, contracts, money, trust)?

Low radius + reversible → T0/T1. High radius or irreversible → T2/T3.

## Tiers

### T0 — Agent autonomous
Docs, tests-only changes, comments, formatting, typo fixes, generated client regeneration with no API change.
- Agent: branch, commit, open PR (non-draft).
- CI: may auto-merge on green if the repo enables it.
- Human: weekly spot-check of merged T0 PRs.

### T1 — Agent builds, human approves
Ordinary features and bug fixes inside existing modules and existing contracts.
- Agent: branch, commit, open PR with summary + test evidence.
- Human: one approving review. Reviewer reads tests first, then the diff.

### T2 — Human shapes, agent builds
Anything touching: DB migrations, auth/permissions, public API schemas, event/message schemas,
dependencies & lockfiles, CI workflows, Dockerfiles/compose, infra code, or a diff > 400 changed lines.
- Agent: must have run `/grill` and written a design note in `docs/design/` **before** implementation.
- Agent: opens a **draft** PR linking the design note; includes rollback plan.
- Human: code owner approves the design note first, then the code. Migrations need an explicit
  "expand/contract" statement (see `postgres-migrations` skill).

### T3 — Human drives
Production infrastructure, secrets/credentials, destructive data operations (DROP, TRUNCATE, bulk DELETE,
backfills on prod), payments/billing, irreversible migrations, anything touching customer data exports.
- Agent: may investigate, write a plan, and produce a patch **in the PR description or a `.patch` file**.
- Agent: may not `git commit` T3 changes (the commit hook blocks it) and may not execute against prod.
- Human: reviews the plan, applies it, runs it, and stays for verification.

## Things no agent does, at any tier
- Push or merge to protected branches; force-push; `--no-verify`.
- Read `.env*`, key files, or secrets stores; paste tokens into code, logs, or PRs.
- Run `terraform apply/destroy`, `kubectl apply/delete`, `helm upgrade/uninstall`, `alembic downgrade`, or DDL against shared databases.
- Disable, skip, or weaken a test to make CI pass (`skip`, `xfail`, loosening assertions) without saying so in the PR.
- Merge its own PR (CI auto-merge for T0 is the only exception).

## Escalation triggers (stop, write down state, ask)
- Tier goes up mid-task (e.g. you discover a migration is needed) → pause, tell the human, grill, design.
- Two failed attempts at the same fix.
- Flaky test you can't explain.
- Anything that "works" but you can't explain why.

## PR description contract (agents fill this in)
- **What & why** (2–4 sentences, user-facing impact first)
- **Tier** + the classifier's reasons; if you raised it, say why
- **How tested** — commands run, new tests, manual checks
- **Risk & rollback** — what breaks if wrong, how to undo
- **Open questions** — anything you guessed
