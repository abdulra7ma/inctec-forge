---
name: fastapi-backend
description: House patterns for Python/FastAPI services — project layout, routers/services/repositories, Pydantic schemas, dependencies, errors, config, async DB sessions, background work. Use for any backend code in this repo.
---
# FastAPI backend patterns

## Layout (domain-first)
```
app/
  main.py              # create_app(): routers, middleware, exception handlers, lifespan
  core/
    config.py          # Settings(BaseSettings) — env only, no defaults for secrets
    db.py              # async engine, async_sessionmaker, get_session dependency
    errors.py          # DomainError hierarchy + one handler mapping to HTTP
    logging.py         # structlog JSON config, request_id contextvar
    security.py        # auth dependencies (get_current_user, require_role)
  <domain>/            # e.g. devices/, alerts/, users/
    router.py          # HTTP only: parse, call service, return schema
    schemas.py         # Pydantic v2 In/Out models (never return ORM objects)
    service.py         # domain logic; no FastAPI imports; raises DomainError
    repository.py      # SQLAlchemy queries only
    models.py          # ORM models
    tasks.py           # background jobs for this domain (optional)
tests/
  <domain>/test_router.py, test_service.py
migrations/            # Alembic
```

## Router
```python
router = APIRouter(prefix="/devices", tags=["devices"])

@router.get("/{device_id}", response_model=DeviceOut)
async def get_device(
    device_id: UUID,
    user: CurrentUser,                      # Annotated[User, Depends(get_current_user)]
    service: Annotated[DeviceService, Depends(get_device_service)],
) -> DeviceOut:
    return await service.get(device_id, tenant_id=user.tenant_id)
```
- No business logic, no SQL, no try/except for domain errors in routers.
- Use `Annotated` dependencies; type aliases (`CurrentUser`, `DbSession`) in `core/`.
- Pagination: cursor-based (`?cursor=&limit=`, limit capped at 100) for anything that can grow.

## Schemas
- `XCreate`, `XUpdate` (all optional, `exclude_unset`), `XOut` (`model_config = ConfigDict(from_attributes=True)`).
- Constrain inputs: `Annotated[str, StringConstraints(max_length=255)]`, enums, `conint(ge=1, le=100)`.
- Breaking a response shape = public contract change = T2.

## Service
- Constructor-injected repository and clients. Pure functions where possible.
- Every query is tenant-scoped — pass `tenant_id` explicitly, never rely on callers filtering.
- Writes that can be retried take an idempotency key.

## Errors
```python
class DomainError(Exception): status = 400; code = "domain_error"
class NotFound(DomainError): status = 404; code = "not_found"
class Conflict(DomainError): status = 409; code = "conflict"
class Forbidden(DomainError): status = 403; code = "forbidden"
```
One handler renders `{"error": {"code": ..., "message": ..., "request_id": ...}}`. Unexpected exceptions → 500 with request_id, full trace in logs only.

## DB
- SQLAlchemy 2.0 async, `select()` style, `expire_on_commit=False`. One session per request via dependency; commit in the service/unit-of-work, not the repository.
- Avoid N+1: `selectinload`/`joinedload` deliberately. Index every FK and every column you filter/sort on.
- Long or heavy work never runs inside a request — enqueue it.

## Config
`pydantic-settings`, nested models, `SecretStr` for secrets, validated at startup (fail fast). No `os.getenv` scattered in code.

## HTTP clients
One shared `httpx.AsyncClient` per dependency (created in lifespan), explicit `timeout=httpx.Timeout(5, connect=2)`, retries with `tenacity` only for idempotent calls, and a metric per outcome.

## Background work
- Short, fire-and-forget, non-critical → `BackgroundTasks`.
- Anything that must not be lost, retries, or schedules → a durable queue (arq/Redis or a Postgres job table). Jobs are idempotent.

## Checklist for a new endpoint
auth dep · tenant scoping · input constraints · response model · error mapping · log line on failure · metric · tests (200, 401/403, 404, 422, conflict).
