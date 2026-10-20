---
name: devops
description: Docker images, docker-compose, GitHub Actions CI/CD, environment config, secrets handling, deploy and rollback practices. Use for any change to Dockerfiles, compose files, workflows, or infra code. All such changes are T2+, production is T3.
---
# DevOps patterns

## Dockerfile (Python service)
```dockerfile
FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY app ./app
RUN uv sync --frozen --no-dev

FROM python:3.12-slim
RUN useradd -r -u 10001 app
WORKDIR /app
COPY --from=build /app /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER app
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/healthz')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
```
Rules: multi-stage, pinned versions, non-root, `.dockerignore` (exclude `.git`, `.env*`, tests), no secrets in build args.

## Health
`/healthz` (process alive, no deps) and `/readyz` (DB + Redis reachable). Orchestrator uses readyz for traffic.

## CI (GitHub Actions)
- Jobs: `lint` (ruff, mypy) → `test` (Postgres + Redis services) → `risk-tier` (label PR) → `build` (image, scan with Trivy) → deploy (on main, environment-protected).
- Pin third-party actions by commit SHA. `permissions:` minimal per job. Cache uv/pnpm.
- Deploy jobs use GitHub Environments with required reviewers for staging/prod.

## Config & secrets
12-factor env config. Secrets from the secret manager / CI secrets, injected at runtime. `.env.example` documents every variable with no real values.

## Deploy & rollback
- Every deploy is a new immutable image tag (git SHA). Rollback = redeploy previous tag.
- DB migrations run as a separate step before the app rollout and must be backward compatible (see postgres-migrations).
- After deploy: check error rate, latency, and the feature's own metric for 15 minutes before calling it done.

## Agent limits
Agents run `docker build`, `docker compose up` locally, `terraform plan`, `kubectl diff`, `helm template`. Never apply to shared environments.
