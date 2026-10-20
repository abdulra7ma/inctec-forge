.PHONY: dev fmt lint typecheck test check migration tier

dev:
	docker compose -f docker-compose.dev.yml up --build

fmt:
	uv run ruff format . && uv run ruff check --fix .

lint:
	uv run ruff format --check . && uv run ruff check .

typecheck:
	uv run mypy app

test:
	uv run pytest -q

check: lint typecheck test

migration:
	@test -n "$(m)" || (echo 'usage: make migration m="message"'; exit 1)
	uv run alembic revision --autogenerate -m "$(m)"

tier:
	python3 scripts/risk_tier.py --base origin/main

# --- agents & factory ---------------------------------------------------------
.PHONY: factory factory-status agents-sync dev-obs dev-temporal worker

factory:
	@test -n "$(f)" || (echo 'usage: make factory f="feature request" [rt=codex]'; exit 1)
	python3 factory/run.py new "$(f)" $(if $(rt),--runtime $(rt),)

factory-status:
	python3 factory/run.py status

agents-sync:
	python3 scripts/sync_agents.py

# --- local stacks (see docs/engineering/toolchain.md) -------------------------
dev-obs:
	docker compose -f docker-compose.dev.yml --profile obs up --build

dev-temporal:
	docker compose -f docker-compose.dev.yml --profile temporal up --build

worker:
	uv run celery -A app.worker.celery_app worker -l info --concurrency=4
