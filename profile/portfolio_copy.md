# Portfolio site copy (safe version)

> Drop-in copy for a personal portfolio. Mirrors the CV and GitHub exactly.

---

## Hero

**Mike (Simbarashe) Ncube — AI Engineer**
I build agentic AI pipelines and the Python backends that serve them.

## About

I work at the intersection of applied AI and backend engineering. My projects pair multi-agent LLM workflows with the unglamorous-but-essential parts: authentication, tenant isolation, PII protection, rule-based detection, and clean HTTP APIs. I prefer local model runtimes for iteration, containerised local environments, and test coverage that actually exercises the detection and auth paths.

## Selected Work

### Proactive Sentinel — multi-tenant Flask SOC service (Python)

Tenant-aware backend with JWT auth, bcrypt passwords, AES-256-GCM field encryption for PII columns, recursive masking of SA/Zim IDs and passports, rule-based and heuristic detections, Redis-backed alert deduplication, MITRE-technique attack-chain grouping, rate limiting, OpenTelemetry instrumentation, and a server-rendered SOC dashboard. Postgres + Redis via Docker Compose; pytest coverage for PII masking, detections, and tenant isolation.

**Stack:** Python · Flask · SQLAlchemy · Alembic · PostgreSQL · Redis · JWT · bcrypt · AES-256-GCM · OpenTelemetry · Docker Compose · pytest

### AI-Social-Agent — agentic content pipeline (Python)

Research → Strategy → Content multi-agent pipeline running on local Ollama (`llama3`), pulling signals from the GitHub API, ArXiv, and an O'Reilly AI RSS feed. File-based shared memory, per-platform prompt templates for LinkedIn / X / Instagram / TikTok, a FastAPI + Jinja2 human-in-the-loop review dashboard (approve / reject / schedule / bulk-approve / analytics), and an n8n container ready for workflow orchestration.

**Stack:** Python · FastAPI · Jinja2 · Ollama (llama3) · GitHub API · ArXiv · RSS · Docker Compose · n8n

## Skills (evidence-based)

Python · Flask · FastAPI · SQLAlchemy · Alembic · PostgreSQL · Redis · JWT · bcrypt · AES-256-GCM (cryptography) · Regex-based PII masking · Ollama / llama3 · Prompt engineering · Multi-agent design · OpenTelemetry · Docker · Docker Compose · n8n · pytest · Jinja2

## What I'm exploring next

Retrieval-augmented generation, vector stores for agent/brand memory, cloud-managed deployment, and infrastructure-as-code workflows. (Listed as *exploration*, not delivered work.)
