# Start the KnowledgeAssist API + web UI.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# Read host/port from .env (fallback to defaults).
$envHost = (Get-Content .env -ErrorAction SilentlyContinue | Where-Object { $_ -match "^APP_HOST=" }) -replace "^APP_HOST=", ""
$envPort = (Get-Content .env -ErrorAction SilentlyContinue | Where-Object { $_ -match "^APP_PORT=" }) -replace "^APP_PORT=", ""
if (-not $envHost) { $envHost = "0.0.0.0" }
if (-not $envPort) { $envPort = "8000" }

Write-Host "Starting KnowledgeAssist on http://$($envHost):$($envPort)" -ForegroundColor Green
& ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --host $envHost --port $envPort
