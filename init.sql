-- =============================================================================
-- DATABASE INITIALIZATION SCRIPT FOR AI RECRUITMENT PLATFORM
-- =============================================================================
-- This script initializes the PostgreSQL database for production deployment

-- Create database if it doesn't exist (handled by Docker environment variables)
-- The database name is set via POSTGRES_DB environment variable

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Set timezone
SET timezone = 'UTC';

-- Create schemas if needed
-- CREATE SCHEMA IF NOT EXISTS recruitment;

-- Grant permissions to the application user
-- The user is created via POSTGRES_USER environment variable
GRANT ALL PRIVILEGES ON DATABASE recruitment TO recruit;

-- Create any initial tables or data here if needed
-- Note: FastAPI with SQLAlchemy will handle table creation via Alembic migrations

-- Example: Create a health check table
CREATE TABLE IF NOT EXISTS health_check (
    id SERIAL PRIMARY KEY,
    status VARCHAR(50) NOT NULL DEFAULT 'healthy',
    last_check TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Insert initial health check record
INSERT INTO health_check (status) VALUES ('healthy') ON CONFLICT DO NOTHING;

-- Create indexes for performance
-- Add any specific indexes your application needs

-- Example: If you have user-related tables, you might want these indexes
-- CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
-- CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);

-- Set up any initial configuration data
-- INSERT INTO configuration (key, value) VALUES 
--   ('app_version', '1.0.0'),
--   ('maintenance_mode', 'false')
-- ON CONFLICT (key) DO NOTHING;

-- Log the initialization
INSERT INTO health_check (status) VALUES ('initialized');

-- Grant necessary permissions for the application
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO recruit;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO recruit;

-- Set default permissions for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO recruit;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE ON SEQUENCES TO recruit;