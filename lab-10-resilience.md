# ACIT 3855 - Lab 10: Fault Tolerance and Resilience Guide

## 1. Overview & Core Principles

The objective of Lab 10 is to make the entire security telemetry platform resilient against runtime outages, network partitions, and service crashes.

### Key Resilience Rules:

1. **Predictable Startup:** Services must not crash on startup if an external dependency (such as Kafka or MySQL) is temporarily unreachable. Instead, services must log the condition and retry with exponential backoff.
2. **Degraded Mode (HTTP 503):** If a service cannot fulfill a request due to an unavailable dependency, it must respond with HTTP `503 Service Unavailable` instead of throwing an unhandled `500 Internal Server Error` or crashing the container.
3. **Zero Data Loss:** When downstream services (e.g., MySQL or the Storage Worker) go down, Kafka absorbs and persists incoming telemetry messages. Messages are processed once the downstream service recovers.
4. **At-Least-Once Delivery & Idempotency:** The Storage Worker commits Kafka offsets only _after_ a successful database transaction. To safely handle redeliveries without creating duplicate records, `trace_id` is enforced as a unique key in MySQL, and `IntegrityError` is handled gracefully.
5. **Self-Healing Recovery:** When downed services come back online, all dependent services must automatically reconnect and resume normal operation without manual intervention or restarts.

---

## 2. Dependency & Outage Matrix

| Service               | Direct Dependencies | Outage Behavior           | Degraded Response                                                                    |                  Data Loss?                   |
| :-------------------- | :------------------ | :------------------------ | :----------------------------------------------------------------------------------- | :-------------------------------------------: |
| **Receiver**          | Redpanda (Kafka)    | Fails to publish to Kafka | Returns HTTP `503` on `POST /auth/login` and `POST /auth/access-check`               | Messages sent during outage rejected with 503 |
| **Storage Worker**    | Redpanda, MySQL     | Database or Kafka down    | Retries DB with exponential backoff; does **not** commit Kafka offsets               |         **None** (buffered in Kafka)          |
| **Storage API**       | MySQL               | MySQL unreachable         | Returns HTTP `503` on `GET /auth/login`, `GET /auth/access-check`, and `GET /status` |                     None                      |
| **Processing Worker** | Storage API, Redis  | Storage 503 or Redis down | Skips polling cycle; preserves watermarks and statistics state                       |                     None                      |
| **Processing API**    | Redis               | Redis down or ping fails  | Returns HTTP `503` on `GET /stats`                                                   |                     None                      |

---

## 3. Implementation Plan

### Phase 1: Receiver Resilience

- **Producer Configuration:** Configure `AIOKafkaProducer` with `enable_idempotence=True`, `request_timeout_ms=10000`, `retry_backoff_ms=250`, and `linger_ms=5`.
- **Startup Resilience:** Implement `start_producer()` with an exponential backoff loop (starting at 1s, doubling up to 30s) inside the lifespan manager so the container waits for Kafka instead of crashing.
- **Runtime Resilience:** Wrap `send_and_wait()` with `asyncio.wait_for(..., timeout=5)`. Catch `(KafkaError, asyncio.TimeoutError)` and return `{"error": "temporarily unavailable"}, 503`.
- **OpenAPI Update:** Add `503` responses to `receiver.yaml`.

### Phase 2: Storage Service & Worker Resilience

- **Database Engine:** Enable `pool_pre_ping=True` in `create_engine()` to automatically discard stale database connections.
- **Deduplication & Idempotency:** Add `unique=True` on `trace_id` in `storage/models.py` (`LoginEvent` and `AccessCheck`).
- **Worker Retry & Offset Commits:**
  - Wrap database writes in `save_to_db_with_retry()` with exponential backoff on `OperationalError`.
  - Handle `IntegrityError` as an idempotent duplicate: log info and treat as success so the offset can be committed.
  - Call `consumer.commit(msg, asynchronous=False)` only after successful DB persistence.
  - Catch malformed JSON messages, log an error, and commit offset to avoid poison-pill loops.
- **Storage Read API:** Wrap `session.query()` calls in `storage.py` with try-except blocks catching `SQLAlchemyError` / `OperationalError` to return HTTP `503` when MySQL is down.
- **OpenAPI Update:** Add `503` responses to `storage.yaml`.

### Phase 3: Processing Service & Worker Resilience

- **Processing API (`app.py`):**
  - Check Redis connectivity before reading.
  - Return HTTP `503` on `GET /stats` when Redis is unreachable.
- **Processing Worker (`worker.py`):**
  - Skip processing cycle cleanly when Storage returns 503 or fails.
  - Catch Redis connection errors during `get`/`set` and retain watermarks in memory without resetting statistics.
- **OpenAPI Update:** Add `503` responses to `processing.yaml`.

### Phase 4: Chaos & Recovery Verification

- Systematically test failure scenarios:
  1. `docker compose stop redis` $\rightarrow$ verify `GET /stats` returns 503; Receiver still accepts events.
  2. `docker compose stop db` $\rightarrow$ verify Storage returns 503; Receiver still accepts events and queues them in Kafka; Storage worker pauses offset commits.
  3. `docker compose stop redpanda` $\rightarrow$ verify Receiver returns 503.
  4. Bring all services back online $\rightarrow$ verify Storage Worker drains Kafka queue to MySQL, Processing Worker catches up, and `GET /stats` reflects 100% of events without duplicates.
