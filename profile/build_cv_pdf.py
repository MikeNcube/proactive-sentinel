"""
Build the ATS-safe PDF CV from profile/cv_ats_ai_engineer.md.

Strict ATS compliance:
  - Single column, no tables, no icons, no graphics, no colors.
  - Standard font (Helvetica, the PDF equivalent of Arial).
  - Simple paragraphs and unordered list bullets only.
  - Content is preserved from the source markdown exactly (only formatted).
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
    Spacer,
)


OUT_PATH = Path(__file__).parent / "Mike_Simbarashe_Ncube_AI_Engineer_CV.pdf"

FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
BLACK = "#000000"


def make_styles():
    base = ParagraphStyle(
        "Base",
        fontName=FONT,
        fontSize=10.5,
        leading=14,
        textColor=BLACK,
        alignment=TA_LEFT,
        spaceBefore=0,
        spaceAfter=0,
    )

    name = ParagraphStyle(
        "Name",
        parent=base,
        fontName=FONT_BOLD,
        fontSize=18,
        leading=22,
        spaceAfter=2,
    )

    title = ParagraphStyle(
        "Title",
        parent=base,
        fontSize=11.5,
        leading=15,
        spaceAfter=2,
    )

    contact = ParagraphStyle(
        "Contact",
        parent=base,
        fontSize=10.5,
        leading=14,
        spaceAfter=10,
    )

    section = ParagraphStyle(
        "Section",
        parent=base,
        fontName=FONT_BOLD,
        fontSize=12,
        leading=16,
        spaceBefore=10,
        spaceAfter=4,
    )

    subsection = ParagraphStyle(
        "Subsection",
        parent=base,
        fontName=FONT_BOLD,
        fontSize=11,
        leading=15,
        spaceBefore=6,
        spaceAfter=3,
    )

    body = ParagraphStyle(
        "Body",
        parent=base,
        fontSize=10.5,
        leading=14,
        spaceAfter=6,
    )

    bullet = ParagraphStyle(
        "Bullet",
        parent=body,
        spaceAfter=2,
        leading=13.5,
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
        [ListItem(Paragraph(t, style), leftIndent=10) for t in items],
        bulletType="bullet",
        start="\u2022",
        leftIndent=14,
        bulletFontName=FONT,
        bulletFontSize=10.5,
        bulletOffsetY=0,
        spaceBefore=0,
        spaceAfter=6,
    )


def build():
    styles = make_styles()
    doc = SimpleDocTemplate(
        str(OUT_PATH),
        pagesize=LETTER,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        title="Mike Simbarashe Ncube - AI Engineer CV",
        author="Mike Simbarashe Ncube",
        subject="Curriculum Vitae",
        creator="profile/build_cv_pdf.py",
    )

    story = []

    story.append(Paragraph("MIKE (SIMBARASHE) NCUBE", styles["name"]))
    story.append(
        Paragraph(
            "AI Engineer &mdash; Agentic AI, Applied LLM Workflows, Python Backends",
            styles["title"],
        )
    )
    story.append(
        Paragraph(
            "Email: [add] | GitHub: github.com/MikeNcube | LinkedIn: [add] | Location: [add]",
            styles["contact"],
        )
    )

    story.append(Paragraph("PROFESSIONAL SUMMARY", styles["section"]))
    story.append(
        Paragraph(
            "AI engineer building agentic AI pipelines and the Python backends that serve "
            "them. Experienced with multi-agent LLM workflows on local model runtimes, "
            "Flask/FastAPI services, multi-tenant data models, JWT authentication, "
            "AES-256 field-level encryption, PII masking, rule-based detection, and alert "
            "correlation. Comfortable with Docker-based local environments, pytest, and "
            "OpenTelemetry instrumentation.",
            styles["body"],
        )
    )

    story.append(Paragraph("CORE SKILLS", styles["section"]))
    core_skills = [
        "<b>Languages:</b> Python 3.11",
        "<b>AI / LLM:</b> Agentic multi-agent pipelines, prompt-template design, "
        "Ollama (local llama3), human-in-the-loop review loops",
        "<b>Backend:</b> Flask, FastAPI, SQLAlchemy 2.x, Alembic, Jinja2, "
        "Flask-Limiter, Flask-CORS, flask-jwt-extended",
        "<b>Data:</b> PostgreSQL, Redis (dedup cache), public-API and RSS ingestion "
        "(GitHub Search, ArXiv Atom, O&rsquo;Reilly RSS)",
        "<b>Security:</b> JWT (HS256 access + refresh), bcrypt, AES-256-GCM column "
        "encryption, regex-based PII masking (SA ID, Zim ID, passport), rate-limiting, "
        "secure response headers, tenant isolation",
        "<b>Observability:</b> OpenTelemetry (API/SDK, Flask + SQLAlchemy "
        "instrumentation, OTLP/gRPC), JSON request logging, correlation IDs",
        "<b>Tooling:</b> Docker, Docker Compose, n8n, pytest, pytest-flask, "
        "factory-boy, Makefile, gunicorn",
    ]
    story.append(bullets(core_skills, styles["bullet"]))

    story.append(Paragraph("PROJECT EXPERIENCE", styles["section"]))

    story.append(
        Paragraph(
            "Proactive Sentinel &mdash; Multi-tenant Python/Flask SOC Service (Open Source)",
            styles["subsection"],
        )
    )
    sentinel_bullets = [
        "Designed a Flask application-factory service with tenant-scoped auth, bcrypt "
        "password hashing, and JWT access + refresh tokens.",
        "Implemented AES-256-GCM column-level encryption using a SQLAlchemy "
        "TypeDecorator; applied it to user PII fields (phone, full name, address, MFA "
        "secret) with a dedicated ENCRYPTION_KEY separate from JWT secrets.",
        "Built a recursive PII masking layer for structured telemetry, covering South "
        "African national IDs, Zimbabwe IDs, and passport number patterns.",
        "Implemented rule-based detections for user file-access spikes and UX "
        "degradation (slow claims, WhatsApp frustration, HTTP 4xx/5xx, negative "
        "sentiment on social channels, Zendesk latency, CRM lead leakage).",
        "Built an alert correlation engine that deduplicates alerts via SHA-256 "
        "fingerprints in Redis and groups them into MITRE ATT&amp;CK&ndash;style attack "
        "chains using technique IDs, with a confidence score per chain.",
        "Added a per-IP and per-unit request-velocity threat detector with an "
        "auto-ban after repeated violations and a unit-compromise signal.",
        "Exposed /api/health, /api/alerts, /api/alerts/&lt;id&gt;/dismiss, /api/stats, "
        "/api/tenants/current, /api/units/*, /api/auth/*, and /api/audit/logs; added "
        "Flask-Limiter rate limiting and hardened response headers (HSTS, "
        "X-Frame-Options, X-Content-Type-Options).",
        "Instrumented the stack with OpenTelemetry (Flask + SQLAlchemy, OTLP/gRPC) "
        "and structured JSON logging with correlation IDs.",
        "Packaged the service with a non-root python:3.11-slim Docker image and a "
        "Docker Compose stack including Postgres 15 and Redis 7; added an init.sql "
        "that enables pgcrypto, uuid-ossp, and a tenant-context helper function for "
        "row-level-security policies.",
        "Wrote pytest suites covering PII masking, detection engine behaviour, "
        "tenant isolation, and API flows.",
    ]
    story.append(bullets(sentinel_bullets, styles["bullet"]))

    story.append(
        Paragraph(
            "AI-Social-Agent &mdash; Agentic Content Pipeline (Open Source)",
            styles["subsection"],
        )
    )
    social_bullets = [
        "Built a three-agent Python pipeline (Research &rarr; Strategy &rarr; Content) "
        "that turns fresh AI-ecosystem signals into platform-specific social posts.",
        "Integrated a local Ollama runtime (llama3) via HTTP for all LLM calls, "
        "keeping iteration fast and free of external API dependencies.",
        "Implemented a data-ingestion module pulling from the GitHub Search API "
        "(trending repos by topic), the ArXiv Atom feed, and an O&rsquo;Reilly AI RSS "
        "feed; persisted results as timestamped JSON for downstream agents.",
        "Designed version-controlled prompt templates per agent and per platform "
        "(LinkedIn, X, Instagram, TikTok), plus hook-writer, body-generator, and "
        "strategist sub-prompts.",
        "Built a FastAPI + Jinja2 human-in-the-loop review dashboard supporting "
        "list/filter/view, approve, reject, schedule, bulk-approve, bulk-schedule, "
        "and per-platform / per-status / per-weekday analytics.",
        "Added a weekday-gated scheduler that picks up approved-but-unscheduled "
        "posts and simulates posting to each platform.",
        "Stood up an n8n container via Docker Compose with a mounted workflows "
        "folder for future event-driven orchestration.",
    ]
    story.append(bullets(social_bullets, styles["bullet"]))

    story.append(Paragraph("EDUCATION", styles["section"]))
    story.append(
        Paragraph(
            "[Degree, Institution, Year] &mdash; keep existing real entry",
            styles["body"],
        )
    )

    story.append(Paragraph("CERTIFICATIONS", styles["section"]))
    story.append(
        Paragraph(
            "[Only keep entries that are real and verifiable]",
            styles["body"],
        )
    )

    story.append(Paragraph("ADDITIONAL INFORMATION", styles["section"]))
    story.append(
        Paragraph(
            "<b>ATS keyword coverage (evidence-backed):</b>",
            styles["body"],
        )
    )
    story.append(
        Paragraph(
            "AI Engineer &middot; Agentic AI &middot; multi-agent &middot; LLM &middot; "
            "prompt engineering &middot; Ollama &middot; Python &middot; Flask &middot; "
            "FastAPI &middot; SQLAlchemy &middot; Alembic &middot; PostgreSQL &middot; "
            "Redis &middot; JWT &middot; bcrypt &middot; AES-256 &middot; encryption "
            "&middot; PII &middot; multi-tenant &middot; rate limiting &middot; "
            "OpenTelemetry &middot; Docker &middot; Docker Compose &middot; n8n "
            "&middot; pytest &middot; MITRE ATT&amp;CK &middot; alert correlation "
            "&middot; data pipelines",
            styles["body"],
        )
    )

    doc.build(story)
    return OUT_PATH


if __name__ == "__main__":
    path = build()
    size_kb = path.stat().st_size / 1024
    print(f"Wrote {path} ({size_kb:.1f} KB)")
