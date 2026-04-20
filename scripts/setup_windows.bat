@echo off
REM Proactive Sentinel Setup Script for Windows
echo =========================================
echo Proactive Sentinel - Database Setup
echo =========================================

REM Check if Docker is running
docker info > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running. Please start Docker Desktop first.
    exit /b 1
)

REM Start services
echo Starting services...
docker-compose up -d

REM Wait for PostgreSQL
echo Waiting for PostgreSQL...
timeout /t 10 /nobreak > nul

REM Run migrations
echo Running database migrations...
docker-compose exec -T app python -m flask db upgrade

REM Create test database
echo Setting up test database...
docker-compose exec -T postgres psql -U sentinel -c "DROP DATABASE IF EXISTS sentinel_test;" 2>nul
docker-compose exec -T postgres psql -U sentinel -c "CREATE DATABASE sentinel_test;"
REM DATABASE_URL is derived from POSTGRES_PASSWORD (set in your .env).
REM No hardcoded 'dev_password' fallback -- if POSTGRES_PASSWORD is unset,
REM the migration will fail loudly.
docker-compose exec -T app bash -c "if [ -z \"$POSTGRES_PASSWORD\" ]; then echo 'POSTGRES_PASSWORD is not set' >&2; exit 1; fi; export DATABASE_URL=postgresql://sentinel:${POSTGRES_PASSWORD}@postgres:5432/sentinel_test && python -m flask db upgrade"

REM Seed database
echo Seeding database...
docker-compose exec -T app python scripts/seed_data.py

echo.
echo =========================================
echo Setup complete!
echo =========================================
echo Next steps:
echo 1. Run tests: docker-compose exec app pytest tests/ -v
echo 2. Test API: curl.exe http://localhost:5000/health
echo 3. View logs: docker-compose logs -f
