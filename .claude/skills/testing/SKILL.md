---
name: testing
description: Testing strategy and conventions — pytest/pytest-asyncio with real Postgres, factories, HTTP mocking, frontend Vitest/Playwright, coverage targets and flaky-test policy. Use when writing or fixing tests.
---
# Testing

## Pyramid for our services
- **Unit** (fast, many): pure domain logic in `service.py`, validators, utilities.
- **Integration** (most valuable): router → service → real Postgres via `httpx.AsyncClient(transport=ASGITransport(app))`.
- **Contract**: OpenAPI snapshot test — a diff in the schema fails CI and forces a conscious decision.
- **E2E** (few): Playwright on critical user journeys only.

## Backend conventions
- `pytest`, `pytest-asyncio` (`asyncio_mode = "auto"`), `testcontainers[postgres]` locally or the CI service.
- Each test runs in a transaction rolled back at the end (or truncate between tests) — no ordering dependencies.
- Data via factories (`polyfactory` or simple builder functions), not giant shared fixtures.
- Outbound HTTP mocked with `respx`; time with `time-machine`; randomness seeded.
- Name tests as sentences: `test_returns_404_when_device_belongs_to_other_tenant`.
- Assert on behaviour and outputs, not on "mock was called" unless the call *is* the behaviour (e.g. webhook sent).

## What every change needs
- Bug fix → a test reproducing the bug, failing before the fix.
- New endpoint → success, authz failure, not found, validation error, one edge case.
- Authz → a test proving user A cannot read/modify tenant B's data.

## Coverage
Target ≥ 85% lines on `app/`, but a reviewer weighs *which* lines: error paths, authz, money and data writes must be covered.

## Flaky tests
Quarantine within a day (`@pytest.mark.flaky` + ticket), fix within a week. Never add sleeps or blanket retries.

## Frontend
Vitest + Testing Library: query by role/label, test what the user sees and does. MSW for API mocking. Playwright for flows: login, primary create/edit path, error recovery.
