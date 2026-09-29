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

#### Event 2: Access Check (`POST /auth/access-check`)

| Property | Type | Description |
| :--- | :--- | :--- |
| `user_id` * | `string (uuid)` | User identifier |
| `privilege_level` * | `integer` | Metric for statistics (1 = User, 2 = Manager, 3 = Admin) |
| `timestamp` * | `string (date-time)` | Event recording time (ISO 8601) |
| `resource_path` | `string` | Target endpoint (e.g., `/admin/finance`) |
| `access_granted` | `boolean` | `true` or `false` |

*\* Meets the 3 required lab properties: identifier, numeric metric, and timestamp.*

---

## Quick Reference Commands

- **Run Server:**

  ```bash
  uvicorn receiver:app --reload --port 8080
  ```

- **Swagger UI:** `http://localhost:8080/ui/`
