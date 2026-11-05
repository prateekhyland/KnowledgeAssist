# Apply schema updates for mixed public/private retrieval support.
# Uses the app's own idempotent schema initializer (works for fresh + existing DBs).

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$python = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Python virtual environment not found at $python. Run scripts/setup.ps1 first."
}

Write-Host "Applying schema migration via app.db.ensure_schema()..." -ForegroundColor Cyan
& $python -c "from app import db; db.ensure_schema(); print('Schema migration complete.')"

Write-Host "Done." -ForegroundColor Green
