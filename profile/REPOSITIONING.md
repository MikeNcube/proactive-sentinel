# Mike (Simbarashe) Ncube — Profile Repositioning (Real-Only)

> Senior AI engineering hiring panel + ATS review.
> Scope of evidence audited: this repository (`MikeNcube/proactive-sentinel`) and its sub-project `AI-Social-Agent/`.
> All claims below are traceable to files in this repo. Nothing has been invented. Where the current headline outruns the evidence, it is explicitly flagged.

---

## 0. Evidence Ledger (what is actually in the repo)

Used as the single source of truth for every output below.

### Project A — Proactive Sentinel (repo root)
- **Language / framework:** Python 3.11, Flask 2.3 (`src/__init__.py`, `app.py`, `main.py`), SQLAlchemy 2.0, Alembic migrations (`migrations/`).
- **AuthN/AuthZ:** custom `JWTManager` (HS256 access + refresh) in `src/auth/jwt_manager.py`; decorators for `require_auth` / `require_tenant` in `src/auth/decorators.py`, `src/api/decorators.py`; bcrypt password hashing with legacy Werkzeug fallback (`src/models/user.py`).
- **PII protection:** AES-256-GCM column-level encryption via SQLAlchemy `TypeDecorator` (`src/encryption.py`); regex-based PII masker for South African national ID, Zimbabwe ID, and passport numbers in `detections/vrl_filter.py` and `utils.py`.
- **Detection logic:** rules-based `DetectionEngine` (`detections/detection_engine.py`) flagging user file-access spikes; `UXObserver` (`detections/ux_observer.py`) heuristics for slow claims (`processing_time > 2s`), WhatsApp frustration (repeated "human"/"help"), HTTP 404/500, negative-sentiment outcry on Facebook/X, Zendesk wait-time, and CRM "incomplete applications" lead leakage; threat detector (`src/security/threat_detector.py`) with per-IP / per-unit velocity windows, known-bad-IP set, and auto-ban after 3 violations.
- **Correlation:** `CorrelationEngine` (`src/services/correlation_engine.py`) dedupes alerts via SHA-256 fingerprints in Redis and groups alerts into MITRE ATT&CK–style attack chains (reconnaissance → exfiltration) using technique IDs (T1046, T1592, T1078, T1059, T1021, T1020, etc.).
- **API:** Flask blueprints for `/api/health`, `/api/alerts`, `/api/alerts/<id>/dismiss`, `/api/stats`, `/api/tenants/current`, `/api/units/*`, `/api/audit/logs`, plus `/api/auth/*`; `flask-limiter` rate limiting; correlation-id middleware; security response headers (HSTS, X-Frame, CSP-adjacent).
- **Observability:** OpenTelemetry API/SDK + Flask + SQLAlchemy instrumentation + OTLP/gRPC exporter (`requirements.txt`), `python-json-logger`.
- **Persistence / infra (containerized, local):** `docker-compose.yml` with Postgres 15 and Redis 7 services; `Dockerfile` (python:3.11-slim, non-root `sentinel` user, gunicorn); `init.sql` sets up `uuid-ossp`, `pgcrypto`, tenant-context function for row-level-security policies.
- **Frontend:** server-rendered dashboard HTML (`templates/dashboard.html`, `dashboard/flask_dashboard.py`, `dashboard/static/app.js`) — a SOC-styled SPA served by Flask.
- **Testing:** pytest + pytest-flask + factory-boy; unit tests for PII masking and detection engine (`tests/test_sentinel.py`), tenant-isolation test (`tests/test_tenant_isolation.py`), API integration test (`tests/integration/test_api_flow.py`), health test (`tests/test_app.py`).
- **Deployment config present in files:** `railway.json`, `start.sh`, `Makefile` (no CI/CD pipeline files, no Terraform).

### Project B — AI-Social-Agent (sub-directory)
- **Multi-agent pipeline:** `AI-Social-Agent/scripts/enhanced_agents.py` chains a Research Agent → Strategy Agent → Content Agent, each driven by a prompt template under `AI-Social-Agent/agents/prompts/` (`research_agent.txt`, `strategy_agent.txt`, `content_agent.txt`, `instagram_agent.txt`, `tiktok_agent.txt`, plus `hook-writer.txt`, `body-generator.txt`, `strategist.txt`).
- **Model runtime:** local **Ollama** HTTP endpoint at `localhost:11434` calling `llama3` (`AI-Social-Agent/scripts/helpers.py::query_ollama`). README also mentions Groq as an aspirational hybrid option; there is no Groq client code present.
- **Data ingestion:** `AI-Social-Agent/scripts/data_sources.py` pulls from GitHub Search API (trending repos by topic), ArXiv Atom feed, and an O'Reilly AI RSS feed; results are persisted as timestamped JSON under `data/` and `agents/memory/`.
- **Memory:** flat-file JSON artifacts under `agents/memory/` (per-agent, per-post, approvals, schedules, published markers). README mentions SQLite/vector DB as *coming soon* — no such code exists in the repo.
- **Review UI:** `AI-Social-Agent/dashboard/app.py` is a FastAPI + Jinja2 dashboard for human-in-the-loop approve / reject / schedule / bulk-approve / analytics of generated posts; posting to LinkedIn / X / Instagram / TikTok is currently simulated (`scripts/scheduler.py`).
- **Orchestration:** `AI-Social-Agent/docker/docker-compose.yml` runs an **n8n** container mounting the `workflows/` folder (the workflows folder currently contains only a placeholder).

### What is **not** in the repo (and therefore must not appear in any output)
- No Terraform / IaC / CloudFormation / Pulumi files.
- No AWS service integrations — `boto3` is listed in `requirements.txt` but no module imports it.
- No RAG, embeddings, vector store, LangChain, LangGraph, OpenAI, Anthropic, or Groq client code.
- No Kubernetes, no cloud load balancer, no managed database, no CDN, no message broker beyond Redis used as a dedupe cache.
- No production metrics, SLOs, user counts, latency numbers, or revenue figures.

### Headline reality check
The candidate's stated headline is:

> *"AI Engineer | Designing Scalable AI Infrastructure (Agentic AI & RAG) | Building LLM Platforms | Terraform • Python • Data Pipelines"*

| Claim | Supported by repo? | Verdict |
|---|---|---|
| AI Engineer | Yes — multi-agent pipeline + Flask AI-adjacent backend | Keep |
| Agentic AI | Yes — Research/Strategy/Content agents with shared memory | Keep |
| RAG | **No** retrieval/vector/embedding code in repo | Treat as aspirational only |
| LLM Platforms | Partial — Ollama llama3 integration + prompt templates + HITL review UI | Reframe as "applied LLM workflows" |
| Terraform | **No** `.tf` / `.hcl` files in repo | Remove from evidence-based sections |
| Python | Yes — primary language | Keep |
| Data Pipelines | Yes — GitHub/ArXiv/RSS ingestion + JSON memory | Keep (framed as ingestion pipelines) |
| Scalable AI Infrastructure | **No** infra code; local Docker Compose only | Do not claim |

---

## 1. GitHub Rewrite (Strictly Real-Only)

### Unified profile README (short bio)

```markdown
### Hi, I'm Mike (Simbarashe) Ncube

AI engineer building practical AI and automation systems in Python.
I work on agentic pipelines, applied LLM workflows, and the backend engineering
that makes them usable — authentication, PII protection, rule-based detection,
alert correlation, and clean HTTP APIs.

**Current focus**
- Agentic AI pipelines (multi-agent research → strategy → content, human-in-the-loop review)
- Applied LLM workflows with local model runtimes (Ollama / llama3) and prompt templates
- Python backends with Flask, SQLAlchemy, JWT auth, and column-level encryption
- Data ingestion from public APIs and feeds (GitHub, ArXiv, RSS)
- Test-driven development with pytest and containerised local environments

**Toolbox (based on actual projects)**
Python · Flask · FastAPI · SQLAlchemy · Alembic · PostgreSQL · Redis ·
Ollama · n8n · Docker · Docker Compose · OpenTelemetry · pytest · Jinja2
```

### Cross-repo narrative (one line)

> *"I build agentic AI pipelines and the Python backends that serve them — from prompt-driven multi-agent workflows with human review, to multi-tenant Flask services with JWT, AES-256-GCM field encryption, PII masking, and rule-based detection."*

---

## 2. Repo-by-Repo Rewritten Descriptions

### 2.1 `proactive-sentinel` — Multi-tenant Flask SOC service

**Short description (GitHub repo blurb, ≤ 160 chars)**
> Multi-tenant Python/Flask SOC backend: JWT auth, AES-256-GCM field encryption, PII masking, rule-based detection, and MITRE-style alert correlation.

**Long description (pinned README section)**

- **Problem.** A tenant-aware security operations backend needs to ingest event logs, scrub personal identifiers before storage, apply detection rules, correlate related alerts, and expose the results through an authenticated HTTP API and a dashboard — without leaking data across tenants.
- **What exists in the repo.**
  - Flask application factory (`src/__init__.py`) wiring SQLAlchemy, Alembic, JWT, Flask-CORS, Flask-Limiter, and OpenTelemetry instrumentation.
  - Multi-tenant data model: `Tenant`, `User`, `Alert`, `AuditLog`, `Unit` (`src/models/*`) with UUID primary keys and per-tenant foreign keys; `init.sql` provisions `pgcrypto`, `uuid-ossp`, and a `set_tenant_context()` trigger helper for row-level-security policies.
  - AuthN/AuthZ: `JWTManager` issues HS256 access + refresh tokens; `require_auth` / `require_tenant` decorators enforce tenant scoping on every `/api/*` route. Passwords are bcrypt-hashed with a Werkzeug fallback path.
  - PII protection: `FieldEncryption` (AES-256-GCM via `cryptography`) exposed as a SQLAlchemy `TypeDecorator` and applied to user phone, name, address, and MFA secret columns; `VRLFilter` recursively masks South African national IDs, Zimbabwe IDs, and passport numbers inside structured telemetry payloads.
  - Detection: `DetectionEngine` flags file-access spikes per user; `UXObserver` emits alerts for slow claims (>2s), WhatsApp frustration, HTTP 404/500, negative sentiment on Facebook/X, Zendesk wait > 5 min, and CRM "incomplete applications" leakage; `ThreatDetector` enforces per-IP and per-unit request-velocity windows with an auto-ban after three violations.
  - Correlation: `CorrelationEngine` deduplicates alerts via SHA-256 fingerprints in Redis and groups alerts into MITRE ATT&CK–style attack chains using technique IDs (T1046, T1078, T1059, T1021, T1020, …), assigning a confidence score and a severity label.
  - API surface: `/api/health`, `/api/alerts`, `/api/alerts/<id>/dismiss`, `/api/stats`, `/api/tenants/current`, `/api/units/*`, `/api/auth/*`, `/api/audit/logs`; global rate-limiting and security response headers (HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy).
  - Observability: OpenTelemetry API/SDK with Flask + SQLAlchemy instrumentation and an OTLP/gRPC exporter, JSON-formatted request logs with correlation IDs.
  - Frontend: server-rendered SOC dashboard (`templates/dashboard.html` + `dashboard/`) served by Flask.
  - Local runtime: `docker-compose.yml` provisions Postgres 15 and Redis 7 alongside the Flask app; `Dockerfile` builds a non-root `python:3.11-slim` image and runs under gunicorn.
  - Tests: pytest suites for PII masking, detection logic, tenant isolation, and API flows.
- **Technical approach.** Clean separation into `api/`, `auth/`, `models/`, `repositories/`, `services/`, `detections/`, `security/`, `utils/`; dependency-injected Flask extensions; decorator-based auth + tenant scoping; TypeDecorator pattern for transparent encryption; Redis-backed dedup with TTL; MITRE technique grouping as a confidence signal rather than a hard classifier.
- **Value (supported).** Demonstrates the engineering fundamentals expected of an AI engineer who also builds the serving layer: tenant isolation, key-separated field encryption, PII scrubbing, rule-based alerting, alert correlation, rate limiting, observability hooks, and a tested HTTP surface.

### 2.2 `AI-Social-Agent` (sub-project) — Agentic content pipeline with human review

**Short description**
> Python multi-agent pipeline (Research → Strategy → Content) running on local Ollama/llama3, with a FastAPI human-in-the-loop review dashboard and n8n orchestration.

**Long description**

- **Problem.** Turn fresh signals about AI tooling into platform-specific social posts without losing editorial control.
- **What exists in the repo.**
  - Three specialised agents in `scripts/enhanced_agents.py`:
    - **Research agent** — ingests GitHub trending repos, ArXiv recent papers, and an O'Reilly AI RSS feed (`scripts/data_sources.py`) and summarises the top three trends using a prompt template (`agents/prompts/research_agent.txt`).
    - **Strategy agent** — expands research into three LinkedIn content angles (`agents/prompts/strategy_agent.txt`).
    - **Content agent** — generates platform-specific posts for LinkedIn / X / Instagram / TikTok using per-platform prompt files.
  - Shared **file-based memory** under `agents/memory/` (research, strategy, posts, approvals, schedules, published markers); a lightweight brand-voice note at `agents/memory/brand-voice.md`.
  - **Model runtime.** All LLM calls go through `scripts/helpers.py::query_ollama`, which hits a local **Ollama** server at `http://localhost:11434/api/generate` using `llama3`.
  - **Human-in-the-loop review UI** (`dashboard/app.py`, FastAPI + Jinja2): list / filter / view posts, approve, reject, schedule, bulk-approve, bulk-schedule, analytics (by platform, by status, by weekday), and a "run pipeline" button that shells out to the agent script.
  - **Scheduler** (`scripts/scheduler.py`): weekday-gated job loop that picks up approved-but-unscheduled posts and simulates posting to each platform.
  - **Orchestration stub**: `docker/docker-compose.yml` runs an **n8n** container with basic auth and a mounted `workflows/` folder for future event-driven orchestration.
- **Technical approach.** Small, stateless agent functions coordinated through the filesystem; prompt templates are version-controlled plain text; platform specialisation happens through prompt routing in the content agent; approvals are just sentinel JSON files, which keeps the review loop debuggable and portable.
- **Value (supported).** A working end-to-end agentic loop (signal → plan → draft → human gate → schedule) on a local model runtime, with a clean separation between agent logic, data sources, and UI.
- **Known limitations (documented honestly).** Posting is simulated; the vector/brand-memory DB mentioned in the README is not yet implemented; n8n workflows are placeholders; there is no retrieval-augmented layer yet.

---

## 3. Pinned Repositories (selection)

Because this evidence base is effectively two substantive projects in one monorepo, the pin recommendation is:

1. **`proactive-sentinel`** — lead pin. Strongest engineering signal: multi-tenant Flask backend, JWT, AES-256-GCM field encryption, PII masking, rule-based detection, MITRE-style correlation, OTel instrumentation, Docker Compose, pytest.
2. **`AI-Social-Agent`** (as its own pinned repo if extracted, or prominently linked from the root README) — strongest AI signal: multi-agent pipeline, Ollama/llama3 integration, data ingestion from GitHub/ArXiv/RSS, FastAPI human-review UI, n8n scaffolding.

Do **not** pin repos that cannot be verified in the codebase; the headline's RAG / Terraform / "scalable AI infrastructure" claims are not backed by code in this repository and must not drive pin selection.

---

## 4. Portfolio Rewrite (safe version)

**Hero**

> Mike (Simbarashe) Ncube — AI Engineer
> I build agentic AI pipelines and the Python backends that serve them.

**About**

> I work at the intersection of applied AI and backend engineering. My projects
> pair multi-agent LLM workflows with the unglamorous-but-essential parts:
> authentication, tenant isolation, PII protection, rule-based detection, and
> clean HTTP APIs. I prefer local model runtimes for iteration, containerised
> local environments, and test coverage that actually exercises the detection
> and auth paths.

**Selected work**

- **Proactive Sentinel — multi-tenant Flask SOC service (Python).**
  Tenant-aware backend with JWT auth, bcrypt passwords, AES-256-GCM field
  encryption for PII columns, recursive masking of SA/Zim IDs and passports,
  rule-based and heuristic detections, Redis-backed alert deduplication,
  MITRE-technique attack-chain grouping, rate limiting, OpenTelemetry
  instrumentation, and a server-rendered SOC dashboard. Postgres + Redis via
  Docker Compose; pytest coverage for PII masking, detections, and tenant
  isolation.

- **AI-Social-Agent — agentic content pipeline (Python).**
  Research → Strategy → Content multi-agent pipeline running on local Ollama
  (`llama3`), pulling signals from the GitHub API, ArXiv, and an O'Reilly AI
  RSS feed. File-based shared memory, per-platform prompt templates for
  LinkedIn / X / Instagram / TikTok, a FastAPI + Jinja2 human-in-the-loop
  review dashboard (approve / reject / schedule / bulk-approve / analytics),
  and an n8n container ready for workflow orchestration.

**Skills (evidence-based)**

Python · Flask · FastAPI · SQLAlchemy · Alembic · PostgreSQL · Redis · JWT ·
bcrypt · AES-256-GCM (cryptography) · Regex-based PII masking · Ollama /
llama3 · Prompt engineering · Multi-agent design · OpenTelemetry · Docker ·
Docker Compose · n8n · pytest · Jinja2

**What I'm exploring next (aspirational, not claimed as delivered)**

Retrieval-augmented generation, vector stores for brand/agent memory,
cloud-managed deployment, and infrastructure-as-code workflows.

---

## 5. ATS CV — AI Engineer Focus

> Plain-text, single-column, no tables, no graphics, no icons. Safe for ATS parsing. All bullets are traceable to files in this repo.

```
MIKE (SIMBARASHE) NCUBE
AI Engineer — Agentic AI, Applied LLM Workflows, Python Backends
Email: [add] | GitHub: github.com/MikeNcube | LinkedIn: [add] | Location: [add]

PROFESSIONAL SUMMARY
AI engineer building agentic AI pipelines and the Python backends that serve
them. Experienced with multi-agent LLM workflows on local model runtimes,
Flask/FastAPI services, multi-tenant data models, JWT authentication, AES-256
field-level encryption, PII masking, rule-based detection, and alert
correlation. Comfortable with Docker-based local environments, pytest, and
OpenTelemetry instrumentation.

CORE SKILLS
Languages: Python 3.11
AI / LLM: Agentic multi-agent pipelines, prompt-template design, Ollama
  (local llama3), human-in-the-loop review loops
Backend: Flask, FastAPI, SQLAlchemy 2.x, Alembic, Jinja2, Flask-Limiter,
  Flask-CORS, flask-jwt-extended
Data: PostgreSQL, Redis (dedup cache), public-API and RSS ingestion
  (GitHub Search, ArXiv Atom, O'Reilly RSS)
Security: JWT (HS256 access + refresh), bcrypt, AES-256-GCM column
  encryption, regex-based PII masking (SA ID, Zim ID, passport),
  rate-limiting, secure response headers, tenant isolation
Observability: OpenTelemetry (API/SDK, Flask + SQLAlchemy
  instrumentation, OTLP/gRPC), JSON request logging, correlation IDs
Tooling: Docker, Docker Compose, n8n, pytest, pytest-flask, factory-boy,
  Makefile, gunicorn

PROJECTS

Proactive Sentinel — Multi-tenant Python/Flask SOC Service (Open Source)
- Designed a Flask application-factory service with tenant-scoped auth,
  bcrypt password hashing, and JWT access + refresh tokens.
- Implemented AES-256-GCM column-level encryption using a SQLAlchemy
  TypeDecorator; applied it to user PII fields (phone, full name, address,
  MFA secret) with a dedicated ENCRYPTION_KEY separate from JWT secrets.
- Built a recursive PII masking layer for structured telemetry, covering
  South African national IDs, Zimbabwe IDs, and passport number patterns.
- Implemented rule-based detections for user file-access spikes and UX
  degradation (slow claims, WhatsApp frustration, HTTP 4xx/5xx, negative
  sentiment on social channels, Zendesk latency, CRM lead leakage).
- Built an alert correlation engine that deduplicates alerts via SHA-256
  fingerprints in Redis and groups them into MITRE ATT&CK–style attack
  chains using technique IDs, with a confidence score per chain.
- Added a per-IP and per-unit request-velocity threat detector with an
  auto-ban after repeated violations and a unit-compromise signal.
- Exposed `/api/health`, `/api/alerts`, `/api/alerts/<id>/dismiss`,
  `/api/stats`, `/api/tenants/current`, `/api/units/*`, `/api/auth/*`, and
  `/api/audit/logs`; added Flask-Limiter rate limiting and hardened
  response headers (HSTS, X-Frame-Options, X-Content-Type-Options).
- Instrumented the stack with OpenTelemetry (Flask + SQLAlchemy, OTLP/gRPC)
  and structured JSON logging with correlation IDs.
- Packaged the service with a non-root `python:3.11-slim` Docker image and
  a Docker Compose stack including Postgres 15 and Redis 7; added an
  `init.sql` that enables `pgcrypto`, `uuid-ossp`, and a tenant-context
  helper function for row-level-security policies.
- Wrote pytest suites covering PII masking, detection engine behaviour,
  tenant isolation, and API flows.

AI-Social-Agent — Agentic Content Pipeline (Open Source)
- Built a three-agent Python pipeline (Research → Strategy → Content) that
  turns fresh AI-ecosystem signals into platform-specific social posts.
- Integrated a local Ollama runtime (`llama3`) via HTTP for all LLM calls,
  keeping iteration fast and free of external API dependencies.
- Implemented a data-ingestion module pulling from the GitHub Search API
  (trending repos by topic), the ArXiv Atom feed, and an O'Reilly AI RSS
  feed; persisted results as timestamped JSON for downstream agents.
- Designed version-controlled prompt templates per agent and per platform
  (LinkedIn, X, Instagram, TikTok), plus hook-writer, body-generator, and
  strategist sub-prompts.
- Built a FastAPI + Jinja2 human-in-the-loop review dashboard supporting
  list/filter/view, approve, reject, schedule, bulk-approve, bulk-schedule,
  and per-platform / per-status / per-weekday analytics.
- Added a weekday-gated scheduler that picks up approved-but-unscheduled
  posts and simulates posting to each platform.
- Stood up an n8n container via Docker Compose with a mounted workflows
  folder for future event-driven orchestration.

EDUCATION
[Degree, Institution, Year] — keep existing entry

CERTIFICATIONS
[Only keep entries that are real and verifiable]
```

**ATS keywords deliberately included (all evidence-backed):** AI Engineer,
Agentic AI, multi-agent, LLM, prompt engineering, Ollama, Python, Flask,
FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis, JWT, bcrypt, AES-256,
encryption, PII, multi-tenant, rate limiting, OpenTelemetry, Docker, Docker
Compose, n8n, pytest, MITRE ATT&CK, alert correlation, data pipelines.

**ATS keywords deliberately *excluded* because they are not in the repo:**
AWS, S3, Lambda, EKS, Kubernetes, Terraform, CloudFormation, RAG, vector
database, embeddings, LangChain, LangGraph, OpenAI, Anthropic, Groq,
production scale, SLO, SLA, microservices at scale.

---

## 6. General Tech CV (Software / AI, broader positioning)

> Same truth base, wider framing. Still no AWS / Terraform / RAG claims.

```
MIKE (SIMBARASHE) NCUBE
Software Engineer — Python Backends & Applied AI
Email: [add] | GitHub: github.com/MikeNcube | LinkedIn: [add]

SUMMARY
Python engineer who builds backends and applied-AI systems end-to-end.
Comfortable owning a service from data model through HTTP API to
containerised runtime, with pragmatic security (JWT, field-level
encryption, PII masking) and lightweight observability. Also builds
multi-agent LLM workflows on local model runtimes with human-in-the-loop
review.

TECHNICAL SKILLS
Languages: Python 3
Web / API: Flask, FastAPI, Jinja2, REST, blueprints, decorators
Data: PostgreSQL, Redis, SQLAlchemy 2.x ORM, Alembic migrations,
  public-API and RSS ingestion
Security & Auth: JWT (HS256), bcrypt, AES-256-GCM, PII masking,
  tenant isolation, rate limiting, secure headers
AI / LLM: Multi-agent pipelines, prompt-template design, local Ollama
  (`llama3`), human-in-the-loop review workflows
DevEx / Runtime: Docker, Docker Compose, gunicorn, Makefile, pytest,
  OpenTelemetry, structured JSON logging
Other: n8n (workflow scaffolding), Git, Linux

SELECTED PROJECTS

Multi-tenant Flask SOC service (Python / PostgreSQL / Redis)
- Application-factory Flask service with JWT auth, bcrypt passwords, and
  tenant-scoped decorators on every `/api/*` route.
- AES-256-GCM column-level encryption via a SQLAlchemy TypeDecorator,
  applied to user PII fields.
- Recursive PII masking for South African / Zimbabwean IDs and passport
  numbers in structured telemetry payloads.
- Rule-based detection engine plus a UX-observer module covering slow
  claims, channel frustration, HTTP 4xx/5xx, social-sentiment outcry,
  support latency, and CRM lead leakage.
- Redis-backed alert deduplication and MITRE-technique attack-chain
  grouping.
- Per-IP and per-unit velocity throttling with auto-ban on repeated
  violations.
- OpenTelemetry instrumentation, rate limiting, secure response headers,
  Docker Compose with Postgres + Redis, pytest coverage.

Agentic content pipeline (Python / FastAPI / Ollama)
- Research → Strategy → Content multi-agent loop; prompts are
  version-controlled text.
- GitHub Search API, ArXiv feed, and O'Reilly RSS ingestion with
  JSON persistence.
- Local Ollama (`llama3`) runtime for all LLM calls.
- FastAPI + Jinja2 human-review dashboard with approvals, scheduling,
  bulk operations, and analytics.
- Docker Compose with n8n container ready for orchestration.

EDUCATION
[Keep existing entry]
```

---

## 7. Consistency Audit Report

| Surface | Headline claim | Evidence in repo | Action |
|---|---|---|---|
| LinkedIn headline | "Scalable AI Infrastructure" | None (local Docker Compose only) | Soften in bio; keep only as aspirational phrase in the "exploring next" section; remove from CV/portfolio evidence claims. |
| LinkedIn headline | "Agentic AI & RAG" | Agentic: YES. RAG: NO | Keep "Agentic AI". Remove "RAG" from CV / portfolio / pinned repo blurbs; allow it only on LinkedIn "Open to learn" or future-work sections. |
| LinkedIn headline | "Building LLM Platforms" | Ollama integration + prompt templates + review UI only | Reframe as "Applied LLM workflows" across CV and portfolio. |
| LinkedIn headline | "Terraform" | No `.tf` / `.hcl` files | Remove from skills list in ATS CV and portfolio skills block. May stay on LinkedIn as a learning interest only if honestly labelled. |
| CV skills | Python, Flask, FastAPI, SQLAlchemy, JWT, bcrypt, AES-256, PII masking, Ollama, Docker, pytest | All present | Keep. |
| CV skills | AWS / S3 / Lambda / Kubernetes | Not present (`boto3` unused) | Do not list. |
| Portfolio | Multi-tenant SOC + Agentic content pipeline | Both present | Keep, mirrored in CV. |
| Pinned repos | Proactive Sentinel + AI-Social-Agent | Both strong | Pin both. |

**Net changes to apply across LinkedIn + Portfolio + GitHub + CV:**

1. Drop **RAG**, **Terraform**, and **"scalable AI infrastructure"** from anywhere that presents them as delivered work.
2. Standardise the AI framing as **"Agentic AI + Applied LLM workflows (local Ollama)"**.
3. Standardise the backend framing as **"Python backends (Flask/FastAPI) with JWT, field-level encryption, PII masking, rule-based detection, and alert correlation"**.
4. Use the same project blurbs on GitHub, portfolio, and CV so a recruiter reading all three sees one consistent story.

---

## 8. Recruiter Perception Summary

**Before (current public framing).**
A senior-sounding headline ("Scalable AI Infrastructure, Agentic AI & RAG, LLM
Platforms, Terraform") that an experienced AI hiring manager will stress-test
against the repo — and find gaps: no IaC, no RAG, no cloud infrastructure.
Result: credibility risk. The real, very respectable work gets discounted
because the framing has outrun the evidence.

**After (repositioned).**
A mid-to-senior AI engineer who can do two things most candidates can't do
together:

1. **Build an agentic AI loop end-to-end** — multi-agent pipeline, local LLM
   runtime, structured prompts, data ingestion from real public sources, and a
   human-in-the-loop review UI. Pragmatic, inspectable, and runnable on a
   laptop.
2. **Ship the backend engineering around it** — multi-tenant Flask service
   with JWT, bcrypt, AES-256-GCM field encryption, PII masking for regional
   identifiers, rule-based and heuristic detections, Redis-backed alert
   deduplication, MITRE-style correlation, rate limiting, OpenTelemetry
   instrumentation, and tests.

**ATS pass rate.** The new CV hits the AI-engineer keyword cluster (AI
Engineer, Agentic AI, multi-agent, LLM, prompt engineering, Ollama, Python,
Flask, FastAPI, PostgreSQL, Redis, JWT, AES-256, PII, multi-tenant,
OpenTelemetry, Docker, pytest, MITRE ATT&CK, alert correlation, data
pipelines) without stuffing unverifiable terms. It should pass common
AI-engineer and Python-backend ATS filters cleanly.

**Recruiter takeaway in one sentence.**
> *"Mike is an AI engineer who builds agentic pipelines on local LLMs and
> the secure, multi-tenant Python backends that serve them — grounded,
> tested, and honest about scope."*

---

## Appendix — Edits to make on existing public surfaces

- **LinkedIn headline (suggested replacement, still strong, now defensible):**
  `AI Engineer | Agentic AI & Applied LLM Workflows | Python Backends (Flask/FastAPI) | Data Pipelines`
- **LinkedIn About (first paragraph):** reuse the Portfolio "About" block.
- **GitHub profile README:** use the block in Section 1.
- **GitHub repo descriptions:** use the short descriptions in Section 2.
- **Portfolio site:** use Section 4 verbatim.
- **CV — AI-focused role applications:** Section 5.
- **CV — broader software/AI applications:** Section 6.
- **Interview prep note:** be ready to demo the Ollama agent loop and to walk
  through `src/encryption.py`, `detections/vrl_filter.py`, and
  `src/services/correlation_engine.py` — they are the three files that most
  concretely back the repositioned story.
