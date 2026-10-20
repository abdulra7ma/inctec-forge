---
name: system-design
description: Structured approach to system design questions — requirements, capacity estimates, data model, APIs, components, scaling, failure handling and trade-offs. Use for new services or features with scale, reliability, or cross-service implications; pairs with the architect agent.
---
# System design method

1. **Requirements** — functional (verbs users do) and non-functional (latency, availability, durability, consistency, compliance). Write numbers.
2. **Estimates** — rps (avg/peak), data size per record × records/day × retention, read:write ratio. Back-of-envelope is fine; show the math.
3. **API** — endpoints/events with request/response shapes and idempotency semantics.
4. **Data model** — entities, keys, access patterns → indexes. Choose consistency per entity (strong vs eventual).
5. **High-level components** — draw the simplest thing that meets requirements (Mermaid). Default: FastAPI modular monolith + Postgres + Redis.
6. **Deep dives** — the 1–2 hardest parts: hot partitions, fan-out, ordering, exactly-once illusions (idempotency + dedupe), backpressure.
7. **Failure modes** — for each dependency: slow, down, wrong. Timeouts, retries with jitter, circuit breakers, dead-letter queues, graceful degradation.
8. **Scaling path** — what breaks at 10x and the next step (read replicas, partitioning, caching, async), not built now.
9. **Operability** — deploy, migrate, observe, roll back.
10. **Trade-offs** — what we gave up and why. Feed into an ADR.

Patterns we reach for: outbox for reliable events · idempotency keys on writes · cursor pagination · time-series data to VictoriaMetrics not Postgres · cache-aside with explicit TTL and invalidation owner.
