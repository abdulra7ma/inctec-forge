# Writing skills and roles

Forge has two kinds of reusable agent knowledge:

| | **Skill** (`.agents/skills/<name>/SKILL.md`) | **Role** (`.agents/roles/<name>.md`) |
|---|---|---|
| Answers | *How* do we do X here? | *Who* is doing the work, with what judgment and limits? |
| Example | `postgres-migrations`: expand/contract, safe vs dangerous DDL | `security-reviewer`: what to look for, how to report, when to escalate |
| Loaded | on demand, when the task matches its `description` | when a phase of work is delegated to that role |
| Format | open [Agent Skills spec](https://agentskills.io/specification) — works in Claude Code, Codex, Gemini CLI, Cursor, Copilot, opencode | Forge format: `name`, `description`, `tier`, `access` |

Rule of thumb: if you find yourself repeating the same correction in reviews, it's a missing **skill**.
If you need a different *perspective* on the work (a tester, a skeptic, a DBA), it's a missing **role**.

## Writing a skill

### 1. Anatomy
```
.agents/skills/kafka-consumers/
├── SKILL.md          # required: frontmatter + instructions
├── references/       # optional: longer docs the agent opens only when needed
├── scripts/          # optional: helpers the agent can run
└── assets/           # optional: templates, example configs
```

```markdown
---
name: kafka-consumers
description: Patterns for Kafka consumers in our Python services — consumer groups, offset commits, retries and
  dead-letter topics, idempotent handlers, lag metrics. Use when adding or changing anything that reads from Kafka.
---
# Kafka consumers
…instructions…
```

Spec rules (the sync script enforces them): `name` is lowercase letters, digits and single hyphens, ≤ 64 chars, and
**matches the folder name**; `description` is ≤ 1024 chars.

### 2. The description is the most important line
Agents see only `name` + `description` for every skill until they decide to open one. So the description must say
**what it covers and when to use it**, with the words people actually type.

- ✗ `description: Kafka helpers.`
- ✓ `description: Patterns for Kafka consumers … Use when adding or changing anything that reads from Kafka.`

### 3. Write the body like a senior engineer's checklist, not a textbook
- Lead with the **decision** ("use X unless Y"), then the **pattern** (a short code skeleton from *our* stack),
  then the **rules** (things that break in production), then a **checklist**.
- Be specific to IncTec: our libraries, our folder layout, our metric names. Generic advice the model already knows
  wastes context.
- Say what's T2/T3 in this area so the agent escalates correctly.
- Keep `SKILL.md` under ~300 lines. Move long references into `references/` and link them one level deep.
- Show, don't describe: one 10-line example beats three paragraphs.

### 4. Test it before you PR it
1. Open your agent in a repo with the skill and give it a task that *should* trigger it — without naming the skill.
   Did it pick the skill up? If not, improve the description.
2. Give it a task that should *not* trigger it. Did it stay quiet?
3. Compare the output with and without the skill. If you can't see a difference, the skill isn't teaching anything new.

## Writing a role

```markdown
---
name: dba-reviewer
description: Reviews schema changes and heavy queries for locking, index use and data safety. Use for any PR touching
  migrations/ or adding queries on tables over 1M rows. Read-only.
tier: reasoning        # reasoning | fast  → mapped to a real model per tool in .agents/config.toml
access: read           # read | write | docs   (+web to allow web search)
---
You are the DBA reviewer. …
```

Guidelines:
- One job per role. A role that "reviews code and also writes tests" is two roles.
- State the **output contract**. Reviewer roles used by the factory must end with the JSON verdict
  (`{"reviewer": …, "verdict": "PASS" | "CHANGES", "findings": [...]}`) — copy it from `code-reviewer.md`.
- State what the role must **never** do (edit code, approve its own work, run against prod…).
- Pick `tier: reasoning` for judgment (design, review, approval), `fast` for well-specified execution.
- Want the factory to use it? Add it under `[[factory.reviewers]]` in `.agents/config.toml` with the file globs it
  should run on.

## After any change
```bash
make agents-sync      # rebuilds tool adapters (e.g. .claude/agents, .claude/skills) and validates skill frontmatter
```
Commit the `.agents/` change *and* the regenerated files together — CI's `agents-sync` job fails if they drift.
Changes under `.agents/` are tier T2: they change how every agent behaves, so a code owner reviews them.

## Borrowing from public libraries
Plenty of good skills already exist (see the [reading list](reading-list.md)). To adopt one:
1. Read it fully — a skill is instructions your agents will follow; treat it like code you're merging.
2. Copy it into `.agents/skills/<name>/`, then adapt it to our stack and conventions.
3. Keep the source in its `metadata` (e.g. `metadata: { source: "anthropics/skills", adapted: "2026-10" }`).
4. PR it like any other skill.
