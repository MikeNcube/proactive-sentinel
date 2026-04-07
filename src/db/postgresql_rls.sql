-- Enable RLS on all tables
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Create policy for users table
CREATE POLICY user_tenant_isolation ON users
    USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);

-- Create policy for alerts table
CREATE POLICY alert_tenant_isolation ON alerts
    USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);

-- Create policy for audit_logs
CREATE POLICY audit_log_tenant_isolation ON audit_logs
    USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);

-- Function to automatically set tenant_id on insert
CREATE OR REPLACE FUNCTION set_tenant_id()
RETURNS TRIGGER AS $$
BEGIN
    NEW.tenant_id = current_setting('app.current_tenant_id', true)::UUID;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for alerts
CREATE TRIGGER set_alert_tenant_id
    BEFORE INSERT ON alerts
    FOR EACH ROW
    EXECUTE FUNCTION set_tenant_id();
