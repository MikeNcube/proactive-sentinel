-- init.sql
-- Runs on first PostgreSQL container startup (docker-compose).
--
-- Historical note: this file used to create a role named ``app_user`` with
-- the hardcoded password ``app_password`` and ``GRANT ALL PRIVILEGES``. That
-- default credential has been removed; the application connects as the
-- ``sentinel`` role created by the postgres image's POSTGRES_USER /
-- POSTGRES_PASSWORD, which are injected from the POSTGRES_PASSWORD env var
-- (see docker-compose.yml and .env.example). If you need an additional
-- read-only or reporting role, create it explicitly with a password sourced
-- from your secret manager -- never hardcode it in init.sql.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

SET timezone = 'UTC';

-- Helper function referenced by application RLS policies.
-- The authoritative RLS policies are installed by the Alembic migration
-- ``migrations/versions/b7f3c9d1a2e4_enable_row_level_security.py``.
CREATE OR REPLACE FUNCTION set_tenant_context()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM set_config(
        'app.current_tenant_id',
        current_setting('app.current_tenant_id', true),
        false
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
