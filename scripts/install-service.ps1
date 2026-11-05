# Register KnowledgeAssist as an auto-starting Windows Service using NSSM.
# Prerequisite: install NSSM (https://nssm.cc) and ensure nssm.exe is on PATH.
# Run this script from an elevated (Administrator) PowerShell.

param(
    [string]$ServiceName = "KnowledgeAssist"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

if (-not (Get-Command nssm -ErrorAction SilentlyContinue)) {
    Write-Error "nssm.exe not found on PATH. Download from https://nssm.cc and add it to PATH."
    exit 1
}

$python = Join-Path $root ".venv\Scripts\python.exe"
$args = "-m uvicorn app.main:app --host 0.0.0.0 --port 8000"

Write-Host "Installing service '$ServiceName'..."
nssm install $ServiceName $python $args
nssm set $ServiceName AppDirectory $root
nssm set $ServiceName Start SERVICE_AUTO_START
nssm set $ServiceName AppStdout (Join-Path $root "logs\service.log")
nssm set $ServiceName AppStderr (Join-Path $root "logs\service.err.log")
New-Item -ItemType Directory -Force -Path (Join-Path $root "logs") | Out-Null

Write-Host "Starting service..."
nssm start $ServiceName
Write-Host "Service '$ServiceName' installed and started." -ForegroundColor Green
