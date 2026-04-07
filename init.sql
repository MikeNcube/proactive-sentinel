-- init.sql
-- This script runs on first PostgreSQL container startup

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Set default timezone
SET timezone = 'UTC';

-- Create application role (if needed)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_user') THEN
        CREATE ROLE app_user WITH LOGIN PASSWORD 'app_password';
    END IF;
END
$$;

-- Grant privileges
GRANT CONNECT ON DATABASE sentinel TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT CREATE ON SCHEMA public TO app_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- Create function for setting tenant context
CREATE OR REPLACE FUNCTION set_tenant_context()
RETURNS TRIGGER AS $$
BEGIN
    -- This will be used by RLS policies
    PERFORM set_config('app.current_tenant_id', current_setting('app.current_tenant_id', true), false);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Note: Tables will be created by Alembic migrations
-- This script only sets up database extensions and base functions
