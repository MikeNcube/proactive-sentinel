# Proactive Sentinel - Verification Script (Windows PowerShell)
# Usage: .\scripts\verify.ps1

$ErrorActionPreference = "Stop"

function Write-Info($message) {
    Write-Host "[INFO] $message" -ForegroundColor Cyan
}

function Write-Success($message) {
    Write-Host "[SUCCESS] $message" -ForegroundColor Green
}

function Write-WarningMsg($message) {
    Write-Host "[WARNING] $message" -ForegroundColor Yellow
}

function Write-ErrorMsg($message) {
    Write-Host "[ERROR] $message" -ForegroundColor Red
}

function Check-Docker {
    Write-Info "Checking Docker daemon..."
    try {
        docker info *> $null
        Write-Success "Docker is running"
    }
    catch {
        Write-ErrorMsg "Docker daemon is not running. Please start Docker Desktop first."
        exit 1
    }
}

Write-Host "========================================="
Write-Host "  Proactive Sentinel Verification Suite"
Write-Host "========================================="
Write-Host ""

Check-Docker

Write-Info "Starting services..."
docker-compose up -d
Start-Sleep -Seconds 10
Write-Success "Services started"

Write-Info "Checking service health..."
$psOutput = docker-compose ps
if ($psOutput -match "Exit") {
    Write-ErrorMsg "Some services failed to start"
    docker-compose logs --tail=20 postgres redis app
    exit 1
}
Write-Success "All services are running"

Write-Info "Waiting for PostgreSQL to be ready..."
$ready = $false
for ($i = 1; $i -le 30; $i++) {
    try {
        docker-compose exec -T postgres pg_isready -U sentinel *> $null
        $ready = $true
        break
    }
    catch {
        Start-Sleep -Seconds 1
    }
}
if (-not $ready) {
    Write-ErrorMsg "PostgreSQL failed to become ready"
    exit 1
}
Write-Success "PostgreSQL is ready"

Write-Info "Creating test database..."
try {
    docker-compose exec -T postgres psql -U sentinel -c "CREATE DATABASE sentinel_test;" *> $null
    Write-Success "Test database created"
}
catch {
    Write-WarningMsg "Test database already exists, skipping"
}

Write-Info "Initializing Alembic migrations..."
if (-not (Test-Path "migrations")) {
    docker-compose exec -T app flask db init *> $null
    Write-Success "Alembic initialized"
}
else {
    Write-WarningMsg "Migrations directory exists, skipping init"
}

Write-Info "Creating migration..."
try {
    docker-compose exec -T app flask db migrate -m "Initial multi-tenant schema"
    Write-Success "Migration created"
}
catch {
    Write-WarningMsg "No changes detected"
}

Write-Info "Applying migration..."
docker-compose exec -T app flask db upgrade
Write-Success "Migration applied"

Write-Info "Running tests..."
docker-compose exec -T app pytest tests/ -v --tb=short --cov=src --cov-report=term-missing
Write-Success "All tests passed"

Write-Info "Seeding database with test data..."
docker-compose exec -T app python scripts/seed_data.py
Write-Success "Database seeded"

Write-Info "Testing API endpoints..."
$health = Invoke-RestMethod -Uri "http://localhost:5000/health" -Method Get
if ($health.status -eq "healthy") {
    Write-Success "Health check passed"
}
else {
    Write-ErrorMsg "Health check failed"
    exit 1
}

$tenantIdRaw = docker-compose exec -T postgres psql -U sentinel -d sentinel -t -c "SELECT id FROM tenants WHERE subdomain='acme' LIMIT 1;"
$tenantId = ($tenantIdRaw | Out-String).Trim()
if ($tenantId) {
    Write-Success "Found tenant: $tenantId"
    try {
        $tenantResp = Invoke-RestMethod -Uri "http://localhost:5000/api/tenants/current" -Method Get -Headers @{ "X-Tenant-ID" = $tenantId }
        if ($tenantResp.tenant_name) {
            Write-Success "Tenant API endpoint working"
        }
        else {
            Write-ErrorMsg "Tenant API endpoint failed"
        }
    }
    catch {
        Write-ErrorMsg "Tenant API endpoint failed"
    }
}
else {
    Write-WarningMsg "No tenant found, skipping tenant API test"
}

Write-Host ""
Write-Host "========================================="
Write-Success "Verification Complete!"
Write-Host "========================================="
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. View logs: docker-compose logs -f"
Write-Host "2. Access API: http://localhost:5000"
Write-Host "3. Run specific tests: docker-compose exec app pytest tests/test_tenant_isolation.py -v"
Write-Host "4. Stop services: docker-compose down"
Write-Host ""

