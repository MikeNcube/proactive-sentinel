# Mike (Simbarashe) Ncube — ATS CV (AI Engineer Focus)

> Plain-text-friendly. Single column. No tables / graphics / icons. Evidence-only.

---

**MIKE (SIMBARASHE) NCUBE**
AI Engineer — Agentic AI, Applied LLM Workflows, Python Backends
Email: [add] | GitHub: github.com/MikeNcube | LinkedIn: [add] | Location: [add]

## PROFESSIONAL SUMMARY

AI engineer building agentic AI pipelines and the Python backends that serve them. Experienced with multi-agent LLM workflows on local model runtimes, Flask/FastAPI services, multi-tenant data models, JWT authentication, AES-256 field-level encryption, PII masking, rule-based detection, and alert correlation. Comfortable with Docker-based local environments, pytest, and OpenTelemetry instrumentation.

## CORE SKILLS

- **Languages:** Python 3.11
- **AI / LLM:** Agentic multi-agent pipelines, prompt-template design, Ollama (local llama3), human-in-the-loop review loops
- **Backend:** Flask, FastAPI, SQLAlchemy 2.x, Alembic, Jinja2, Flask-Limiter, Flask-CORS, flask-jwt-extended
- **Data:** PostgreSQL, Redis (dedup cache), public-API and RSS ingestion (GitHub Search, ArXiv Atom, O'Reilly RSS)
- **Security:** JWT (HS256 access + refresh), bcrypt, AES-256-GCM column encryption, regex-based PII masking (SA ID, Zim ID, passport), rate-limiting, secure response headers, tenant isolation
- **Observability:** OpenTelemetry (API/SDK, Flask + SQLAlchemy instrumentation, OTLP/gRPC), JSON request logging, correlation IDs
- **Tooling:** Docker, Docker Compose, n8n, pytest, pytest-flask, factory-boy, Makefile, gunicorn

## PROJECTS

### Proactive Sentinel — Multi-tenant Python/Flask SOC Service (Open Source)

- Designed a Flask application-factory service with tenant-scoped auth, bcrypt password hashing, and JWT access + refresh tokens.
- Implemented AES-256-GCM column-level encryption using a SQLAlchemy TypeDecorator; applied it to user PII fields (phone, full name, address, MFA secret) with a dedicated ENCRYPTION_KEY separate from JWT secrets.
- Built a recursive PII masking layer for structured telemetry, covering South African national IDs, Zimbabwe IDs, and passport number patterns.
- Implemented rule-based detections for user file-access spikes and UX degradation (slow claims, WhatsApp frustration, HTTP 4xx/5xx, negative sentiment on social channels, Zendesk latency, CRM lead leakage).
- Built an alert correlation engine that deduplicates alerts via SHA-256 fingerprints in Redis and groups them into MITRE ATT&CK–style attack chains using technique IDs, with a confidence score per chain.
- Added a per-IP and per-unit request-velocity threat detector with an auto-ban after repeated violations and a unit-compromise signal.
- Exposed `/api/health`, `/api/alerts`, `/api/alerts/<id>/dismiss`, `/api/stats`, `/api/tenants/current`, `/api/units/*`, `/api/auth/*`, and `/api/audit/logs`; added Flask-Limiter rate limiting and hardened response headers (HSTS, X-Frame-Options, X-Content-Type-Options).
- Instrumented the stack with OpenTelemetry (Flask + SQLAlchemy, OTLP/gRPC) and structured JSON logging with correlation IDs.
- Packaged the service with a non-root `python:3.11-slim` Docker image and a Docker Compose stack including Postgres 15 and Redis 7; added an `init.sql` that enables `pgcrypto`, `uuid-ossp`, and a tenant-context helper function for row-level-security policies.
- Wrote pytest suites covering PII masking, detection engine behaviour, tenant isolation, and API flows.

### AI-Social-Agent — Agentic Content Pipeline (Open Source)

- Built a three-agent Python pipeline (Research → Strategy → Content) that turns fresh AI-ecosystem signals into platform-specific social posts.
- Integrated a local Ollama runtime (`llama3`) via HTTP for all LLM calls, keeping iteration fast and free of external API dependencies.
- Implemented a data-ingestion module pulling from the GitHub Search API (trending repos by topic), the ArXiv Atom feed, and an O'Reilly AI RSS feed; persisted results as timestamped JSON for downstream agents.
- Designed version-controlled prompt templates per agent and per platform (LinkedIn, X, Instagram, TikTok), plus hook-writer, body-generator, and strategist sub-prompts.
- Built a FastAPI + Jinja2 human-in-the-loop review dashboard supporting list/filter/view, approve, reject, schedule, bulk-approve, bulk-schedule, and per-platform / per-status / per-weekday analytics.
- Added a weekday-gated scheduler that picks up approved-but-unscheduled posts and simulates posting to each platform.
- Stood up an n8n container via Docker Compose with a mounted workflows folder for future event-driven orchestration.

## EDUCATION

[Degree, Institution, Year] — keep existing real entry

## CERTIFICATIONS

[Only keep entries that are real and verifiable]

---

### ATS keyword coverage (evidence-backed)

AI Engineer · Agentic AI · multi-agent · LLM · prompt engineering · Ollama · Python · Flask · FastAPI · SQLAlchemy · Alembic · PostgreSQL · Redis · JWT · bcrypt · AES-256 · encryption · PII · multi-tenant · rate limiting · OpenTelemetry · Docker · Docker Compose · n8n · pytest · MITRE ATT&CK · alert correlation · data pipelines
