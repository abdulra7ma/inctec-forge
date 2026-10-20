---
name: design-doc
description: Write a design note (T2 work) or an ADR (architecture decision) from the templates in docs/. Use before implementing migrations, auth changes, new contracts, new dependencies or services, or when asked for a design, RFC, or ADR.
---
# /design-doc

1. Decide which document:
   - **Design note** → `docs/design/YYYY-MM-DD-<slug>.md` from `docs/design/_template.md`. One change, one note.
   - **ADR** → `docs/adr/NNNN-<slug>.md` from `docs/adr/0000-template.md`, next free number. For choices that outlive one feature
     (datastore, service boundary, auth model, versioning strategy, major library).
2. Fill it from the grill output and the code. Every claim about current behaviour cites a file path.
3. Mandatory sections are never "TBD": Problem, Proposal, Rollback, Observability, Test plan.
4. Data model changes: show the exact DDL or SQLAlchemy model diff and the migration strategy (expand → migrate → contract).
5. Contract changes: show before/after request/response or event schema and who consumes it.
6. Keep it short: 1–2 pages. A diagram (Mermaid) only if it saves words.
7. Set status `draft`, tell the human it needs approval, and link it in the PR.
