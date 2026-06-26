param(
  [switch]$IncludeWebSmoke,
  [switch]$IncludeArchiveSmoke,
  [string]$WebBase = "http://127.0.0.1:5190",
  [string]$ApiBase = "http://127.0.0.1:8091",
  [string]$SourceJobId = ""
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "dev-env.ps1")

$ProjectRoot = $env:TRANSCRIBER_ROOT
$BackendQuality = Join-Path $ProjectRoot "scripts\quality-backend.ps1"
$WebQuality = Join-Path $ProjectRoot "scripts\quality-web.ps1"
$WebSmoke = Join-Path $ProjectRoot "scripts\smoke-web-ui.ps1"
$ArchiveSmoke = Join-Path $ProjectRoot "scripts\smoke-archive-roundtrip.ps1"
$TotalSteps = 2
if ($IncludeWebSmoke) { $TotalSteps += 1 }
if ($IncludeArchiveSmoke) { $TotalSteps += 1 }

Write-Host ""
Write-Host "Full local quality check"
Write-Host "  Project: $ProjectRoot"
Write-Host "  Web smoke: $($IncludeWebSmoke.IsPresent)"
Write-Host "  Archive smoke: $($IncludeArchiveSmoke.IsPresent)"
Write-Host ""

Write-Host "1/$TotalSteps Backend quality..."
& $BackendQuality

Write-Host ""
Write-Host "2/$TotalSteps Web quality..."
& $WebQuality

$Step = 3
if ($IncludeWebSmoke) {
  Write-Host ""
  Write-Host "$Step/$TotalSteps Web UI smoke..."
  & $WebSmoke -WebBase $WebBase -ApiBase $ApiBase
  $Step += 1
}
else {
  Write-Host ""
  Write-Host "Web UI smoke skipped. To include it, start API and web servers, then run:"
  Write-Host "  $ProjectRoot\scripts\quality-all.ps1 -IncludeWebSmoke"
}

if ($IncludeArchiveSmoke) {
  Write-Host ""
  Write-Host "$Step/$TotalSteps Archive smoke..."
  if ($SourceJobId) {
    & $ArchiveSmoke -ApiBase $ApiBase -SourceJobId $SourceJobId
  }
  else {
    & $ArchiveSmoke -ApiBase $ApiBase
  }
}
else {
  Write-Host ""
  Write-Host "Archive smoke skipped. To include it, start the API with a completed job, then run:"
  Write-Host "  $ProjectRoot\scripts\quality-all.ps1 -IncludeArchiveSmoke"
}

Write-Host ""
Write-Host "Full local quality check passed."
