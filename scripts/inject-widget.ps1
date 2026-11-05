# Inject (or remove) the KnowledgeAssist widget <script> tag into every .html file
# under a folder. Idempotent: a marker comment prevents double-insertion.
#
# Usage:
#   .\inject-widget.ps1 -Path "C:\path\to\webapp" -WidgetUrl "http://localhost:8000"
#   .\inject-widget.ps1 -Path "C:\path\to\webapp" -KbId "jcscc"
#   .\inject-widget.ps1 -Path "C:\path\to\webapp" -Remove
#
# -KbId pins answers to one knowledge base. Only needed when the site's first URL
# segment differs from the id in sources.yaml (otherwise the widget detects it).
#
# Note: writing under C:\Program Files requires an elevated (Administrator) shell.

param(
    [Parameter(Mandatory = $true)][string]$Path,
    [string]$WidgetUrl = "http://localhost:8000",
    [string]$KbId,
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $Path)) { throw "Path not found: $Path" }

$marker = "<!-- KnowledgeAssist widget -->"
$kbAttr = if ($KbId) { " data-kb=""$KbId""" } else { "" }
$snippet = "$marker`r`n<script src=""$WidgetUrl/widget.js""$kbAttr></script>"

$files = Get-ChildItem -Path $Path -Recurse -Include *.html, *.htm -File
$changed = 0

foreach ($f in $files) {
    $content = Get-Content -Path $f.FullName -Raw -Encoding UTF8

    # Always strip any previous injection first (keeps it idempotent / updatable).
    $pattern = [regex]::Escape($marker) + "\s*<script src=""[^""]*/widget\.js""[^>]*></script>\s*"
    $content = [regex]::Replace($content, $pattern, "")

    if (-not $Remove) {
        if ($content -match "(?i)</body>") {
            $content = [regex]::Replace($content, "(?i)</body>", "$snippet`r`n</body>", 1)
        } else {
            # No </body> (rare) - append at end of file.
            $content = $content + "`r`n$snippet`r`n"
        }
    }

    Set-Content -Path $f.FullName -Value $content -Encoding UTF8 -NoNewline
    $changed++
}

$action = if ($Remove) { "Removed widget from" } else { "Injected widget into" }
Write-Host "$action $changed HTML file(s) under $Path" -ForegroundColor Green
