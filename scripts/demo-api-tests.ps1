# Demo API test pack for chat + codegen (including encrypted private-context behavior).
# Usage examples:
#   .\scripts\demo-api-tests.ps1
#   .\scripts\demo-api-tests.ps1 -BaseUrl http://localhost:8000 -KbId default

param(
    [string]$BaseUrl = "http://localhost:8000",
    [string]$KbId = "",
    [string]$ApiSet = "",
    [string]$ChatQuestion = "What authentication methods are supported?",
    [string]$CodegenQuestion = "Generate a Python integration snippet using these APIs."
)

$ErrorActionPreference = "Stop"

function New-PublicKeyPem {
    try {
        $rsa = [System.Security.Cryptography.RSA]::Create(2048)
        if ($rsa -and ($rsa.PSObject.Methods.Name -contains 'ExportSubjectPublicKeyInfo')) {
            $bytes = $rsa.ExportSubjectPublicKeyInfo()
            $b64 = [Convert]::ToBase64String($bytes)
            $lines = for ($i = 0; $i -lt $b64.Length; $i += 64) {
                $b64.Substring($i, [Math]::Min(64, $b64.Length - $i))
            }
            return @("-----BEGIN PUBLIC KEY-----", $lines, "-----END PUBLIC KEY-----") -join "`n"
        }
    } catch {
        # fall through to Python fallback
    }

    $python = ".\.venv\Scripts\python.exe"
    if (-not (Test-Path $python)) {
        $python = "py"
    }

    $pyCode = "from cryptography.hazmat.primitives.asymmetric import rsa; from cryptography.hazmat.primitives import serialization; k=rsa.generate_private_key(public_exponent=65537,key_size=2048); pub=k.public_key().public_bytes(encoding=serialization.Encoding.PEM,format=serialization.PublicFormat.SubjectPublicKeyInfo); print(pub.decode('utf-8'))"
    if ($python -eq "py") {
        return (& py -3 -c $pyCode)
    }
    return (& $python -c $pyCode)
}

function Invoke-ApiJson {
    param(
        [string]$Method,
        [string]$Url,
        [hashtable]$Body
    )

    if ($Body) {
        $json = $Body | ConvertTo-Json -Depth 8
        return Invoke-RestMethod -Method $Method -Uri $Url -ContentType "application/json" -Body $json
    }
    return Invoke-RestMethod -Method $Method -Uri $Url
}

Write-Host "== Health check ==" -ForegroundColor Cyan
$health = Invoke-ApiJson -Method GET -Url "$BaseUrl/health"
$health | ConvertTo-Json -Depth 8

Write-Host "`n== Chat test ==" -ForegroundColor Cyan
$chatReq = @{ question = $ChatQuestion }
if ($KbId) { $chatReq.kb_id = $KbId }
if ($ApiSet) { $chatReq.api_set = $ApiSet }
$chatResp = Invoke-ApiJson -Method POST -Url "$BaseUrl/chat" -Body $chatReq
$chatResp | ConvertTo-Json -Depth 8

Write-Host "`n== Codegen test (with recipient key) ==" -ForegroundColor Cyan
$publicKeyPem = New-PublicKeyPem
$codeReq = @{ question = $CodegenQuestion; recipient_public_key = ($publicKeyPem -join "`n") }
if ($KbId) { $codeReq.kb_id = $KbId }
if ($ApiSet) { $codeReq.api_set = $ApiSet }
$codeResp = Invoke-ApiJson -Method POST -Url "$BaseUrl/codegen" -Body $codeReq
$codeResp | ConvertTo-Json -Depth 12

if ($codeResp.private_context -eq $true) {
    if ($codeResp.ciphertext) {
        Write-Host "PASS: Private-context codegen returned encrypted payload." -ForegroundColor Green
    } else {
        Write-Host "FAIL: Private-context response did not include ciphertext." -ForegroundColor Red
        exit 1
    }
} else {
    if ($codeResp.code) {
        Write-Host "PASS: Public-context codegen returned plaintext code." -ForegroundColor Green
    } else {
        Write-Host "WARN: No code field present; check model/retrieval output." -ForegroundColor Yellow
    }
}

Write-Host "`nDemo API tests complete." -ForegroundColor Green
