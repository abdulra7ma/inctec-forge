---
name: background-work
description: Choosing and implementing background work — FastAPI BackgroundTasks vs Celery task queues vs Temporal durable workflows — with idempotency, retries, scheduling, observability and testing patterns. Use whenever work must happen outside the request, on a schedule, or across multiple steps/services.
---
# Background work: pick the lightest thing that's safe

## Decision table
| Need | Use | Why |
|---|---|---|
| < 1s, non-critical, ok to lose on crash (send analytics event) | FastAPI `BackgroundTasks` | zero infra |
| Single-step job, must not be lost, retries, fan-out, periodic (send email, resize image, poll device, nightly report) | **Celery** (Redis broker) | simple, team knows it, great for many small tasks |
| Multi-step process with state, waits (minutes→months), compensation/rollback, human-in-the-loop, must survive deploys exactly where it left off (onboarding, provisioning a site, incident escalation chains, billing cycles, agent pipelines) | **Temporal** | durable execution — the workflow's state *is* the code's progress |
| Stream processing / high-volume events | Out of scope here → ADR (Redis Streams, Kafka, NATS) | |

Rule of thumb: if you are about to add a `status` column plus a cron job that "picks up where it left off", or to chain Celery tasks with
manual state machines — that's a workflow. Use Temporal. Introducing Temporal to a repo for the first time is T2 + ADR.

---
## Celery patterns
```
app/worker/
  celery_app.py      # Celery("app", broker=settings.redis_url, backend=None or redis), config below
  tasks/<domain>.py  # thin tasks calling domain services
```
Config that matters:
```python
celery_app.conf.update(
    task_acks_late=True,               # ack after success → crash = redelivery (so tasks MUST be idempotent)
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,      # fair dispatch for long tasks
    task_time_limit=300, task_soft_time_limit=270,
    task_default_queue="default",
    task_routes={"app.worker.tasks.reports.*": {"queue": "slow"}},
    broker_transport_options={"visibility_timeout": 3600},  # > longest task
    timezone="UTC",
)
```
Task rules:
- **Idempotent** by design: natural keys / idempotency key + "already done?" check, upserts not inserts.
- Arguments are IDs and small primitives — never ORM objects, never large payloads (store in Postgres/S3, pass the ID).
- Retries: `autoretry_for=(TransientError,)`, `retry_backoff=True`, `retry_jitter=True`, `max_retries=5`. Never retry on validation/logic errors.
- Tasks are thin: open a DB session, call the domain service, close. Business logic stays in `service.py` (testable without Celery).
- Async code: Celery workers are sync — call async services with `asyncio.run()` inside the task, or use **arq** for an all-async worker (ADR).
- Periodic: Celery beat with a single beat instance (or `redbeat` lock). Schedules in code, UTC.
- Enqueue after commit: never enqueue inside a DB transaction that may roll back — use an outbox table or `after_commit` hook.
- Observability: Flower or Grafana dashboard on queue depth, task latency, failures by task & reason; OTel instrumentation (`opentelemetry-instrumentation-celery`).
- Testing: unit-test the service; for task wiring use `task_always_eager=True` in a test settings profile, plus one integration test with a real worker in CI if routing matters.

---
## Temporal patterns (Python SDK `temporalio`)
```
app/workflows/
  <name>/workflow.py    # @workflow.defn — orchestration only, deterministic
  <name>/activities.py  # @activity.defn — all I/O (DB, HTTP, email) lives here
  worker.py             # Worker(client, task_queue=..., workflows=[...], activities=[...])
```
**Determinism rules (violations break running workflows → workflow code is T2):**
- No I/O, randomness, `datetime.now()`, `uuid4()`, threads or env reads in workflow code. Use `workflow.now()`, `workflow.uuid4()`, `workflow.random()`, activities for I/O.
- Changing the logic of a workflow that has running executions requires `workflow.patched("change-id")` versioning or a new workflow type. Replay-test against recorded histories in CI.
- Workflow and activity inputs/outputs are dataclasses or Pydantic models with explicit versions; never change a field's meaning.

Activity rules:
- Idempotent (Temporal retries them). Pass an idempotency key derived from `workflow_id + activity_id`.
- Always set `start_to_close_timeout`; set a `RetryPolicy` with `non_retryable_error_types` for business errors.
- Long activities heartbeat (`activity.heartbeat(progress)`) so cancellation and worker crashes are detected.

Patterns: sagas with compensations (try/except calling undo activities) · signals for human approval · queries for status pages ·
`workflow.sleep(timedelta(days=3))` for reminders · child workflows for fan-out · schedules instead of cron.
Workflow IDs are business keys (`onboard-tenant-{tenant_id}`) → natural dedupe.

Testing: `WorkflowEnvironment.start_time_skipping()` for workflow tests; mock activities by registering fakes; replayer tests for versioning.
Ops: Temporal Web UI for debugging; metrics via SDK Prometheus exporter → VictoriaMetrics; alert on workflow failure rate and task-queue backlog.
Local: `make dev-temporal` (compose profile) or `temporal server start-dev`.

---
## Checklist for any background job/workflow
idempotent · bounded retries with backoff · timeout · dead-letter/failure path visible to humans · metrics (rate, errors, duration, backlog) ·
logs with job/workflow ID and tenant · tested without the framework (service) and with it (wiring) · documented owner.
