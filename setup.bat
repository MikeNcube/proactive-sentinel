@echo off
echo === Proactive Sentinel Setup ===
echo.

REM Check Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker Desktop is not running. Please start it first.
    pause
    exit /b 1
)

echo [1/4] Stopping any existing containers...
docker-compose down -v

echo [2/4] Building containers (no cache)...
docker-compose build --no-cache

echo [3/4] Starting services...
docker-compose up -d

echo [4/4] Waiting for health checks (30 seconds)...
timeout /t 30 /nobreak

echo.
echo Checking container status...
docker-compose ps

echo.
echo === Setup Complete ===
echo Dashboard: http://localhost:5001
echo API:       http://localhost:5001/api
echo.
pause
