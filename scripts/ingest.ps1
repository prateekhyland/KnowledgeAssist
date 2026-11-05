# Crawl + parse + embed + index the docs defined in sources.yaml.
# Optional: pass a knowledge-base id to index just one, e.g. .\ingest.ps1 default

param([string]$Kb)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$python = ".\.venv\Scripts\python.exe"
if ($Kb) {
    & $python -m ingest.index --kb $Kb
} else {
    & $python -m ingest.index
}
