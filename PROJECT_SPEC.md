# IAM Security Telemetry Service

## Project Overview

A centralized security telemetry receiver that logs authentication (login) and authorization (access check) events from web applications for auditing and threat metrics.

---

## Defense Q&A

### 1. Platform Purpose

Collects and audits real-time user login and access-control events to monitor suspicious activity and calculate security statistics.

### 2. Events Received

1. **User Login (`login_event`)**: Emitted when a user attempts to log in.
2. **Resource Access (`access_check`)**: Emitted when a user requests access to a protected route.

### 3. Event Data Structures

#### Event 1: Login Event (`POST /auth/login`)

| Property | Type | Description |
| :--- | :--- | :--- |
| `user_id` * | `string (uuid)` | User identifier |
| `failed_attempts` * | `integer` | Metric for statistics (e.g., failed attempts before login) |
| `timestamp` * | `string (date-time)` | Event recording time (ISO 8601) |
| `ip_address` | `string` | Client IP address |
| `status` | `string` | `SUCCESS` or `FAILURE` |
| `trace_id` | `string` | Unique tracking ID across microservices |

#### Event 2: Access Check (`POST /auth/access-check`)

| Property | Type | Description |
| :--- | :--- | :--- |
| `user_id` * | `string (uuid)` | User identifier |
| `privilege_level` * | `integer` | Metric for statistics (1 = User, 2 = Manager, 3 = Admin) |
| `timestamp` * | `string (date-time)` | Event recording time (ISO 8601) |
| `resource_path` | `string` | Target endpoint (e.g., `/admin/finance`) |
| `access_granted` | `boolean` | `true` or `false` |
| `trace_id` | `string` | Unique tracking ID across microservices |

*\* Meets the 3 required lab properties: identifier, numeric metric, and timestamp.*

---

## Quick Reference Commands

### Running with Docker Compose (Recommended)

- **Start entire platform:**

  ```bash
  docker compose up -d --build
  ```

- **Check container health & status:**

  ```bash
  docker compose ps
  ```

- **Stream live logs across all services:**

  ```bash
  docker compose logs -f
  ```

- **Stop all services:**

  ```bash
  docker compose down
  ```

- **Run JMeter Load Tests:**

  ```bash
  ./run_jmeter.sh 10 5
  ```

- **Inspect Aggregate Statistics:**

  ```bash
  curl http://localhost:8100/stats
  ```

- **Reset Database & Statistics:**

  ```bash
  docker compose exec storage curl -X POST http://storage:8090/reset
  docker compose exec redis redis-cli del stats
  ```

- **Public Web UIs:**
  - Grafana Telemetry Dashboard: `http://localhost:3000/` (admin/password)
  - Prometheus Metrics UI: `http://localhost:9090/`
  - Alloy Debugging Console: `http://localhost:12345/`
  - Redpanda Broker Console: `http://localhost:8085/`
  - Receiver Swagger UI: `http://localhost:8080/ui/`
  - Processing Swagger UI: `http://localhost:8100/ui/`

---

### Running Standalone for Local Development (Alternative)

- **Run Receiver (Port 8080):**

  ```bash
  cd receiver
  uvicorn receiver:app --reload --reload-include receiver.yaml --port 8080
  ```

- **Run Storage (Port 8090):**

  ```bash
  cd storage
  uvicorn storage:app --reload --reload-include storage.yaml --port 8090
  ```

---

## System Architecture & Infrastructure

### 1. Services & Endpoints

- **`receiver` (Port 8080):**
  - Receives and validates incoming events via OpenAPI (`receiver.yaml`).
  - Generates a `trace_id` for each event using `time.time_ns()`.
  - Publishes events asynchronously to Redpanda (Kafka topics `login` and `accessChecks`) using an ASGI lifespan-managed `aiokafka.AIOKafkaProducer`.
  - **Endpoints:**
    - `POST /auth/login` — Ingests login attempts, injects `trace_id`, and publishes to `login` Kafka topic.
    - `POST /auth/access-check` — Ingests authorization checks, injects `trace_id`, and publishes to `accessChecks` Kafka topic.
    - `GET /status` — Health check endpoint used by Docker healthchecks (returns `200 OK`).

- **`redpanda` (Kafka Broker - Ports 9092 internal / 19092 external):**
  - High-performance, Kafka-compatible message broker running in single-broker dev mode.
  - Receives events from `receiver` and queues them reliably for consumers.

- **`redpanda-console` (Port 8085):**
  - Web UI for monitoring topics (`login`, `accessChecks`), partitions, consumer groups, and message offsets in real time.

- **`storage-worker` (Background Event Consumer):**
  - Standalone consumer daemon running `confluent-kafka` Consumer.
  - Subscribes to `login` and `accessChecks` topics.
  - Persists incoming events to MySQL database with SQLAlchemy.
  - Performs manual offset commits only after successful DB transactions to ensure at-least-once delivery.
  - Supports graceful shutdown on `SIGTERM`/`SIGINT`.

- **`storage` (Port 8090):**
  - Read/query API connecting to MySQL using SQLAlchemy (`LoginEvent`, `AccessCheck`).
  - Microsecond-resolution timestamps via `DATETIME(fsp=6)` prevent event loss during concurrency spikes.
  - Automatically creates tables on startup if they don't exist.
  - **Endpoints:**
    - `GET /auth/login?after=<timestamp>` — Retrieves login events recorded after the specified ISO timestamp.
    - `GET /auth/access-check?after=<timestamp>` — Retrieves access check events recorded after the specified ISO timestamp.
    - `GET /status` — Returns service health and record counts (`num_logins`, `num_access_checks`).
    - `POST /reset` — Drops and recreates all database tables.

- **`db` (Port 3306 - MySQL):**
  - MySQL database container running on the internal Docker network.

- **`redis` (Port 6379 - Redis):**
  - High-performance in-memory key-value data store used to decouple data processing from API serving.
  - Configured with Append-Only File (AOF) disk persistence (`--appendonly yes --appendfsync everysec`) and a named volume (`redis_data`) to prevent state loss across restarts.

- **`processing-worker` (Background Daemon):**
  - Standalone Python daemon running a continuous polling loop every 5 seconds.
  - Queries `storage:8090` for newly recorded event deltas (`?after=...`).
  - Computes cumulative event counts (`total_login_events`, `total_access_checks`) and metric maximums (`max_failed_attempts`, `max_privilege_level`).
  - Saves the updated state JSON string to Redis.

- **`processing` (Port 8100 - API Service):**
  - Lightweight Connexion / Uvicorn REST API.
  - Uses an ASGI Lifespan manager (`@asynccontextmanager`) to maintain a persistent Redis connection pool.
  - **Endpoints:**
    - `GET /stats` — Returns aggregate security statistics from Redis.

### 2. Networking & Docker Compose

- All services run in Docker containers defined in `docker-compose.yml`.
- **Port Exposure:** Only `receiver` (8080), `processing` (8100), and `redpanda-console` (8085) are mapped to the host machine. `storage` (8090), `storage-worker`, `db` (3306), `redis` (6379), `redpanda` internal (9092), and `processing-worker` communicate across the internal Docker network.
- **Startup Order & Health Dependencies:**
  - `db` runs healthcheck (`mysqladmin ping`).
  - `storage` starts when `db` is healthy (`curl http://storage:8090/status`).
  - `redis` runs healthcheck (`redis-cli ping`).
  - `redpanda` runs healthcheck (`rpk cluster health`).
  - `receiver` starts when `redpanda` is healthy.
  - `storage-worker` starts when both `db` and `redpanda` are healthy.
  - `processing-worker` starts when both `storage` and `redis` are healthy.
  - `processing` starts when `redis` is healthy (`curl http://processing:8100/stats`).

### 3. Configuration & Security

- **Environment Variables:**
  - `receiver`: Reads `KAFKA_BROKER`, `KAFKA_TOPIC_LOGIN`, `KAFKA_TOPIC_ACCESS`.
  - `storage`: Reads `DATABASE_URL`.
  - `storage-worker`: Reads `DATABASE_URL`, `KAFKA_BROKER`, `KAFKA_TOPIC_LOGIN`, `KAFKA_TOPIC_ACCESS`.
  - `processing-worker`: Reads `STORAGE_SERVICE_URL`, `REDIS_URL`, and `POLL_INTERVAL`.
  - `processing`: Reads `REDIS_URL`.
- **Timeouts & Connection Handling:**
  - `receiver`: All outgoing HTTP requests include an explicit 5-second timeout.
  - `processing-worker`: 5-second timeout on storage queries.
  - `storage`: Database sessions are closed in `finally` blocks to prevent leaked connections.
  - `processing`: Persistent Redis connection pool managed via ASGI Lifespan.
- **Ignored Files:** `.env` and `*.log` files are excluded in `.gitignore`.

### 4. Logging & Tracing

- **Tracing:** `receiver` injects a unique `trace_id` (nanosecond timestamp) into each event payload before publishing to Kafka. Both `storage-worker` (saving to MySQL) and `storage` (serving GET endpoints) log and preserve this trace ID across microservice boundaries.
- **Logging:** Configured in `log_conf.yml` across services, writing `DEBUG`/`INFO` logs to both the terminal/Docker logs and `app.log`.

### 5. Fault Tolerance & Resilience (Lab 10)

- **Degraded Mode (HTTP 503):**
  - If Redpanda/Kafka is unavailable, `receiver` enters degraded mode and returns HTTP 503 on `POST /auth/login` and `POST /auth/access-check`.
  - If MySQL is unavailable, `storage` returns HTTP 503 on `GET /auth/login`, `GET /auth/access-check`, and `GET /status`.
  - If Redis is unavailable, `processing` returns HTTP 503 on `GET /stats`.
- **Zero Data Loss & Safe Offset Commits:**
  - `storage-worker` uses `enable.auto.commit: False` and manually commits Kafka offsets synchronously only after a successful database write.
  - When MySQL is down, `storage-worker` retries with exponential backoff without committing offsets, allowing Kafka to buffer incoming events.
- **Idempotency & Deduplication:**
  - A unique constraint on `trace_id` in MySQL prevents duplicate rows. When duplicate messages arrive from Kafka, `storage-worker` catches `IntegrityError`, logs the duplicate, and safely commits the offset.
- **Self-Healing Recovery:**
  - All services automatically recover and resume processing as soon as their underlying dependencies return online, with no container restarts required.

### 6. Observability & Telemetry (Lab 11)

- **Prometheus (Port 9090):**
  - Scrapes metrics periodically from Redpanda's Prometheus endpoint (`redpanda:9644`).
  - Provides PromQL time-series metrics on topic partition offsets and queue depth:
    `sum(vectorized_cluster_partition_end_offset) - sum(vectorized_cluster_partition_start_offset)`
- **Loki (Port 3100):**
  - High-performance, lightweight log aggregation engine indexing container metadata.
- **Grafana Alloy (Port 12345):**
  - Observability collector connected to `/var/run/docker.sock`. Automatically discovers all running microservice containers, labels their stdout/stderr logs, and ships them to Loki.
- **Grafana (Port 3000):**
  - Unified operational dashboard providing real-time visibility across 4 distinct data sources:
    1. **MySQL Data Source:** Queries row counts from `login_event` and `access_check`.
    2. **Infinity Data Source:** Parses live JSON security telemetry statistics from `http://processing:8100/stats`.
    3. **Prometheus Data Source:** Tracks Kafka queue depth and topic offsets over time.
    4. **Loki Data Source:** Real-time log stream with search filtering by `trace_id` and service names.
