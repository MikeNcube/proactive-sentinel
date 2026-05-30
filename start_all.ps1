# Start All Proactive Sentinel Services
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting Proactive Sentinel Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Start Docker API Backend
Write-Host "`n[1/2] Starting API Backend (Docker)..." -ForegroundColor Yellow
docker-compose up -d

# Wait for API to be ready
Write-Host "Waiting for API to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0
while ($attempt -lt $maxAttempts) {
    try {
        $response = curl.exe -s http://localhost:5001/health
        if ($response -match "healthy") {
            Write-Host "API Backend is ready!" -ForegroundColor Green
            break
        }
    } catch {
        # Still starting
    }
    $attempt++
    Start-Sleep -Seconds 1
}

# Start Dashboard
Write-Host "`n[2/2] Starting Dashboard (Flask)..." -ForegroundColor Yellow
$dashboardProcess = Start-Process -NoNewWindow -PassThru -FilePath "python" -ArgumentList "dashboard/flask_dashboard.py" -WorkingDirectory "C:\Users\gpcal\proactive-sentinel"

Start-Sleep -Seconds 3

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Services Started!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "API Backend:   http://localhost:5001"
Write-Host "Dashboard:     http://localhost:5000"
Write-Host "========================================"
Write-Host ""
Write-Host "To stop services:"
Write-Host "  docker-compose down"
Write-Host "  Then close the dashboard terminal"

