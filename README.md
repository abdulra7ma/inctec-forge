# IncTec Forge

IncTec's engineering system. Drop it into any repo and an engineer — human or agent, using **any** coding tool and **any** model — can start
building immediately with the same taste, workflow, toolchain, and clear rules about what agents may do alone.

## Install
```bash
./install.sh /path/to/your/repo     # never overwrites; conflicts are written as *.devkit for manual merge
```
Commit the result on a branch and open a PR — the git hooks it installs already refuse direct commits to `main`.

## Vendor-neutral by design
```
AGENTS.md                ← the constitution. Read natively by Codex, Cursor, Copilot, opencode, Gemini (via .gemini/settings.json), …
CLAUDE.md                ← one line: @AGENTS.md (+ Claude notes)
.agents/
  roles/*.md             ← 13 role prompts with neutral frontmatter: tier (reasoning|fast), access (read|write|docs)
  skills/*/SKILL.md      ← 15 skills in the open SKILL.md format
  config.toml            ← runtimes (claude, codex, gemini, opencode, aider, stub), tier→model per runtime, per-role overrides, factory settings
  risk-rules.json        ← what makes a change T0/T1/T2/T3
scripts/sync_agents.py   ← generates .claude/agents, .claude/skills, .gemini/settings.json (CI fails on drift)
```
Edit only `.agents/` and `AGENTS.md`, then run `make agents-sync`. Swap models by editing one line in `config.toml`.
Mix vendors per role, e.g. build with Claude and review with Codex — a different model family catches different mistakes.

## The software factory
```
feature → spec-writer → builder ⇄ reviewers [code · security · ux* · ui*]  (max 2 fix rounds)
                                      → approver ─┬─ APPROVE + tier allows (T0) → PR with auto-merge (CI + branch protection still gate it)
                                                  └─ ESCALATE / T1+ / blocked   → draft PR labelled factory:needs-human
* only when frontend files change
```
```bash
make factory f="Add status filter to GET /devices"      # or: python3 factory/run.py new "..." --runtime codex
make factory-status                                      # what's running, what needs a human and why
python3 factory/run.py approve <run-id>                  # HUMAN ONLY (refuses agent sessions)
python3 factory/run.py new "smoke test" --runtime stub   # offline dry run, no model calls
```
- Each run gets its own **git worktree + branch**, so several features can run in parallel.
- The **orchestrator owns facts** (runs `make check`, computes the tier, builds the diff); agents own judgment.
  Green reviews never override red checks.
- The approver **cannot override policy**: only tiers in `auto_merge_tiers` (default `["T0"]`) auto-merge.
- A builder that tries to commit a T3 change (e.g. `DROP COLUMN`) is stopped by the git hook; the change is saved as `uncommittable.patch` for a human.
- Everything is recorded in `.factory/runs/<id>/` (prompts, logs, reviews per round, approver decision).
- Interactive alternative: the `factory` skill runs the same pipeline with your tool's sub-agents.
- CLI flags in `config.toml` differ between agent tools and change across versions — check `<cli> --help` after upgrades.

## Autonomy tiers — enforced in every tool
| Tier | Example | Agent | Human |
|---|---|---|---|
| T0 | docs, tests only | commit + PR; factory may auto-merge | spot-check |
| T1 | normal feature/fix | commit + PR | 1 approval |
| T2 | migrations, auth, contracts, Temporal workflows, deps, CI, infra, agent config, >400 lines | design note + draft PR | code owner |
| T3 | prod infra, secrets, DROP/TRUNCATE, payments | propose only | commits & executes |

Layers: **git hooks** (`scripts/githooks/`, work with any tool; agents are detected via `AI_AGENT=1` or known agent env vars, so
set `AI_AGENT=1` in any agent tool that isn't auto-detected) · **CI** (`risk-tier` labels PRs and requires design notes for T2+;
`agents-sync` drift check) · **GitHub branch protection** · tool-specific extras (`.claude/hooks/guard_bash.py` blocks destructive shell commands before they run).

## Stack coverage — `docs/engineering/toolchain.md`
Plan → develop → CI → test → staging → production → monitor → incident, with the default and allowed-alternative tool per stage.
- **Background work** skill: BackgroundTasks vs **Celery** vs **Temporal** decision table and production patterns (idempotency, retries, workflow determinism and versioning, testing).
- **Observability** skill: OpenTelemetry → **VictoriaMetrics / Loki / Tempo → Grafana**, Sentry, SLO burn-rate alerting, dashboards and alerts as code.
- `docker-compose.dev.yml`: `make dev` (app, Celery worker, Postgres, Redis) · `make dev-obs` (+ full Grafana stack, datasources pre-wired so logs ↔ traces ↔ metrics link) · `make dev-temporal` (+ Temporal and its UI).

## Contents
| Path | Purpose |
|---|---|
| `AGENTS.md` | Constitution: stack, non-negotiables, skills, roles, loop, tiers, when to ask |
| `docs/engineering/` | `autonomy.md`, `taste.md`, `decision-making.md`, `toolchain.md` |
| `docs/adr/`, `docs/design/` | ADR and design-note templates (specs go to `docs/specs/`) |
| `.agents/roles/` | spec-writer, architect, griller, builder, backend/frontend/devops/test engineers, code/security/ux/ui reviewers, approver |
| `.agents/skills/` | workflow: build-feature, grill, design-doc, review, ship, debug, factory · domain: fastapi-backend, postgres-migrations, background-work, testing, frontend, devops, observability, system-design |
| `factory/` | `run.py` orchestrator + `stub_agent.py` for offline tests |
| `scripts/` | `risk_tier.py`, `sync_agents.py`, `githooks/` |
| `.github/` | CI, PR template, CODEOWNERS example |
| `templates/` | Makefile, compose stack, observability configs, ruff/mypy/pytest config, pre-commit |

## Rolling it out
1. Week 1: install in one active repo. Leads run tasks through `build-feature`; try the factory on T0/T1 tickets.
2. Week 2: tune `risk-rules.json` from real misclassifications; choose models per role in `config.toml`.
3. Week 3+: roll out to other repos; weekly 30-minute taste review of 2 merged PRs.
4. Same review comment twice → it becomes a line in `taste.md` or a skill. That's how the system learns.
