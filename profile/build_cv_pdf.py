"""
Build a strictly one-page, ATS-safe PDF CV from profile/cv_ats_ai_engineer.md.

ATS rules enforced:
  - Single column, no tables, no icons, no graphics, no colors.
  - No emojis, no decorative separator lines or decorative hyphens.
  - Standard Helvetica (PDF equivalent of Arial/Calibri).
  - Bullet character is a plain "-" to maximize ATS compatibility.
  - Content is preserved from the source markdown.
  - Layout order: Name + title, Contact, Summary, Core Skills,
    Project Experience, Education, Certifications, Additional Info,
    Keywords.
"""

from pathlib import Path

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
)


OUT_PATH = Path(__file__).parent / "Mike_Simbarashe_Ncube_AI_Engineer_CV.pdf"

FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
BLACK = "#000000"


def make_styles():
    base = ParagraphStyle(
        "Base",
        fontName=FONT,
        fontSize=6.9,
        leading=8.2,
        textColor=BLACK,
        alignment=TA_LEFT,
        spaceBefore=0,
        spaceAfter=0,
    )

    name = ParagraphStyle(
        "Name",
        parent=base,
        fontName=FONT_BOLD,
        fontSize=11,
        leading=12.5,
        spaceAfter=1,
    )

    title = ParagraphStyle(
        "Title",
        parent=base,
        fontSize=7.6,
        leading=9,
        spaceAfter=1,
    )

    contact = ParagraphStyle(
        "Contact",
        parent=base,
        fontSize=6.9,
        leading=8.2,
        spaceAfter=3,
    )

    section = ParagraphStyle(
        "Section",
        parent=base,
        fontName=FONT_BOLD,
        fontSize=8,
        leading=9.6,
        spaceBefore=3,
        spaceAfter=1,
    )

    subsection = ParagraphStyle(
        "Subsection",
        parent=base,
        fontName=FONT_BOLD,
        fontSize=7.4,
        leading=8.9,
        spaceBefore=1.5,
        spaceAfter=0,
    )

    body = ParagraphStyle(
        "Body",
        parent=base,
        fontSize=6.9,
        leading=8.2,
        spaceAfter=1.5,
    )

    bullet = ParagraphStyle(
        "Bullet",
        parent=body,
        spaceAfter=0,
        leading=8.2,
    )

    return {
        "name": name,
        "title": title,
        "contact": contact,
        "section": section,
        "subsection": subsection,
        "body": body,
        "bullet": bullet,
    }


def bullets(items, style):
    return ListFlowable(
        [ListItem(Paragraph(t, style), leftIndent=7) for t in items],
        bulletType="bullet",
        start="-",
        leftIndent=8,
        bulletFontName=FONT,
        bulletFontSize=6.9,
        bulletOffsetY=0,
        spaceBefore=0,
        spaceAfter=1.5,
    )


def build():
    styles = make_styles()
    doc = SimpleDocTemplate(
        str(OUT_PATH),
        pagesize=LETTER,
        leftMargin=0.38 * inch,
        rightMargin=0.38 * inch,
        topMargin=0.3 * inch,
        bottomMargin=0.3 * inch,
        title="Mike Simbarashe Ncube - AI Engineer CV",
        author="Mike Simbarashe Ncube",
        subject="Curriculum Vitae",
        creator="profile/build_cv_pdf.py",
    )

    story = []

    story.append(Paragraph("MIKE (SIMBARASHE) NCUBE", styles["name"]))
    story.append(
        Paragraph(
            "AI Engineer &mdash; Agentic AI, RAG, Applied LLM Workflows, AWS Cloud, Python Backends",
            styles["title"],
        )
    )
    story.append(
        Paragraph(
            "Johannesburg, Gauteng, South Africa | GitHub: github.com/MikeNcube | "
            "Portfolio: mike-ncube-github-io.vercel.app | Email: [add] | LinkedIn: [add]",
            styles["contact"],
        )
    )

    story.append(Paragraph("PROFESSIONAL SUMMARY", styles["section"]))
    story.append(
        Paragraph(
            "AI engineer who designs, ships, and operates production-grade AI and "
            "data systems end-to-end. Builds agentic AI pipelines, applied LLM "
            "workflows, and Retrieval-Augmented Generation systems, backed by "
            "Python services (Flask/FastAPI) and AWS cloud architecture (ALB, "
            "Auto Scaling, multi-AZ, EC2, VPC, IAM, S3, RDS, Kinesis). Delivers "
            "regulated real-world products (POPIA, FIC, FAIS) with JWT "
            "authentication, AES-256 field-level encryption, PII masking, "
            "rule-based detection, alert correlation, OpenTelemetry "
            "instrumentation, Terraform infrastructure-as-code, Airflow "
            "orchestration, and Great Expectations data quality.",
            styles["body"],
        )
    )

    story.append(Paragraph("CORE SKILLS", styles["section"]))
    core_skills = [
        "<b>Languages:</b> Python 3.11, SQL, Bash, HTML/CSS",
        "<b>AI / LLM:</b> Agentic multi-agent pipelines, Retrieval-Augmented Generation, "
        "LangChain, prompt engineering, Ollama (local llama3), LLM orchestration, "
        "vector databases, human-in-the-loop review loops",
        "<b>Cloud (AWS):</b> ALB, EC2 Auto Scaling, multi-AZ VPC, IAM, S3, RDS "
        "(PostgreSQL), Kinesis, CloudWatch, Security Groups, NACLs",
        "<b>Data engineering:</b> Apache Airflow (DAGs), Great Expectations, Pandas, "
        "Neo4j, boto3, streaming + batch ETL, data contracts",
        "<b>Infrastructure-as-Code:</b> Terraform",
        "<b>Backend:</b> Flask, FastAPI, SQLAlchemy 2.x, Alembic, Jinja2, "
        "Flask-Limiter, Flask-CORS, flask-jwt-extended, Pydantic, Uvicorn, Gunicorn",
        "<b>Data stores:</b> PostgreSQL, Redis, SQLite",
        "<b>Security:</b> JWT (HS256 access + refresh), bcrypt, AES-256-GCM column "
        "encryption, regex-based PII masking (SA ID, Zim ID, passport), POPIA / FIC "
        "/ FAIS compliance, SMTP SSL, tenant isolation, rate limiting, secure "
        "response headers",
        "<b>Observability:</b> OpenTelemetry (API/SDK, Flask + SQLAlchemy "
        "instrumentation, OTLP/gRPC), JSON structured logging, correlation IDs",
        "<b>Delivery:</b> Docker, Docker Compose, Railway, CI/CD, nixpacks, "
        "Gunicorn, pytest, pytest-flask, factory-boy, Makefile, ReportLab (PDF "
        "generation), n8n",
    ]
    story.append(bullets(core_skills, styles["bullet"]))

    story.append(Paragraph("PROJECT EXPERIENCE", styles["section"]))

    story.append(
        Paragraph(
            "Zororo Phumulani &mdash; Digital Policy Application Platform (FastAPI, regulated Insurtech)",
            styles["subsection"],
        )
    )
    zororo = [
        "Built and deployed a 1,400+ line FastAPI application serving a "
        "POPIA-compliant funeral-insurance policy onboarding flow under FSP48558, "
        "underwritten by KGA Life FSP15980.",
        "Implemented a 7-step workflow engine (identity verification, 18+ age "
        "validation, FIC-compliant ID upload, POPIA/FAIS consent capture, payment "
        "integration, automated policy generation, audit logging) with dependency "
        "enforcement between steps.",
        "Generated branded policy PDFs on the fly with ReportLab, dispatched "
        "client and admin notifications over SMTP SSL (port 465), and persisted "
        "submissions to SQLite with IP + consent-version audit trails.",
        "Packaged the service with a Dockerfile + nixpacks.toml + Procfile and "
        "deployed it to Railway with zero-downtime releases.",
        "Exposed a versioned REST API (/api/v1/rates, /api/v1/policies, "
        "/api/v1/policies/{ref}, /api/health) consumed by the web front-end.",
    ]
    story.append(bullets(zororo, styles["bullet"]))

    story.append(
        Paragraph(
            "Proactive Sentinel &mdash; Multi-tenant Python/Flask SOC Service",
            styles["subsection"],
        )
    )
    sentinel = [
        "Designed a Flask application-factory service with tenant-scoped auth, "
        "bcrypt password hashing, and JWT access + refresh tokens.",
        "Implemented AES-256-GCM column-level encryption via a SQLAlchemy "
        "TypeDecorator for user PII fields (phone, full name, address, MFA "
        "secret) with a dedicated ENCRYPTION_KEY separate from JWT secrets.",
        "Built a recursive PII masking layer for structured telemetry covering "
        "South African national IDs, Zimbabwe IDs, and passport number patterns.",
        "Implemented rule-based detections and a UX-observer (slow claims, "
        "WhatsApp frustration, HTTP 4xx/5xx, negative sentiment, Zendesk latency, "
        "CRM lead leakage) and a per-IP / per-unit velocity threat detector with "
        "auto-ban after repeated violations.",
        "Built an alert correlation engine that deduplicates via SHA-256 "
        "fingerprints in Redis and groups alerts into MITRE ATT&amp;CK attack "
        "chains using technique IDs, with a confidence score per chain.",
        "Instrumented with OpenTelemetry (Flask + SQLAlchemy, OTLP/gRPC) and "
        "structured JSON logging with correlation IDs; packaged with a non-root "
        "python:3.11-slim image and a Docker Compose stack (Postgres 15, Redis 7).",
        "Bundled an AI-Social-Agent sub-project: a three-agent Python pipeline "
        "(Research, Strategy, Content) on local Ollama (llama3), ingesting from "
        "the GitHub Search API, ArXiv feed, and RSS feeds, with a FastAPI + "
        "Jinja2 human-in-the-loop review dashboard and n8n orchestration "
        "container.",
    ]
    story.append(bullets(sentinel, styles["bullet"]))

    story.append(
        Paragraph(
            "End-to-End Recommender System Data Pipeline (Airflow, FastAPI, Terraform)",
            styles["subsection"],
        )
    )
    recom = [
        "Built a data-engineering pipeline with Apache Airflow DAGs for daily "
        "orchestration, Great Expectations for data-quality validation, and "
        "Terraform (main.tf) provisioning AWS S3 buckets for landing-zone storage.",
        "Exposed a FastAPI inference API (/process, /health) with Pydantic "
        "request/response models, Pandas/NumPy transforms, and Uvicorn runtime.",
        "Implemented boto3 producers for AWS Kinesis streaming ingestion and "
        "staged Neo4j for graph-enriched ratings.",
        "Organised the repo into src/, api/, dags/, airflow/, scripts/ (batch + "
        "streaming ETL), sql/, notebooks/, and tests/ for clean separation of "
        "concerns.",
    ]
    story.append(bullets(recom, styles["bullet"]))

    story.append(
        Paragraph(
            "Resilient Web Tier on AWS &mdash; ALB + Auto Scaling, Multi-AZ",
            styles["subsection"],
        )
    )
    aws_web = [
        "Designed a highly available AWS web tier: Application Load Balancer "
        "with health checks, EC2 Auto Scaling Group across multiple Availability "
        "Zones, CloudWatch-driven scale-out/scale-in on CPU and request metrics, "
        "VPC with private subnets, and IAM least-privilege roles.",
        "Built the underlying Flask service (app/server.py) to expose an "
        "AZ-aware health endpoint that surfaces the serving host and "
        "Availability Zone for ALB target-health verification.",
        "Authored architecture documentation, an operations guide, and a "
        "load-test plan under docs/ and stress/; shipped a deploy script and a "
        "pytest suite.",
    ]
    story.append(bullets(aws_web, styles["bullet"]))

    story.append(
        Paragraph(
            "Cloud Data Engineering Portfolio &amp; RDS Connectivity Lab",
            styles["subsection"],
        )
    )
    cloud_mini = [
        "Cloud Data Engineering Portfolio: compact end-to-end demo &mdash; "
        "Terraform (AWS S3) IaC, Airflow DAG scaffold, Great Expectations YAML "
        "for data-quality, boto3 Kinesis producer, Neo4j + Pandas.",
        "RDS Connectivity Lab: hands-on troubleshooting of EC2-to-RDS "
        "PostgreSQL using VPC configuration, subnet routing, Security Groups, "
        "NACLs, IAM roles, and boto3 automation.",
    ]
    story.append(bullets(cloud_mini, styles["bullet"]))

    story.append(Paragraph("EDUCATION", styles["section"]))
    story.append(
        Paragraph(
            "[Degree, Institution, Year] &mdash; keep existing real entry",
            styles["body"],
        )
    )

    story.append(Paragraph("CERTIFICATIONS", styles["section"]))
    certs = [
        "Generative AI with Large Language Models &mdash; DeepLearning.AI",
        "Retrieval-Augmented Generation (RAG) Systems &mdash; DeepLearning.AI",
        "Agentic AI &mdash; DeepLearning.AI",
        "LangChain for LLM Applications &mdash; DeepLearning.AI",
        "AWS Generative AI Introduction",
        "AWS Machine Learning Foundations",
        "Data Engineering Bootcamp",
        "Generative AI Introduction &mdash; Udacity",
    ]
    story.append(bullets(certs, styles["bullet"]))

    story.append(Paragraph("KEYWORDS", styles["section"]))
    story.append(
        Paragraph(
            "AI Engineer, AI Infrastructure, Agentic AI, RAG, Retrieval-Augmented "
            "Generation, LangChain, LLM, prompt engineering, Ollama, llama3, "
            "vector databases, multi-agent, Python, Flask, FastAPI, SQLAlchemy, "
            "Alembic, Pydantic, Uvicorn, Gunicorn, PostgreSQL, Redis, SQLite, "
            "Apache Airflow, Great Expectations, Terraform, AWS, ALB, EC2, Auto "
            "Scaling, multi-AZ, VPC, IAM, S3, RDS, Kinesis, CloudWatch, boto3, "
            "Pandas, Neo4j, JWT, bcrypt, AES-256, encryption, PII, POPIA, FIC, "
            "FAIS, SMTP SSL, ReportLab, multi-tenant, rate limiting, "
            "OpenTelemetry, Docker, Docker Compose, Railway, CI/CD, pytest, "
            "MITRE ATT&amp;CK, alert correlation, data pipelines, ETL, streaming, "
            "data quality.",
            styles["body"],
        )
    )

    doc.build(story)
    return OUT_PATH


if __name__ == "__main__":
    path = build()
    size_kb = path.stat().st_size / 1024
    print(f"Wrote {path} ({size_kb:.1f} KB)")
