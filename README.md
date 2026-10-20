# IncTec Forge

IncTec's engineering guideline, in a form both people and coding agents can follow. Install it into any repo, and an
engineer using **any** coding tool and **any** model can start building immediately — with the same taste, workflow,
toolchain, and clear rules about what agents may do alone and what needs a human.

## Install — one command

From the root of your project repo, name the agent(s) you use:

```bash
bash <(gh api repos/abdulra7ma/inctec-forge/contents/bootstrap.sh -H "Accept: application/vnd.github.raw") --agent claude
```

| `--agent` | What you get on top of the core |
|---|---|
| `claude` | `CLAUDE.md`, 13 sub-agents, slash-command skills, shell-command guard hook |
| `codex` · `cursor` · `copilot` · `opencode` | nothing extra — they read `AGENTS.md` and `.agents/skills/` natively |
| `gemini` | `.gemini/settings.json` so Gemini CLI loads `AGENTS.md` |
| `aider` | `.aider.conf.yml` that loads `AGENTS.md` |

Combine with commas (`--agent claude,cursor`), or leave it out to be asked. The installer:
1. copies the core system — never overwriting your files (conflicts are saved as `*.forge-new`);
2. builds only the adapters your agent(s) need;
3. turns on the git-hook guardrails;
4. **commits it all on branch `chore/forge-setup`** → push and open a PR.

Already cloned the forge? `python3 path/to/inctec-forge/install.py --agent claude`.
Update an existing repo to the latest forge: same command with `--update`.

## Learn
| | |
|---|---|
| [Getting started](docs/guides/getting-started.md) | install, first feature, daily use in each tool, the factory |
| [Writing skills and roles](docs/guides/writing-skills-and-roles.md) | teach the agents something new; borrow from public libraries |
| [Building your own agent system](docs/guides/building-your-own-agent-system.md) | the design principles behind Forge, and how to extend it |
| [Reading list](docs/guides/reading-list.md) | standards, public skills libraries, the essential essays, stack docs |
| [Contributing](CONTRIBUTING.md) | add a skill, fix a rule, improve the guideline — 10-minute PRs welcome |

## What's inside
```
AGENTS.md                 the constitution every agent reads first (stack, non-negotiables, loop, tiers)
.agents/
  roles/                  13 roles: spec-writer, architect, griller, builder, backend/frontend/devops/test engineers,
                          code/security/ux/ui reviewers, approver
  skills/                 15 skills (open SKILL.md format) — workflow: build-feature, grill, design-doc, review, ship,
                          debug, factory · domain: fastapi-backend, postgres-migrations, background-work (Celery/Temporal),
                          testing, frontend, devops, observability, system-design
  config.toml             your agents, tool CLIs, tier → model mapping, per-role overrides, factory settings
  risk-rules.json         what makes a change T0 / T1 / T2 / T3
docs/engineering/         autonomy policy · taste · decision-making · stage-by-stage toolchain
docs/guides/              the guides above
factory/                  unattended pipeline: spec → build ⇄ parallel reviews → approver → merge | needs-human
scripts/                  risk_tier.py · sync_agents.py · githooks/
templates/                Makefile, dev compose (Postgres, Redis, Celery, Temporal, Grafana/VictoriaMetrics/Loki/Tempo), CI
install.py · bootstrap.sh the installer
```

## Autonomy tiers — enforced in every tool
| Tier | Example | Agent | Human |
|---|---|---|---|
| T0 | docs, tests only | commit + PR; factory may auto-merge | spot-check |
| T1 | normal feature/fix | commit + PR | 1 approval |
| T2 | migrations, auth, contracts, Temporal workflows, deps, CI, infra, agent config, >400 lines | design note + draft PR | code owner |
| T3 | prod infra, secrets, DROP/TRUNCATE, payments | propose only | commits & executes |

Enforced by git hooks (any tool), CI (`risk-tier`, `agents-sync`), GitHub branch protection, and tool-specific extras.

## The factory
```bash
make factory f="Add a ?status= filter to GET /devices"   # any runtime: claude, codex, gemini, opencode, aider
make factory-status
python3 factory/run.py approve <run-id>                  # human only
```
Each run gets its own worktree and branch. The orchestrator runs the checks and computes the tier itself; the approver
can't override policy — by default only T0 auto-merges. Mix vendors per role in `.agents/config.toml`.
