param(
  [switch]$IncludeArchiveSmoke,
  [string]$ApiBase = "http://127.0.0.1:8091",
  [string]$SourceJobId = ""
)

$ErrorActionPreference = "Stop"

. "D:\revenge-tour\transcriber\scripts\dev-env.ps1"

$ProjectRoot = "D:\revenge-tour\transcriber"
$BackendQuality = Join-Path $ProjectRoot "scripts\quality-backend.ps1"
$WebQuality = Join-Path $ProjectRoot "scripts\quality-web.ps1"
$ArchiveSmoke = Join-Path $ProjectRoot "scripts\smoke-archive-roundtrip.ps1"
$TotalSteps = if ($IncludeArchiveSmoke) { 3 } else { 2 }

Write-Host ""
Write-Host "Full local quality check"
Write-Host "  Project: $ProjectRoot"
Write-Host "  Archive smoke: $($IncludeArchiveSmoke.IsPresent)"
Write-Host ""

Write-Host "1/$TotalSteps Backend quality..."
& $BackendQuality

Write-Host ""
Write-Host "2/$TotalSteps Web quality..."
& $WebQuality

if ($IncludeArchiveSmoke) {
  Write-Host ""
  Write-Host "3/$TotalSteps Archive smoke..."
  if ($SourceJobId) {
    & $ArchiveSmoke -ApiBase $ApiBase -SourceJobId $SourceJobId
  }
  else {
    & $ArchiveSmoke -ApiBase $ApiBase
  }
}
else {
  Write-Host ""
  Write-Host "Archive smoke skipped. To include it, run:"
  Write-Host "  D:\revenge-tour\transcriber\scripts\quality-all.ps1 -IncludeArchiveSmoke"
}

Write-Host ""
Write-Host "Full local quality check passed."
