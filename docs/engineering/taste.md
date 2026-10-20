# Engineering Taste

Taste is the set of judgments that make code cheap to change later. These are ours.

## Simplicity
- Solve today's problem with today's code. No speculative abstractions, plugin systems, or "generic" layers
  until the third real use case. Duplication is cheaper than the wrong abstraction.
- Fewer moving parts: a Postgres table beats a new queue; a cron job beats a workflow engine — until it doesn't, and then write an ADR.
- Prefer the standard library and the stack we already run. Every dependency is a liability with a maintainer you don't control.

## Naming & structure
- Names say what a thing *is* (`overdue_invoices`), not how it was computed (`filtered_list2`).
- Modules are organised by **domain** (`app/devices/`, `app/alerts/`), not by technical layer at the top level.
- One function, one level of abstraction. If you need a comment to separate "steps", those are functions.
- Public surface small, private surface free. Leading underscore anything not used outside the module.

## Boundaries
- Validate at the edge (Pydantic schemas in, Pydantic schemas out). Inside the domain, trust your types.
- Domain logic never imports FastAPI, never knows about HTTP status codes.
- I/O at the edges, pure logic in the middle — pure functions are trivially testable.
- Every external call has a timeout, a retry policy (or an explicit "no retries"), and a metric.

## Errors
- Fail loudly and early in development; degrade gracefully in production.
- Raise domain exceptions; translate them to HTTP once, in one exception handler.
- Never swallow an exception without logging it with context. Never log and re-raise the same error at every layer.
- Error messages say what happened, what was expected, and what to do next.

## Data
- The database schema is the most expensive thing to change. Design it more carefully than code.
- Constraints in the database (NOT NULL, FK, UNIQUE, CHECK), not just in Python.
- Timestamps are `timestamptz`, stored in UTC. Money is integer minor units or `numeric`, never float.
- IDs: UUIDv7 (sortable) for public identifiers; never expose sequential IDs externally.

## Tests
- Test behaviour through the public interface, not implementation details.
- A test name is a sentence: `test_expired_token_returns_401`.
- Real Postgres in tests (testcontainers or CI service). Mocks only at true external boundaries.
- A flaky test is a bug. Fix or delete it within a day; never retry-until-green.

## Code review smell list (reject or question)
- Function > 50 lines, file > 400 lines, more than 4 parameters, nesting > 3 levels.
- Boolean parameters that switch behaviour (`do_thing(x, True)`) — make two functions.
- `except Exception: pass`, bare `except`, `# type: ignore` without a reason.
- `utils.py` / `helpers.py` / `common.py` growing without a theme.
- Comments that explain *what* instead of *why*.
- A change that touches 10 files for a 1-file idea.

## The 2 a.m. test
Before you finish, imagine an engineer paged at 2 a.m. who has never seen this code.
Can they find it from the log line? Understand it without your context? Turn it off safely?
If not, add the log, the name, or the feature flag.
