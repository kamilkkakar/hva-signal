param(
  [Parameter(Mandatory = $true)][string]$WebPublicUrl,
  [Parameter(Mandatory = $true)][string]$ApiPublicUrl
)

# GET-only public (or local) deploy check. Never POST /v1/heatmap or analysis jobs.
$ErrorActionPreference = "Stop"
$web = $WebPublicUrl.TrimEnd("/")
$api = $ApiPublicUrl.TrimEnd("/")

function Get-Json([string]$Url, [string]$Needle) {
  $body = curl.exe -sfS --max-time 20 $Url
  if ($LASTEXITCODE -ne 0) { throw "GET $Url failed" }
  if ($body -notmatch [regex]::Escape($Needle) -and $body -notmatch $Needle) {
    throw "$Url missing $Needle : $body"
  }
  Write-Output "ok $Url -> $body"
  return $body
}

Get-Json "$api/health" '"status":"ok"' | Out-Null
$ready = Get-Json "$api/ready" '"status":"ready"'
if ($ready -notmatch '"data_mode":"replay"') { throw "API /ready data_mode is not replay: $ready" }
Get-Json "$web/health" '"status":"ok"' | Out-Null
$webReady = Get-Json "$web/ready" '"status":"ready"'
if ($webReady -notmatch '"data_mode":"replay"') { throw "WEB /ready data_mode is not replay: $webReady" }

$jobUrl = "$web/api/v1/analysis/jobs/m0-probe"
$job = curl.exe -sfS --max-time 20 $jobUrl
if ($LASTEXITCODE -ne 0) { throw "GET $jobUrl failed" }
if ($job -notmatch '"status":"unknown_job"') { throw "frontend->API job probe: $job" }
Write-Output "ok $jobUrl -> $job"

$html = curl.exe -sfS --max-time 20 $web/
if ($LASTEXITCODE -ne 0) { throw "GET $web/ failed" }
if ($html -notmatch "(?i)<html") { throw "frontend root is not HTML" }

Write-Output "verify-public-deploy ok (GET /health /ready /api/v1/analysis/jobs/m0-probe only; zero heatmap POSTs)"
