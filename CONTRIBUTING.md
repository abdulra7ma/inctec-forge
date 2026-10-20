# Contributing to IncTec Forge

Forge is **our engineering guideline in executable form** — everyone at IncTec is welcome (and expected) to improve it.
If you've explained the same thing in code review twice, it belongs here.

## What you can contribute

| Contribution | Where | Typical size |
|---|---|---|
| A new skill (a pattern we use: Kafka, gRPC, a client API, a testing trick) | `.agents/skills/<name>/SKILL.md` | 1 file, 50–300 lines |
| Improve an existing skill (fix, missing case, better example) | `.agents/skills/…` | a few lines |
| A new role (DBA reviewer, accessibility reviewer, perf reviewer…) | `.agents/roles/<name>.md` | 1 file |
| A taste rule from real code review | `docs/engineering/taste.md` | 1–3 lines |
| A tool default or alternative | `docs/engineering/toolchain.md` | a table row |
| Better risk-tier rules | `.agents/risk-rules.json` | a few patterns |
| A guide or reading-list link | `docs/guides/` | any |
| Installer / factory / scripts improvements | `install.py`, `factory/`, `scripts/` | code + test |
| Support for another coding tool | `scripts/sync_agents.py`, `.agents/config.toml`, `install.py` | small |

Not sure if it fits? Open an issue or ask in the engineering channel first — a two-line idea is a fine start.

## How to contribute (10 minutes)

```bash
git clone https://github.com/abdulra7ma/inctec-forge && cd inctec-forge
git config core.hooksPath scripts/githooks      # same guardrails as every Forge repo
git switch -c skill/kafka-consumers             # skill/…, role/…, docs/…, fix/…, feat/…

# make your change, then:
python3 scripts/sync_agents.py                  # validates skills/roles + regenerates adapters
git add -A && git commit -m "feat(skills): add kafka-consumers skill"
git push -u origin skill/kafka-consumers        # open a PR
```

Writing a skill or role? Read [docs/guides/writing-skills-and-roles.md](docs/guides/writing-skills-and-roles.md) first
— especially the part about descriptions and testing.

## What makes a PR easy to merge
- **One idea per PR.** A new skill, or a fix — not both.
- **Specific to us.** Our stack, our folder layout, our conventions. Generic advice the model already knows doesn't help.
- **Tested with an agent.** Say in the PR which tool you tried it with and what changed in the output.
- **Short.** Skills under ~300 lines; move long references into `references/`.
- **Sync committed.** `python3 scripts/sync_agents.py` run and its output committed (CI checks this).
- Conventional Commits: `feat(skills): …`, `fix(roles): …`, `docs(guides): …`, `chore: …`.

## Review and ownership
- Every PR needs one approval. Changes to `AGENTS.md`, `docs/engineering/autonomy.md`, `.agents/risk-rules.json`,
  the git hooks or the factory need an engineering-lead approval — they change how every agent in every repo behaves.
- Bigger changes to how we work (a new tier rule, a new default tool, a new pipeline stage) start as a short proposal
  in `docs/adr/` so the team can discuss before anyone builds.
- Disagree with a rule? Open a PR that changes it, with the reason. That's how the guideline evolves.

## How changes reach project repos
Repos pick up new Forge versions with `python3 install.py --update` (or the bootstrap command with `--update`).
Updates refresh roles, skills, scripts and docs; each repo keeps its own `.agents/config.toml` and `.agents/risk-rules.json`.
