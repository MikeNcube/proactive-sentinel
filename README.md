# Proactive Sentinel SOC

Proactive Sentinel is a multi-tenant Security Operations Centre (SOC) platform built for financial services providers. It ingests events from agents, log shippers, and internal services, runs them through a detection and correlation engine, and surfaces alerts on a real-time dashboard — automatically blocking attacker IPs, writing audit entries, and routing business-signal anomalies to UX observers without requiring a pre-registered endpoint token for every source.

---

## What it monitors

| Signal type | Examples |
|---|---|
| Claims fraud | Ransomware bursts, shadow copy deletion, credential dumping |
| Privilege escalation | Role changes, LSASS access, lateral movement (RDP/SMB) |
| Data exfiltration | C2 outbound traffic, directory enumeration, PowerShell encoded commands |
| WhatsApp / UX | Frustration signals, Zendesk latency spikes, lead leakage |
| Operational health | Slow claims processing, web 500 errors, social outcry patterns |

MITRE ATT&CK techniques are correlated across events to detect multi-stage attack chains (recon → lateral movement → exfil triggers a `critical` chain alert).

---

## Run locally

**Prerequisites:** Docker and Docker Compose.

```bash
cp .env.example .env          # fill in JWT_SECRET_KEY, POSTGRES_PASSWORD, ENCRYPTION_KEY
docker compose up --build
```

The API is available at `http://localhost:5001`. The dashboard is at `http://localhost:5001/dashboard`.

Run database migrations on first start:

```bash
docker compose exec app flask db upgrade
```

Run the test suite (no Docker required — uses SQLite in-memory):

```bash
pip install -r requirements.txt
pytest tests/ -v
```

---

## Key API endpoints

All endpoints under `/api/*` require a `Bearer` token obtained from `POST /api/auth/login`.

### Ingest an event

```
POST /api/events/ingest
Content-Type: application/json
Authorization: Bearer <token>

{
  "source": "wazuh-agent-01",
  "event_type": "ransomware",
  "severity": "critical",
  "raw_data": { "host": "server-01", "source_ip": "10.0.0.5" },
  "confidence": 0.95
}
```

Responses: `201 { created, alert_id, severity }` or `200 { created: false, reason: "duplicate suppressed" }`.

Security events route through `DetectionEngine` (Redis dedup + MITRE correlation). UX events (`slow_claims`, `whatsapp_frustration`, `web_error`, `social_outcry`, `zendesk_latency`, `lead_leakage`) route through `UXObserver`.

### List alerts

```
GET /api/alerts
Authorization: Bearer <token>
```

Returns all open alerts for the authenticated tenant, ordered by creation time.

### Unban a blocked IP

```
POST /api/security/unban-ip
Content-Type: application/json
Authorization: Bearer <token>

{ "ip": "10.0.0.5" }
```

Removes the IP from the Redis block list. Rate-limited to 20 requests per hour.

### Other endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Register a new tenant and admin user |
| `POST` | `/api/auth/login` | Obtain a JWT access token |
| `GET` | `/api/auth/me` | Current user and tenant |
| `POST` | `/api/alerts/<id>/dismiss` | Dismiss an alert |
| `GET` | `/api/health` | Database connectivity check |
| `POST` | `/api/units/register` | Register an endpoint/agent |
| `POST` | `/api/units/heartbeat` | Agent heartbeat |

---

## Automated response (Action Dispatcher)

After an alert is persisted, the dispatcher fires based on severity:

| Severity | FLAG | BLOCK | REPORT |
|---|---|---|---|
| `critical` | ✓ | ✓ Redis `SETEX blocked_ip:{ip}` 24h TTL | ✓ AuditLog entry |
| `high` | ✓ | — | ✓ AuditLog entry |
| `medium` | ✓ | — | — |
| `low` | — | — | — |

Dispatcher failures are non-fatal — a Redis outage does not drop alerts.

---

## Tech stack

| Layer | Technology |
|---|---|
| API | Python 3.11 · Flask 2.3 · marshmallow · Flask-Limiter |
| Auth | JWT HS256 · bcrypt · AES-256-GCM column encryption |
| Database | PostgreSQL 15 (production) · SQLite (tests) · SQLAlchemy 2.0 · Alembic |
| Cache / dedup | Redis 7 · SHA-256 fingerprint deduplication |
| Detection | `DetectionEngine` · `CorrelationEngine` (MITRE ATT&CK chain) · `UXObserver` |
| Observability | OpenTelemetry (OTLP) · structured JSON logging |
| Deployment | Railway · Docker Compose · Gunicorn |

---

## POPIA compliance features

Proactive Sentinel is designed for South African financial services providers regulated under the Protection of Personal Information Act (POPIA).

- **PII masking at ingest** — SA 13-digit IDs, Zimbabwe national IDs, and passports are masked by `VRLFilter` before any log entry is stored or processed.
- **Audit log** — every state change (alert dispatch, dismissal, role change) is written to an immutable `AuditLog` table with actor, timestamp, old value, and new value.
- **Tenant isolation** — all data is scoped by `tenant_id`; PostgreSQL row-level security context is set per request.
- **Encrypted PII fields** — sensitive user columns use AES-256-GCM encryption at rest.
- **No cross-tenant data exposure** — the ingest endpoint rejects `tenant_id` values that do not match the authenticated JWT.

---

## Status

**v1.0.0 · Production-ready** — deployed on Railway with PostgreSQL 15 and Redis 7. CI test suite: 44 passing, 1 skipped (Redis dedup test, requires live Redis).
