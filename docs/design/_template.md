# Design note: <title>

- Author: <human or agent> · Reviewer: <code owner> · Status: draft | approved
- Tier: T2 | T3 · Ticket: <link>

## Problem
One paragraph. Who is affected and what can't they do today?

## Grill summary
Key questions asked in `/grill` and the answers that shaped this design. Unanswered questions listed as risks.

## Proposal
- Data model changes (tables, columns, indexes, constraints)
- API / contract changes (request/response, events) — with versioning approach
- Flow (sequence or bullet steps)
- What we are deliberately NOT doing

## Alternatives rejected
Short, with the reason.

## Rollout
- Feature flag? Migration strategy (expand → migrate → contract)? Backfill plan and its runtime?
- Order of deploys across services.

## Rollback
Exact steps to undo. What data, if any, cannot be rolled back.

## Observability
New metrics, logs, alerts, dashboards. How we'll know it works in prod.

## Test plan
Unit / integration / e2e / load — which, and the key cases.
