import logging
import os
import time
from urllib.parse import urlparse, urlunparse

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


def normalize_database_url(url: str) -> str:
    if not url:
        raise RuntimeError("DATABASE_URL is required and must point to PostgreSQL.")
    normalized = url.strip()
    if normalized.startswith("postgres://"):
        normalized = normalized.replace("postgres://", "postgresql://", 1)
    return normalized


def validate_postgresql_url(url: str) -> str:
    normalized = normalize_database_url(url)
    parsed = urlparse(normalized)
    if parsed.scheme != "postgresql":
        raise RuntimeError(
            f"DATABASE_URL must use PostgreSQL (postgresql://). Got scheme '{parsed.scheme}'."
        )
    if not parsed.hostname:
        raise RuntimeError("DATABASE_URL is malformed: hostname is missing.")
    if not parsed.path or parsed.path == "/":
        raise RuntimeError("DATABASE_URL is malformed: database name is missing.")
    return normalized


def mask_database_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.netloc:
        return "<invalid>"
    host = parsed.hostname or "<unknown-host>"
    port = f":{parsed.port}" if parsed.port else ""
    user = parsed.username or "<user>"
    db_name = parsed.path.lstrip("/") or "<db>"
    redacted_netloc = f"{user}:***@{host}{port}"
    return urlunparse((parsed.scheme, redacted_netloc, f"/{db_name}", "", "", ""))


def get_validated_database_url_from_env() -> str:
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        raise RuntimeError("DATABASE_URL is required and must point to PostgreSQL.")
    return validate_postgresql_url(raw)


def wait_for_database(url: str, timeout_seconds: int = 20, interval_seconds: int = 2) -> None:
    deadline = time.time() + timeout_seconds
    last_error = None
    while time.time() < deadline:
        try:
            engine = create_engine(url, pool_pre_ping=True)
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            logger.info("Database connectivity check passed.")
            return
        except SQLAlchemyError as exc:
            last_error = exc
            logger.warning("Database not reachable yet; retrying: %s", exc)
            time.sleep(interval_seconds)
    raise RuntimeError(
        f"Database is not reachable after {timeout_seconds} seconds."
    ) from last_error

