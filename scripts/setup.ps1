# KnowledgeAssist one-time setup (Windows).
# Creates a Python venv, installs dependencies, pulls the Ollama model,
# and initializes the database schema.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "== KnowledgeAssist setup ==" -ForegroundColor Cyan

# 1. Python virtual environment
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment (.venv)..."
    python -m venv .venv
}
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\pip.exe" install -r requirements.txt

# 2. .env / sources.yaml bootstrap
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example - review the settings." -ForegroundColor Yellow
}
if (-not (Test-Path "sources.yaml")) {
    Copy-Item "sources.example.yaml" "sources.yaml"
    Write-Host "Created sources.yaml from example - edit it to point at your docs." -ForegroundColor Yellow
}

# 3. Pull the LLM model in Ollama (must be installed & running)
$model = (Get-Content .env | Where-Object { $_ -match "^LLM_MODEL=" }) -replace "^LLM_MODEL=", ""
if (-not $model) { $model = "qwen2.5:7b-instruct" }
if (Get-Command ollama -ErrorAction SilentlyContinue) {
    Write-Host "Pulling Ollama model: $model"
    ollama pull $model
} else {
    Write-Host "Ollama not found on PATH. Install it from https://ollama.com and run 'ollama pull $model'." -ForegroundColor Yellow
}

# 4. Initialize DB schema (extension + tables)
Write-Host "Initializing database schema..."
& ".\.venv\Scripts\python.exe" -c "from app import db; db.ensure_schema(); print('schema ready')"

Write-Host "Setup complete. Next: edit sources.yaml, then run scripts/ingest.ps1" -ForegroundColor Green
