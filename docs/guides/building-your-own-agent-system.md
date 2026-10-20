# Building your own agent system — how Forge is designed, and why

Forge is one answer to: *"How do 20 engineers and a lot of coding agents produce consistent, safe, high-taste software?"*
This guide explains the design so you can extend it — or build a variant for another team or product.

## The six layers

```
6. Orchestration   factory/            who does what, in what order, unattended
5. Guardrails      hooks · CI · rules  what is physically prevented, not just discouraged
4. Roles           .agents/roles/      distinct perspectives with limits (builder ≠ reviewer ≠ approver)
3. Skills          .agents/skills/     how we do specific things here, loaded on demand
2. Policies        docs/engineering/   autonomy, taste, decision-making, toolchain
1. Constitution    AGENTS.md           the short always-loaded rules every agent reads first
```

Build bottom-up. Most of the value is in layers 1–3; layers 5–6 make it safe to let agents run longer.

## Principles

**1. Context is a budget.** Every token in the always-loaded file is paid on every task. Keep `AGENTS.md` short and
push detail into skills that load only when relevant (progressive disclosure). If `AGENTS.md` grows past ~150
lines, something belongs in a skill.

**2. Write down taste, or you'll get average taste.** Models default to the median of the internet. Our taste
(`taste.md`), our patterns (skills) and our decision rules (`decision-making.md`) are what make the output *ours*.
The best source is your own code reviews: every repeated comment is a rule waiting to be written.

**3. Separate the doer from the checker.** A model reviewing its own work in the same context mostly agrees with
itself. Reviews run as separate roles in fresh context, ideally on a different model family. The orchestrator —
not an agent — runs the tests and computes the risk tier, because agents can be confidently wrong about both.

**4. Autonomy follows reversibility, not confidence.** We don't ask "is the agent sure?" — we ask "what does it cost
if it's wrong, and can we undo it?" That's the T0–T3 ladder. Cheap and reversible → agent alone. Contracts, data,
money, prod → human decides.

**5. Enforce at the boundary, not in the prompt.** Prompts are suggestions. Git hooks, CI and branch protection are
facts. Every rule that really matters (no commits to main, no destructive migrations by agents) exists as a hook or
check, not only as a sentence. Make enforcement tool-independent, so switching agents doesn't remove a guardrail.

**6. Be vendor-neutral by default.** Models and tools change every few months. Keep the source of truth in open
formats (`AGENTS.md`, `SKILL.md`), describe roles by *capability* (`tier: reasoning`) rather than model name, and
generate tool-specific adapters. Switching tools should be a one-line config change.

**7. Grill before you build.** Most expensive agent failures are building the wrong thing well. A few sharp questions
up front — data, contracts, failure, security, rollback — are cheaper than any review afterwards.

**8. Close the loop.** Measure: how often PRs need human fixes, which tiers escalate, which review comments repeat.
Feed that back into skills and rules weekly. A system that doesn't learn decays.

## Extending Forge

| You want to… | Do this |
|---|---|
| Teach a new pattern (Kafka, gRPC, a client's API) | new skill → [writing-skills-and-roles.md](writing-skills-and-roles.md) |
| Add a new review perspective (DBA, accessibility, performance) | new role + add it under `[[factory.reviewers]]` |
| Support another coding tool | add an entry in `scripts/sync_agents.py` (adapter) and `[runtimes]` in `config.toml` (headless command) |
| Make the tier fit your repo | edit `.agents/risk-rules.json` (paths and patterns per tier) |
| Add a pipeline stage (e.g. performance check before approval) | add a step in `factory/run.py` between reviews and approver |
| Product-specific rules for one repo | a short section at the bottom of that repo's `AGENTS.md`, or a repo-local skill |

## Building a variant for another team

1. Fork Forge (or start from the same six layers).
2. Rewrite `AGENTS.md` stack + non-negotiables for that team — keep it short.
3. Replace domain skills; keep the workflow skills (`build-feature`, `grill`, `review`, `ship`) — they're stack-agnostic.
4. Re-draw the tier boundaries for that team's risk profile (a fintech team will push more into T2/T3).
5. Pilot in one repo for two weeks before rolling out. Tune from real misclassifications and repeated review comments.

## Anti-patterns we deliberately avoid
- **One giant prompt.** A 2,000-line `AGENTS.md` that every task pays for and nobody maintains.
- **Agent approves its own work.** Same context, same blind spots.
- **Trusting the agent's "tests pass".** The orchestrator runs them.
- **Policy only in prose.** If it matters, it's a hook or a CI check.
- **Tool lock-in.** Rules written in one vendor's proprietary format.
- **Skills nobody tested.** If a skill doesn't measurably change output, delete it.
