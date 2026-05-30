Write-Host "ðŸš€ Starting Proactive Sentinel Dashboard..." -ForegroundColor Cyan

cd C:\Users\gpcal\proactive-sentinel

# Load all environment variables from .env
Write-Host "Loading environment variables from .env..." -ForegroundColor Yellow
Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
        $key = $matches[1].Trim()
        $value = $matches[2].Trim()
        [Environment]::SetEnvironmentVariable($key, $value, "Process")
        Write-Host "  Loaded: $key" -ForegroundColor Green
    }
}

# Set PYTHONPATH
$env:PYTHONPATH = "."

# Verify critical variables
if (-not $env:DASHBOARD_SECRET_KEY) {
    Write-Host "âš ï¸  DASHBOARD_SECRET_KEY not found in .env, generating temporary key..." -ForegroundColor Yellow
    $env:DASHBOARD_SECRET_KEY = python -c "import secrets; print(secrets.token_hex(32))"
}

Write-Host "âœ… Environment ready!" -ForegroundColor Green
Write-Host "ðŸŒ Starting dashboard at http://localhost:5000..." -ForegroundColor Cyan

# Start the dashboard
python dashboard/flask_dashboard.py


