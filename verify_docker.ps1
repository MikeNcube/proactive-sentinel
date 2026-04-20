Write-Host "=== Proactive Sentinel Docker Verification ===" -ForegroundColor Cyan

# Login credentials must be supplied via env vars. This script previously
# hardcoded 'admin@zororo.co.za / Admin1234!', which leaked into git and
# became a known default credential.
if (-not $env:VERIFY_LOGIN_EMAIL -or -not $env:VERIFY_LOGIN_PASSWORD) {
    Write-Host "VERIFY_LOGIN_EMAIL and VERIFY_LOGIN_PASSWORD must be set." -ForegroundColor Red
    Write-Host "Example (PowerShell):" -ForegroundColor Yellow
    Write-Host "  `$env:VERIFY_LOGIN_EMAIL = 'admin@example.com'"
    Write-Host "  `$env:VERIFY_LOGIN_PASSWORD = '<the-password>'"
    Write-Host "  .\verify_docker.ps1"
    exit 1
}

# Health check
Write-Host "`n[1] Health check..."
$health = curl.exe -s http://localhost:5001/api/health | ConvertFrom-Json
Write-Host "Status: $($health.status)" -ForegroundColor Green

# Login
Write-Host "`n[2] Login test..."
$loginPayload = @{
    email = $env:VERIFY_LOGIN_EMAIL
    password = $env:VERIFY_LOGIN_PASSWORD
} | ConvertTo-Json -Compress
$login = curl.exe -s -X POST http://localhost:5001/api/auth/login `
    -H "Content-Type: application/json" -d $loginPayload | ConvertFrom-Json
$token = $login.access_token
if ($token) {
    Write-Host "Login OK - token received" -ForegroundColor Green
} else {
    # Do not echo $login; it may contain server diagnostic detail.
    Write-Host "Login FAILED" -ForegroundColor Red
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
        -H "Content-Type: application/json" -d $loginPayload
    Write-Host "  Attempt $_ : HTTP $r"
}

Write-Host "`n=== Verification Complete ===" -ForegroundColor Cyan
