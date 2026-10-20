# Engineering Constitution (AGENTS.md)

This is the single source of truth for every coding agent in this repo — Claude Code, Codex, Gemini CLI, Cursor,
Copilot, opencode, Aider, or a human. Tool-specific files (CLAUDE.md, .gemini/settings.json, …) only point here.
It is short on purpose. Details live in `docs/engineering/` and in `.agents/skills/` — read them when the task touches them.

## Stack (defaults — deviate only with an ADR)
- Backend: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x (async), Alembic, PostgreSQL, Redis
- Background work: Celery (task queue) or Temporal (durable workflows) — choose with `.agents/skills/background-work`
- Tooling: `uv`, `ruff`, `mypy --strict` on `app/`, `pytest` + `pytest-asyncio`
- Frontend: TypeScript (strict), React, Vite or Next.js, TanStack Query, Tailwind, Vitest + Playwright
- Infra: Docker (multi-stage, non-root), docker-compose locally, GitHub Actions CI
- Observability: OpenTelemetry → VictoriaMetrics (metrics), Loki (logs), Tempo (traces), Grafana (dashboards + alerting), Sentry (errors)
- Full stage-by-stage tool map (dev → staging → prod → monitoring): `docs/engineering/toolchain.md`

## Non-negotiables
1. Never commit or push to `main`/`master`/`release/*`. Work on `feat/…`, `fix/…`, `chore/…`, `factory/…` branches.
2. Never read, print, or commit secrets. `.env*` files are off-limits. Config comes from env vars via `pydantic-settings`.
3. Every behaviour change ships with a test that fails without the change.
4. `make check` (lint + types + tests) must be green before any commit.
5. Classify risk before writing code: `python3 scripts/risk_tier.py`. The tier decides who signs off — see below.
6. If you are unsure whether something is reversible, treat it as irreversible and ask.

## Skills (in `.agents/skills/<name>/SKILL.md` — open them when relevant)
Workflow: `build-feature` · `grill` · `design-doc` · `review` · `ship` · `debug` · `factory`
Domain: `fastapi-backend` · `postgres-migrations` · `background-work` · `testing` · `frontend` · `devops` · `observability` · `system-design`
In tools with slash commands these are `/build-feature`, `/grill`, … In other tools, read the SKILL.md and follow it.

## Roles (in `.agents/roles/`)
spec-writer · architect · griller · builder · backend-engineer · frontend-engineer · devops-engineer · test-engineer ·
code-reviewer · security-reviewer · ux-reviewer · ui-reviewer · approver.
If your tool supports sub-agents, delegate to the role. If not, adopt the role's instructions yourself for that phase.

## The loop (the `build-feature` skill runs this; the `factory` runs it unattended)
1. **Understand** — restate goal, user, constraint. Find code that already does half of it.
2. **Classify** — predict the risk tier from the files you expect to touch.
3. **Grill** — T2+ or ambiguous → `grill` before writing code.
4. **Spec / design** — every feature gets a spec; T2+ also a design note; architecture choices an ADR.
5. **Plan** — small, ordered, independently testable steps.
6. **Implement** — test first where practical; smallest diff that solves the problem.
7. **Review** — fresh-context reviewers (code, security, and UX/UI when frontend changes). Max 2 fix rounds.
8. **Ship** — `ship` re-classifies the real diff and commits / opens a PR per tier.

## Autonomy tiers (full policy: `docs/engineering/autonomy.md`)
| Tier | Typical change | Agent may | Human must |
|---|---|---|---|
| T0 | docs, tests only, comments, formatting | commit + PR; factory may auto-merge | spot-check weekly |
| T1 | normal feature/bugfix inside one module | commit + PR | 1 approving review |
| T2 | migrations, auth, API/event contracts, Temporal workflows, deps, CI, infra, >400 lines | branch + **draft** PR + design note | code-owner review + design approval |
| T3 | prod infra, secrets, destructive data ops, payments, irreversible migrations | propose only (plan/patch) | commit and execute themselves |

Enforced in three tool-independent layers: git hooks (`scripts/githooks/`), CI (`risk-tier` job), GitHub branch protection.
Some tools add their own layer (e.g. `.claude/hooks/`). Hooks are a seatbelt, not the driver.

## When to stop and ask the human
- Requirements conflict, or two reasonable readings lead to different designs.
- A public contract would change (API shape, event schema, DB column semantics, workflow signature).
- You need a new dependency, service, or infrastructure component.
- A test is failing and the honest fix is "change the test".
- You tried the same fix twice and it still fails — write down what you know, ask.

## Taste in one paragraph
Boring, obvious code beats clever code. Fewer moving parts beats more. Names say what things *are*.
Functions do one thing at one level of abstraction. Errors are handled where you can do something about them.
Delete code you don't need. Optimise for the engineer paged at 2 a.m. Full version: `docs/engineering/taste.md`.

## Commands
`make dev` (app) · `make dev-obs` (app + Grafana stack) · `make check` · `make test` · `make fmt` ·
`make migration m="msg"` · `make tier` · `make factory f="feature request"` · `python3 scripts/sync_agents.py` (after editing roles/skills)

## Where knowledge lives
`docs/engineering/` (taste, autonomy, decisions, toolchain) · `docs/adr/` · `docs/design/` · `docs/specs/` ·
`.agents/` (roles, skills, config, risk rules) · `factory/` (unattended pipeline)

## Learning and contributing
Guides (getting started, writing skills/roles, system design, reading list) and the contribution guide live in the
IncTec Forge repo: https://github.com/abdulra7ma/inctec-forge — improve the system there, then `python3 install.py --update`.
