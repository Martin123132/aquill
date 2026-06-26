$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "dev-env.ps1")

$WebRoot = Join-Path $env:TRANSCRIBER_ROOT "web"
$PackageLock = Join-Path $WebRoot "package-lock.json"

if (-not (Test-Path $PackageLock)) {
  throw "Missing package-lock.json at $PackageLock."
}

Get-Command npm.cmd -ErrorAction Stop | Out-Null

Write-Host ""
Write-Host "Installing web dependencies"
Write-Host "  Project: $env:TRANSCRIBER_ROOT"
Write-Host "  Web:     $WebRoot"
Write-Host "  Cache:   $env:npm_config_cache"
Write-Host ""

Push-Location $WebRoot
try {
  npm.cmd ci
  if ($LASTEXITCODE -ne 0) {
    throw "Web dependency install failed with exit code $LASTEXITCODE."
  }
}
finally {
  Pop-Location
}

Write-Host ""
Write-Host "Web setup complete. Start the UI with:"
Write-Host "  $env:TRANSCRIBER_ROOT\scripts\serve-web.ps1"
