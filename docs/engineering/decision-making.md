# How we make technical decisions

## 1. Classify the door
- **Two-way door** (cheap to reverse: a function shape, a library-internal pattern, a UI tweak) → decide fast,
  the implementer decides, note it in the PR.
- **One-way door** (DB schema, public API, choice of datastore/queue, auth model, data retention, vendor lock-in)
  → slow down: grill, write options, get a human decision, record an ADR.

## 2. Write the options, not just the answer
For any one-way door, list at least two real options plus "do nothing". For each:
what it costs to build, what it costs to run, what it costs to undo, and what it makes harder later.
If you can only think of one option, you haven't understood the problem yet.

## 3. Decide with explicit criteria
Default priority order when criteria conflict:
1. Correctness & data safety
2. Security
3. Operability (can we observe, debug, roll back?)
4. Simplicity / team familiarity
5. Performance (only with a measured number and a target)
6. Developer convenience

## 4. Record it
- ADR (`docs/adr/NNNN-title.md`) for anything architectural. Immutable once accepted; supersede, don't edit.
- Design note (`docs/design/YYYY-MM-DD-title.md`) for T2 work — narrower, about one change.

## 5. Disagree and commit
Raise objections before the decision with evidence. After it, implement it as if it were your idea.
If new evidence appears, open a new ADR that supersedes the old one.

## Who decides
| Decision | Decider | Consulted |
|---|---|---|
| Inside one module, reversible | implementer (human or agent) | reviewer |
| New dependency, cross-module pattern | tech lead of the area | architect agent, team |
| Datastore, service boundary, auth, public API versioning | engineering lead | area leads, DevOps |
| Prod infra, security posture, data retention | engineering lead + DevOps | security reviewer |
