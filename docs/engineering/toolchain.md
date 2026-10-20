# Toolchain — what we use at every stage

One page an engineer (or agent) checks before building anything: "which tool does this stage use here?"
**Default** = use it without asking. **Alternative** = allowed with an ADR. Anything not listed = ask first.

## 1. Plan & design
| Need | Default | Alternative / notes |
|---|---|---|
| Work tracking | Jira (or the team's Plane workspace) | link ticket in branch name and PR |
| Specs | `docs/specs/` via `spec-writer` | — |
| Design notes / ADRs | `docs/design/`, `docs/adr/` | Confluence for cross-team summaries |
| Diagrams | Mermaid in markdown | Miro / FigJam for workshops |
| UI design | Figma (design system library) | — |
| API design | OpenAPI generated from FastAPI; reviewed in the PR | AsyncAPI for event contracts |

## 2. Develop (local)
| Need | Default | Alternative |
|---|---|---|
| Python deps & envs | `uv` | — |
| Lint/format | `ruff` (+ `prettier`, `eslint` frontend) | — |
| Types | `mypy --strict` / `tsc --strict` | `pyright` |
| Local stack | `docker compose -f docker-compose.dev.yml` (`make dev`) | — |
| Local observability | `make dev-obs` → Grafana :3000, VictoriaMetrics, Loki, Tempo, OTel collector | — |
| Local workflows | `make dev-temporal` → Temporal + UI :8233 | `temporal server start-dev` |
| Task queue worker | Celery (`make worker`) with Redis | arq (all-async) via ADR |
| Coding agents | any tool reading `AGENTS.md` (Claude Code, Codex, Gemini CLI, Cursor, Copilot, opencode, Aider) | — |
| Secrets locally | `.env` (never committed), `.env.example` documents keys | direnv + secret manager CLI |
| Git hooks | `scripts/githooks/` + `pre-commit` (ruff, gitleaks) | — |

## 3. Build & CI
| Need | Default | Alternative |
|---|---|---|
| CI | GitHub Actions: lint → test → risk-tier → agents-sync → build → scan | — |
| Images | Docker multi-stage, non-root, tagged by git SHA | — |
| Registry | GHCR | cloud registry per client |
| Vulnerability scan | Trivy (image), `pip-audit` / `pnpm audit` (deps), gitleaks (secrets) | Snyk |
| Code quality gate | coverage ≥ 85% on `app/`, migration round-trip | SonarQube for client contracts that require it |
| Automated feature delivery | `factory/run.py` (local or CI job) | — |

## 4. Test
| Level | Default |
|---|---|
| Unit / integration (Python) | pytest, pytest-asyncio, testcontainers (Postgres/Redis), respx, polyfactory, time-machine |
| Frontend | Vitest + Testing Library + MSW |
| E2E | Playwright |
| Contract | OpenAPI snapshot test; Temporal replay tests for workflows |
| Load | k6 (scripts in `tests/load/`), run against staging |

## 5. Staging
| Need | Default |
|---|---|
| Deploy | CI on merge to `main` → staging automatically |
| Migrations | separate CI step before rollout; must be backward compatible |
| Config & secrets | environment variables from the secret manager; GitHub Environments |
| Data | anonymised / synthetic — never raw production PII |
| Verification | smoke tests + Playwright critical flows + Grafana check of error rate/latency after deploy |
| Feature flags | env-var flags for simple cases; a flag service via ADR when needed |

## 6. Production
| Need | Default |
|---|---|
| Deploy | manual approval in GitHub Environments (human), same image as staging (promote, never rebuild) |
| Rollback | redeploy previous SHA tag; DB stays forward-compatible thanks to expand/contract |
| Runtime | Docker on VMs/compose for small services; Kubernetes (Helm) for client platforms like RNP — per-project ADR |
| Background | Celery workers (separate deployment, autoscaled on queue depth); Temporal cluster or Temporal Cloud |
| Infra as code | Terraform (plan in CI by agents; apply by humans) |
| Access | least privilege; prod shell access logged; no agent credentials in prod |

## 7. Monitor & operate
| Signal | Default | Where |
|---|---|---|
| Metrics | VictoriaMetrics (vmagent / OTel collector) | Grafana |
| Logs | Loki (VictoriaLogs via ADR) | Grafana Explore |
| Traces | Tempo via OTel collector | Grafana Explore, linked from logs |
| Errors | Sentry (backend + frontend) | Sentry → team channel |
| Alerting | vmalert / Grafana Alerting → Alertmanager → Telegram/Slack + on-call | runbooks in `docs/runbooks/` |
| Uptime / synthetic | Grafana synthetic checks or Uptime Kuma | status page for clients |
| Jobs/workflows | Flower or Grafana Celery dashboard; Temporal Web UI | |
| Profiling (when needed) | py-spy / Pyroscope | |

## 8. Incident
Declare in the incident channel → one incident lead → mitigate first (rollback/flag off) → `/debug` for root cause →
postmortem in `docs/postmortems/` within 5 working days (blameless; action items with owners).

## How agents use this page
Before building, the builder/spec-writer checks which stages the feature touches and includes the matching items
(e.g. a new Celery task → retry policy + queue metric + Grafana panel + alert on backlog age).
