-- NOTE: This file is retained for reference only.
--
-- The authoritative RLS definitions now live in the Alembic migration
-- ``migrations/versions/b7f3c9d1a2e4_enable_row_level_security.py`` and
-- must be applied via ``flask db upgrade``. Do not execute this file
-- directly against production -- it does not track revision state.
--
-- Key differences vs. the pre-migration version of this file:
--   * Policies now use NULLIF(current_setting(..., true), '')::uuid so
--     an unset GUC evaluates to NULL (and therefore blocks access)
--     instead of raising on an invalid cast.
--   * Tables are also FORCED so the table-owning application role is
--     subject to the policies (without FORCE, owners bypass RLS).
--   * Scope is currently limited to ``alerts`` and ``audit_logs``;
--     ``users``/``tenants``/``units`` remain out of scope until a
--     bypass-role is introduced for unauthenticated code paths.

ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS alerts_tenant_isolation ON alerts;
CREATE POLICY alerts_tenant_isolation ON alerts
    USING (
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    )
    WITH CHECK (
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );

ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS audit_logs_tenant_isolation ON audit_logs;
CREATE POLICY audit_logs_tenant_isolation ON audit_logs
    USING (
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    )
    WITH CHECK (
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );
