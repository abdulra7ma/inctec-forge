---
name: observability
description: Logs, metrics, traces, errors, dashboards and alerting for our services on the Grafana stack — OpenTelemetry, VictoriaMetrics, Loki, Tempo, Grafana, Sentry. Use when adding features with new failure modes, external calls, jobs or workflows, or when asked about monitoring, dashboards, SLOs or alerts.
---
# Observability on our stack

## The pipeline
```
app (OTel SDK: traces + metrics + logs, structlog JSON to stdout)
  └─► OpenTelemetry Collector ──► VictoriaMetrics (metrics, PromQL/MetricsQL)  ─┐
                               ├─► Loki            (logs, LogQL)                ├─► Grafana (dashboards, explore, alerting)
                               └─► Tempo           (traces, TraceQL)           ─┘
app exceptions ─► Sentry (errors, releases, user impact)       vmalert / Grafana Alerting ─► on-call channel
```
Local: `make dev-obs` brings this up (Grafana on :3000 with all datasources provisioned). Same signals in staging/prod.
VictoriaLogs can replace Loki (one vendor with VictoriaMetrics) — that switch is an ADR.

## Logs (structlog → stdout JSON; collector ships to Loki)
- Every line: `service`, `env`, `version`, `request_id`, `trace_id`, `span_id`, `tenant_id` when known. Bind via middleware/contextvars.
- Stable event names as nouns+verbs: `webhook_delivery_failed`, with fields — not formatted strings.
- Levels: ERROR = someone should look · WARNING = degraded but handled · INFO = business events · DEBUG off in prod.
- Loki labels are **low-cardinality only** (`service`, `env`, `level`). IDs go in the log body, never labels.
- Never log secrets, tokens, full bodies or PII.

## Metrics (OTel or prometheus-client → VictoriaMetrics)
- RED for every endpoint and outbound dependency: rate, errors, duration (histogram).
- USE for resources: DB pool in-use/wait, Redis, Celery queue depth, Temporal task-queue backlog.
- Naming: `<service>_<thing>_<unit>` (`rnp_webhook_delivery_seconds`), counters end in `_total`.
- Labels bounded: route template, status class, dependency, queue. Never user/device/tenant IDs or raw URLs.
- Business metrics for each feature: the number that proves it works (`devices_onboarded_total`).

## Traces (OTel → Tempo)
Auto-instrument FastAPI, SQLAlchemy, httpx, Redis, Celery; Temporal via its interceptor. Propagate context across queues/workflows.
Sample 100% in dev/staging; in prod parent-based ~10% plus tail-sample all errors and slow requests in the collector.
`trace_id` in every log line → Grafana jumps log ↔ trace ↔ metric (exemplars).

## Errors (Sentry)
`sentry-sdk[fastapi,celery]` with `release=<git sha>`, `environment`, PII scrubbing on. Frontend uses Sentry React with source maps.
Alerts for new issue types in prod go to the owning team's channel.

## Dashboards & alerts as code
- Dashboards: JSON in `observability/grafana/dashboards/` (provisioned). Each service: RED overview, dependencies, jobs/workflows, business KPIs.
- Alert rules: in repo (`observability/alerts/*.yml` for vmalert, or Grafana alerting provisioning). Reviewed like code (T2).
- Every alert has: owner, severity, runbook link (`docs/runbooks/<alert>.md`), and fires on **symptoms users feel** (SLO burn rate, error rate, latency, backlog age) — not CPU.

## SLOs
Each user-facing service: 1–2 SLOs, e.g. "99.5% of API requests succeed in < 500 ms over 30 days". Multi-window burn-rate alerts
(fast: 14.4× over 1h/5m → page; slow: 6× over 6h/30m → ticket).

## Checklist for a new feature
Which metric proves it works? Which log event explains a failure? Which alert fires if it silently stops? Which dashboard panel shows it?
Traces cover the new external calls? Sentry catches its exceptions with useful context?
