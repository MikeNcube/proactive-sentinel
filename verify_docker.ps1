Write-Host "=== Proactive Sentinel Docker Verification ===" -ForegroundColor Cyan

# Health check
Write-Host "`n[1] Health check..."
$health = curl.exe -s http://localhost:5001/api/health | ConvertFrom-Json
Write-Host "Status: $($health.status)" -ForegroundColor Green

# Login
Write-Host "`n[2] Login test..."
$loginBody = '{"email":"demo@example.com","password":"YOUR_PASSWORD_HERE"}'
$login = curl.exe -s -X POST http://localhost:5001/api/auth/login `
    -H "Content-Type: application/json" -d $loginBody | ConvertFrom-Json
$token = $login.access_token
if ($token) {
    Write-Host "Login OK - token received" -ForegroundColor Green
} else {
    Write-Host "Login FAILED: $login" -ForegroundColor Red
    exit 1
}

# Alerts
Write-Host "`n[3] Alerts endpoint..."
$alerts = curl.exe -s http://localhost:5001/api/alerts `
    -H "Authorization: Bearer $token" | ConvertFrom-Json
Write-Host "Alerts response received" -ForegroundColor Green

# Rate limit
Write-Host "`n[4] Rate limit test (6 rapid requests)..."
1..6 | ForEach-Object {
    $r = curl.exe -s -o NUL -w "%{http_code}" `
        -X POST http://localhost:5001/api/auth/login `
        -H "Content-Type: application/json" -d $loginBody
    Write-Host "  Attempt $_ : HTTP $r"
}

Write-Host "`n=== Verification Complete ===" -ForegroundColor Cyan

