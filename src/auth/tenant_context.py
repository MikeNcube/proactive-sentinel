"""
Helpers for managing the PostgreSQL session-level tenant context that
backs our Row Level Security (RLS) policies.

We intentionally use ``SELECT set_config('app.current_tenant_id', :v, false)``
instead of ``SET app.current_tenant_id = :v``:

* PostgreSQL's ``SET`` utility command does **not** accept bind parameters.
  The previous implementation silently failed or raised, leaving RLS with
  a NULL tenant context -- which meant either no rows returned, or (if
  RLS was never enabled on the table) no DB-level isolation at all.
* ``set_config(..., false)`` pins the GUC for the lifetime of the pooled
  database connection, so the value survives intra-request commits that
  start a new SQLAlchemy transaction.
* Because the GUC now outlives a single transaction, every request ends
  by explicitly clearing it (see ``src/__init__.py`` teardown handler) so
  a connection returning to the pool never carries a stale tenant context
  from a prior request.

On non-PostgreSQL backends (SQLite in local tests) these helpers are
no-ops; RLS is a PostgreSQL feature and the repositories still apply a
Python-side ``tenant_id`` filter as defence in depth.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import text

from src.extensions import db

logger = logging.getLogger(__name__)

TENANT_GUC = "app.current_tenant_id"


class TenantContextError(RuntimeError):
    """Raised when the database-level tenant context cannot be established."""


def _is_postgres() -> bool:
    try:
        return db.engine.dialect.name == "postgresql"
    except Exception:  # pragma: no cover - engine not bound yet
        return False


def _normalize_tenant_id(tenant_id: Any) -> str:
    """Validate and canonicalize a tenant identifier as a UUID string.

    Rejecting anything that is not a well-formed UUID before it reaches
    PostgreSQL prevents SQL-shaped values from ever being routed through
    ``set_config`` and keeps RLS policies (which cast to ``::uuid``) from
    failing mid-query.
    """
    if tenant_id is None:
        raise TenantContextError("tenant_id is required to set tenant context")

    raw = str(tenant_id).strip()
    if not raw:
        raise TenantContextError("tenant_id is required to set tenant context")

    try:
        return str(uuid.UUID(raw))
    except (TypeError, ValueError, AttributeError) as exc:
        raise TenantContextError(f"invalid tenant_id: {tenant_id!r}") from exc


def set_tenant_context(tenant_id: Any) -> None:
    """Pin the PostgreSQL GUC used by RLS policies to ``tenant_id``.

    Raises ``TenantContextError`` if, on PostgreSQL, we cannot establish
    the context. Callers MUST propagate the failure rather than continue
    with a missing or stale tenant context.
    """
    normalized = _normalize_tenant_id(tenant_id)

    if not _is_postgres():
        return

    try:
        db.session.execute(
            text("SELECT set_config(:k, :v, false)"),
            {"k": TENANT_GUC, "v": normalized},
        )
    except Exception as exc:
        logger.exception("Failed to set PostgreSQL tenant context")
        raise TenantContextError("failed to set tenant context") from exc


def clear_tenant_context() -> None:
    """Reset the tenant GUC on the current connection.

    Called from the request teardown handler so that a pooled connection
    never carries tenant context across requests. Best-effort: if the
    session is already in an aborted state (e.g. the request raised),
    the reset is skipped because the connection will be rolled back and
    the GUC will be reset on the next BEGIN anyway.
    """
    if not _is_postgres():
        return
    try:
        db.session.execute(
            text("SELECT set_config(:k, '', false)"),
            {"k": TENANT_GUC},
        )
    except Exception:
        logger.debug("Tenant context clear skipped (session already closed?)")


def current_tenant_context() -> str | None:
    """Return the currently pinned tenant id, or ``None`` if unset.

    Useful for debugging and for the request-lifecycle fail-safe.
    """
    if not _is_postgres():
        return None
    try:
        row = db.session.execute(
            text("SELECT NULLIF(current_setting(:k, true), '')"),
            {"k": TENANT_GUC},
        ).first()
    except Exception:  # pragma: no cover - defensive
        return None
    return row[0] if row else None
