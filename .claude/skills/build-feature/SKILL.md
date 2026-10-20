---
name: build-feature
description: End-to-end workflow for building any feature or fix in this repo — understand, classify risk, grill, design, plan, implement, review, ship. Use whenever asked to build, add, implement, or fix something non-trivial.
---
# /build-feature

Run these phases in order. Print a one-line status at each phase boundary. Don't skip phases; shrink them for small work.

## 1. Understand (always)
- Restate the goal in 2–3 sentences: who benefits, what changes for them, how we'll know it works.
- Search the codebase for related code (`Grep` for domain nouns). List the files you expect to touch.
- If a ticket/design note exists, read it.

## 2. Classify
- Predict the tier from expected files using `.agents/risk-rules.json` and `docs/engineering/autonomy.md`.
- Tell the human: "Predicted tier: T_. Reason: …". T3 → switch to **propose-only** mode now.

## 3. Grill (T2+, or anything ambiguous)
- Invoke the `griller` agent with the restated goal + file list, or run the `/grill` skill interactively with the human.
- Do not proceed while a question that would change the data model, contract, or security model is unanswered.

## 4. Design (T2+)
- Run `/design-doc`. Architecture-level choice → also an ADR via the `architect` agent.
- T2: wait for the human to approve the design note before implementing (if the human is unavailable, stop here and say so).

## 5. Plan
- Ordered checklist of steps, each small enough to test on its own (≈ < 150 changed lines). Create a branch:
  `git checkout -b feat/<short-slug>` (or `fix/`, `chore/`).

## 6. Implement
- Delegate to `builder` (full-stack) or a specialist (`backend-engineer`, `frontend-engineer`, `devops-engineer`) or do it yourself
  following that domain's skill. For each step: failing test → code → `make check` → small commit.
- If the tier rises mid-way (e.g. a migration appears), stop and go back to phase 3.

## 7. Self-review
- Run `/review` (code-reviewer + security-reviewer; ux-reviewer + ui-reviewer if frontend changed). Fix every blocker; fix "should fix" unless you can justify not to in the PR.
- Auth / input / secrets / integrations touched → also run the `security-reviewer` agent.

## 8. Ship
- Run `/ship`. It re-computes the tier from the real diff and does the right thing for that tier.

## Definition of done
Tests green · new behaviour tested · no TODOs without ticket links · logs/metrics on new failure paths ·
docs updated if behaviour or config changed · PR description complete per autonomy.md.
