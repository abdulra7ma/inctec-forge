---
name: grill
description: Interrogate a feature idea, plan, or design before building it — surface missing requirements, hidden assumptions, failure modes and risks. Use when the user says "grill me", "poke holes", "challenge this", before any T2+ work, or when requirements are vague.
---
# /grill

Two modes. Pick by context:
- **Grill the human** (default when requirements come from a person): interview them.
- **Grill the plan** (when a plan/design doc exists): spawn the `griller` agent on it, then bring its top questions to the human.

## Rules of the grill
1. Read the relevant code first. Never ask what the code already answers.
2. Ask in rounds of **max 5 questions**, highest cost-of-being-wrong first. Each question:
   - the question (one sentence)
   - why it matters (one line)
   - your proposed default ("If you don't know, I'll assume X")
3. Lenses to draw from: users & success metric · scope & non-goals · data ownership/volume/PII · contracts & compatibility ·
   failure & retries & idempotency · authz & tenancy · rollout & rollback · observability · scale (today and 10x).
4. Push back once on vague answers: "fast" → "p95 under what, at what rps?"; "secure" → "who must NOT see this?".
5. Stop when the remaining unknowns wouldn't change the design. Usually 1–3 rounds.

## Output (save into the design note's "Grill summary", or print if no note yet)
- **Decisions made** — bullet list
- **Assumptions** — things accepted without proof (become risks)
- **Open questions** — owner + by when
- **Verdict** — GO · GO WITH RISKS (list) · NO-GO (why, and what would unblock)

## Severity calibration
Grill hard on: data model, public contracts, auth, money, deletion, anything T2+.
Grill light on: internal refactors, UI copy, T0/T1 work with clear tickets — one round, max 3 questions, or skip.
