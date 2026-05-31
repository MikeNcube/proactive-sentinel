# Mike (Simbarashe) Ncube — General Tech CV

> Broader software/AI positioning. Still fully evidence-backed — no AWS, Terraform, or RAG claims.

---

**MIKE (SIMBARASHE) NCUBE**
Software Engineer — Python Backends & Applied AI
Email: [add] | GitHub: github.com/MikeNcube | LinkedIn: [add]

## SUMMARY

Python engineer who builds backends and applied-AI systems end-to-end. Comfortable owning a service from data model through HTTP API to containerised runtime, with pragmatic security (JWT, field-level encryption, PII masking) and lightweight observability. Also builds multi-agent LLM workflows on local model runtimes with human-in-the-loop review.

## TECHNICAL SKILLS

- **Languages:** Python 3
- **Web / API:** Flask, FastAPI, Jinja2, REST, blueprints, decorators
- **Data:** PostgreSQL, Redis, SQLAlchemy 2.x ORM, Alembic migrations, public-API and RSS ingestion
- **Security & Auth:** JWT (HS256), bcrypt, AES-256-GCM, PII masking, tenant isolation, rate limiting, secure headers
- **AI / LLM:** Multi-agent pipelines, prompt-template design, local Ollama (`llama3`), human-in-the-loop review workflows
- **DevEx / Runtime:** Docker, Docker Compose, gunicorn, Makefile, pytest, OpenTelemetry, structured JSON logging
- **Other:** n8n (workflow scaffolding), Git, Linux

## SELECTED PROJECTS

### Multi-tenant Flask SOC service (Python / PostgreSQL / Redis)

- Application-factory Flask service with JWT auth, bcrypt passwords, and tenant-scoped decorators on every `/api/*` route.
- AES-256-GCM column-level encryption via a SQLAlchemy TypeDecorator, applied to user PII fields.
- Recursive PII masking for South African / Zimbabwean IDs and passport numbers in structured telemetry payloads.
- Rule-based detection engine plus a UX-observer module covering slow claims, channel frustration, HTTP 4xx/5xx, social-sentiment outcry, support latency, and CRM lead leakage.
- Redis-backed alert deduplication and MITRE-technique attack-chain grouping.
- Per-IP and per-unit velocity throttling with auto-ban on repeated violations.
- OpenTelemetry instrumentation, rate limiting, secure response headers, Docker Compose with Postgres + Redis, pytest coverage.

### Agentic content pipeline (Python / FastAPI / Ollama)

- Research → Strategy → Content multi-agent loop; prompts are version-controlled text.
- GitHub Search API, ArXiv feed, and O'Reilly RSS ingestion with JSON persistence.
- Local Ollama (`llama3`) runtime for all LLM calls.
- FastAPI + Jinja2 human-review dashboard with approvals, scheduling, bulk operations, and analytics.
- Docker Compose with n8n container ready for orchestration.

## EDUCATION

[Keep existing real entry]
