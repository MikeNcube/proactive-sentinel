# Mike (Simbarashe) Ncube — ATS CV (AI Engineer, Full-Time)

> Evidence-based. Every claim is traceable to a repository on github.com/MikeNcube or to a listed certification on `mike-ncube-github-io.vercel.app`.

---

**MIKE (SIMBARASHE) NCUBE**
AI Engineer — Agentic AI, RAG, Applied LLM Workflows, AWS Cloud, Python Backends
Johannesburg, Gauteng, South Africa | GitHub: github.com/MikeNcube | Portfolio: mike-ncube-github-io.vercel.app | Email: [add] | LinkedIn: [add]

## PROFESSIONAL SUMMARY

AI engineer who designs, ships, and operates production-grade AI and data systems end-to-end. Builds agentic AI pipelines, applied LLM workflows, and Retrieval-Augmented Generation systems, backed by Python services (Flask/FastAPI) and AWS cloud architecture (ALB, Auto Scaling, multi-AZ, EC2, VPC, IAM, S3, RDS, Kinesis). Delivers regulated real-world products (POPIA, FIC, FAIS) with JWT authentication, AES-256 field-level encryption, PII masking, rule-based detection, alert correlation, OpenTelemetry instrumentation, Terraform infrastructure-as-code, Airflow orchestration, and Great Expectations data quality.

## CORE SKILLS

- **Languages:** Python 3.11, SQL, Bash, HTML/CSS
- **AI / LLM:** Agentic multi-agent pipelines, Retrieval-Augmented Generation, LangChain, prompt engineering, Ollama (local llama3), LLM orchestration, vector databases, human-in-the-loop review loops
- **Cloud (AWS):** ALB, EC2 Auto Scaling, multi-AZ VPC, IAM, S3, RDS (PostgreSQL), Kinesis, CloudWatch, Security Groups, NACLs
- **Data engineering:** Apache Airflow (DAGs), Great Expectations, Pandas, Neo4j, boto3, streaming + batch ETL, data contracts
- **Infrastructure-as-Code:** Terraform
- **Backend:** Flask, FastAPI, SQLAlchemy 2.x, Alembic, Jinja2, Flask-Limiter, Flask-CORS, flask-jwt-extended, Pydantic, Uvicorn, Gunicorn
- **Data stores:** PostgreSQL, Redis, SQLite
- **Security:** JWT (HS256 access + refresh), bcrypt, AES-256-GCM column encryption, regex-based PII masking (SA ID, Zim ID, passport), POPIA / FIC / FAIS compliance, SMTP SSL, tenant isolation, rate limiting, secure response headers
- **Observability:** OpenTelemetry (API/SDK, Flask + SQLAlchemy instrumentation, OTLP/gRPC), JSON structured logging, correlation IDs
- **Delivery:** Docker, Docker Compose, Railway, CI/CD, nixpacks, Gunicorn, pytest, pytest-flask, factory-boy, Makefile, ReportLab (PDF generation), n8n

## PROJECT EXPERIENCE

### Zororo Phumulani — Digital Policy Application Platform (FastAPI, regulated Insurtech)

- Built and deployed a 1,400+ line FastAPI application serving a POPIA-compliant funeral-insurance policy onboarding flow under FSP48558, underwritten by KGA Life FSP15980.
- Implemented a 7-step workflow engine (identity verification, 18+ age validation, FIC-compliant ID upload, POPIA/FAIS consent capture, payment integration, automated policy generation, audit logging) with dependency enforcement between steps.
- Generated branded policy PDFs on the fly with ReportLab, dispatched client and admin notifications over SMTP SSL (port 465), and persisted submissions to SQLite with IP + consent-version audit trails.
- Packaged the service with a Dockerfile + nixpacks.toml + Procfile and deployed it to Railway with zero-downtime releases.
- Exposed a versioned REST API (`/api/v1/rates`, `/api/v1/policies`, `/api/v1/policies/{ref}`, `/api/health`) consumed by the web front-end.

### Proactive Sentinel — Multi-tenant Python/Flask SOC Service

- Designed a Flask application-factory service with tenant-scoped auth, bcrypt password hashing, and JWT access + refresh tokens.
- Implemented AES-256-GCM column-level encryption via a SQLAlchemy TypeDecorator for user PII fields (phone, full name, address, MFA secret) with a dedicated ENCRYPTION_KEY separate from JWT secrets.
- Built a recursive PII masking layer for structured telemetry covering South African national IDs, Zimbabwe IDs, and passport number patterns.
- Implemented rule-based detections and a UX-observer (slow claims, WhatsApp frustration, HTTP 4xx/5xx, negative sentiment, Zendesk latency, CRM lead leakage) and a per-IP / per-unit velocity threat detector with auto-ban after repeated violations.
- Built an alert correlation engine that deduplicates via SHA-256 fingerprints in Redis and groups alerts into MITRE ATT&CK attack chains using technique IDs, with a confidence score per chain.
- Instrumented the stack with OpenTelemetry (Flask + SQLAlchemy, OTLP/gRPC) and structured JSON logging with correlation IDs; packaged with a non-root python:3.11-slim image and a Docker Compose stack including Postgres 15 and Redis 7.
- Bundled an `AI-Social-Agent` sub-project: a three-agent Python pipeline (Research, Strategy, Content) on local Ollama (llama3), ingesting from the GitHub Search API, ArXiv feed, and RSS feeds, with a FastAPI + Jinja2 human-in-the-loop review dashboard and n8n orchestration container.

### End-to-End Recommender System Data Pipeline (Airflow, FastAPI, Terraform)

- Built a data-engineering pipeline with Apache Airflow DAGs for daily orchestration, Great Expectations for data-quality validation, and Terraform (`main.tf`) provisioning AWS S3 buckets for landing-zone storage.
- Exposed a FastAPI inference API (`/process`, `/health`) with Pydantic request/response models, Pandas/NumPy transforms, and Uvicorn runtime.
- Implemented boto3 producers for AWS Kinesis streaming ingestion and staged Neo4j for graph-enriched ratings.
- Organised the repo into `src/`, `api/`, `dags/`, `airflow/`, `scripts/` (batch + streaming ETL), `sql/`, `notebooks/`, and `tests/` for clean separation of concerns.

### Resilient Web Tier on AWS — ALB + Auto Scaling, Multi-AZ

- Designed a highly available AWS web tier: Application Load Balancer with health checks, EC2 Auto Scaling Group across multiple Availability Zones, CloudWatch-driven scale-out/scale-in on CPU and request metrics, VPC with private subnets, and IAM least-privilege roles.
- Built the underlying Flask service (`app/server.py`) to expose an AZ-aware health endpoint that surfaces the serving host and Availability Zone for ALB target-health verification.
- Authored architecture documentation, an operations guide, and a load-test plan under `docs/` and `stress/`; shipped a deploy script and a pytest suite.

### Cloud Data Engineering Portfolio (Terraform, Airflow, Great Expectations)

- Compact end-to-end demonstration of cloud data engineering: Terraform (AWS S3) IaC, Airflow DAG scaffold, Great Expectations YAML for data-quality, boto3 Kinesis producer, Neo4j + Pandas + Python dependencies.

### Cloud Project Board — RDS Connectivity Lab

- Hands-on troubleshooting lab for EC2-to-RDS PostgreSQL connectivity using VPC configuration, subnet routing, Security Groups, NACLs, IAM roles, and boto3 automation.

## EDUCATION

[Degree, Institution, Year] — keep existing real entry

## CERTIFICATIONS

- Generative AI with Large Language Models — DeepLearning.AI
- Retrieval-Augmented Generation (RAG) Systems — DeepLearning.AI
- Agentic AI — DeepLearning.AI
- LangChain for LLM Applications — DeepLearning.AI
- AWS Generative AI Introduction
- AWS Machine Learning Foundations
- Data Engineering Bootcamp
- Generative AI Introduction — Udacity

## ADDITIONAL INFORMATION

- **Public portfolio:** mike-ncube-github-io.vercel.app
- **GitHub:** github.com/MikeNcube (public repos: digi-app-form, End-to-End-Recommender-System-Data-Pipeline, Resilient-Web-Tier-on-AWS-ALB-Auto-Scaling, cloud-data-engineering-portfolio, cloud-project-board-rds-connectivity-lab, MikeNcube.github.io)

### Keywords

AI Engineer, AI Infrastructure, Agentic AI, RAG, Retrieval-Augmented Generation, LangChain, LLM, prompt engineering, Ollama, llama3, vector databases, multi-agent, Python, Flask, FastAPI, SQLAlchemy, Alembic, Pydantic, Uvicorn, Gunicorn, PostgreSQL, Redis, SQLite, Apache Airflow, Great Expectations, Terraform, AWS, ALB, EC2, Auto Scaling, multi-AZ, VPC, IAM, S3, RDS, Kinesis, CloudWatch, boto3, Pandas, Neo4j, JWT, bcrypt, AES-256, encryption, PII, POPIA, FIC, FAIS, SMTP SSL, ReportLab, multi-tenant, rate limiting, OpenTelemetry, Docker, Docker Compose, Railway, CI/CD, pytest, MITRE ATT&CK, alert correlation, data pipelines, ETL, streaming, data quality.
