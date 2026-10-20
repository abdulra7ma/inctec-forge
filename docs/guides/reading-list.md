# Reading list

Curated, not exhaustive. All links checked October 2026. Start with ★.

## Standards Forge is built on
- ★ [AGENTS.md](https://agents.md) — the open format for project instructions to coding agents, and the list of tools that read it.
- ★ [Agent Skills specification](https://agentskills.io/specification) — the `SKILL.md` format: required fields, naming rules, `scripts/`, `references/`, progressive disclosure.

## Skills libraries — browse, borrow, adapt
Treat every external skill as code you're merging: read it fully, adapt it to our stack, review it in a PR
(see [Borrowing from public libraries](writing-skills-and-roles.md#borrowing-from-public-libraries)).
- ★ [anthropics/skills](https://github.com/anthropics/skills) — Anthropic's public skills repository: document skills, design, testing, and examples of well-written skills.
- ★ [skills.sh](https://skills.sh) — a directory of community skills, with the `npx skills add <owner/repo>` installer that works across many agents.
- [Vercel agent skills](https://vercel.com/docs/agent-resources/skills) — curated skills for React/Next.js, UI guidelines, deployment and workflows, with install commands.
- [github/awesome-copilot](https://github.com/github/awesome-copilot) — community instructions, agents and skills, organised by topic.

## How each tool uses instructions and skills
- Claude Code: [Skills](https://code.claude.com/docs/en/skills) · [Sub-agents](https://code.claude.com/docs/en/sub-agents) · [Hooks guide](https://code.claude.com/docs/en/hooks-guide) · [Best practices](https://code.claude.com/docs/en/best-practices)
- OpenAI Codex: [Agent skills](https://learn.chatgpt.com/docs/build-skills)
- Gemini CLI: [Agent skills](https://geminicli.com/docs/cli/skills/) · [Creating skills](https://geminicli.com/docs/cli/creating-skills/) · [Context files (GEMINI.md / AGENTS.md)](https://geminicli.com/docs/cli/gemini-md)
- Cursor: [Agent skills](https://cursor.com/docs/skills)
- GitHub Copilot: [Agent skills in VS Code](https://code.visualstudio.com/docs/agent-customization/agent-skills) · [Adding skills to the cloud agent](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills)
- opencode: [Skills](https://opencode.ai/docs/skills)

## Designing agent systems — the essential essays
- ★ [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) — workflows vs agents, and the core patterns (chaining, routing, parallelisation, orchestrator-workers, evaluator-optimiser). Our factory is an orchestrator-workers + evaluator loop.
- ★ [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — why short always-on context plus on-demand detail works; the thinking behind a short `AGENTS.md`.
- ★ [Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) — why skills exist and how progressive disclosure keeps them cheap.
- [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) — how to measure whether a skill or pipeline change actually helped.
- [Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps) — keeping long, unattended agent runs on track.

## Our stack — official docs worth bookmarking
- [FastAPI](https://fastapi.tiangolo.com) · [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/) · [Alembic](https://alembic.sqlalchemy.org) · [Pydantic](https://docs.pydantic.dev)
- [Celery](https://docs.celeryq.dev) · [Temporal Python SDK](https://docs.temporal.io/develop/python)
- [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/) · [VictoriaMetrics](https://docs.victoriametrics.com) · [Grafana](https://grafana.com/docs/grafana/latest/) · [Loki](https://grafana.com/docs/loki/latest/) · [Tempo](https://grafana.com/docs/tempo/latest/)

Found something great? Add it here in a PR with one line on why it's worth someone's time.
