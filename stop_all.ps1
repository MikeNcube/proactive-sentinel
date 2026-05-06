# Stop All Proactive Sentinel Services
Write-Host "Stopping Proactive Sentinel Services..." -ForegroundColor Yellow

# Stop Docker containers
Write-Host "Stopping API Backend..." -ForegroundColor Yellow
docker-compose down

# Stop dashboard Python process
Write-Host "Stopping Dashboard..." -ForegroundColor Yellow
Get-Process python* | Where-Object { $_.Path -like "*dashboard*" } | Stop-Process -Force

Write-Host "All services stopped!" -ForegroundColor Green
