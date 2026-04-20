"""enable row level security for tenant isolation

Revision ID: b7f3c9d1a2e4
Revises: f1a2b3c4d5e6
Create Date: 2026-04-20 10:00:00.000000

Purpose
-------
Harden multi-tenant isolation at the database layer. Before this migration,
tenant isolation relied entirely on the application adding
``WHERE tenant_id = :x`` to every query -- any forgotten filter or SQL
built from raw strings silently leaked data across tenants.

This migration:

* Enables and **forces** Row Level Security on tenant-scoped tables that
  are only queried *after* authentication + ``require_tenant`` has pinned
  the ``app.current_tenant_id`` GUC. Those tables are ``alerts`` and
  ``audit_logs``.
* Installs USING + WITH CHECK policies that reference
  ``current_setting('app.current_tenant_id', true)`` so any query that
  runs without a pinned tenant context returns zero rows (and any INSERT
  without it fails).
* Uses ``NULLIF(..., '')::uuid`` so an unset GUC (empty string or NULL)
  does not raise on cast; it simply evaluates to NULL, which makes the
  equality check return NULL / false.

Scope decisions
---------------
* ``tenants``, ``users`` and ``units`` are queried in unauthenticated code
  paths (login, tenant lookup by slug, unit token lookup). Enabling RLS on
  them here would break those flows until we introduce a per-path bypass
  role. They are intentionally **out of scope** for this PR and will be
  added in a follow-up together with the bypass-role wiring.
* We use ``FORCE ROW LEVEL SECURITY`` so that even the table owner
  (typically the application role) is subject to the policies. Without
  FORCE, the owner implicitly bypasses RLS and we get no protection.

This migration is idempotent and reversible.
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "b7f3c9d1a2e4"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


RLS_TABLES = ("alerts", "audit_logs")


def _policy_name(table: str) -> str:
    return f"{table}_tenant_isolation"


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        # SQLite / other dialects used in local tests don't support RLS.
        # The application-level tenant filter in BaseRepository still
        # applies, so tests continue to work as before.
        return

    for table in RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")

        # Drop any pre-existing policy with the same name so the migration
        # is safe to re-run after a partial failure.
        op.execute(
            f"DROP POLICY IF EXISTS {_policy_name(table)} ON {table};"
        )
        op.execute(
            f"""
            CREATE POLICY {_policy_name(table)} ON {table}
                USING (
                    tenant_id = NULLIF(
                        current_setting('app.current_tenant_id', true),
                        ''
                    )::uuid
                )
                WITH CHECK (
                    tenant_id = NULLIF(
                        current_setting('app.current_tenant_id', true),
                        ''
                    )::uuid
                );
            """
        )


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for table in RLS_TABLES:
        op.execute(
            f"DROP POLICY IF EXISTS {_policy_name(table)} ON {table};"
        )
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
