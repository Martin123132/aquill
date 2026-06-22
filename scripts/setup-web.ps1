$ErrorActionPreference = "Stop"

. "D:\revenge-tour\transcriber\scripts\dev-env.ps1"

$WebRoot = "D:\revenge-tour\transcriber\web"
$PackageLock = Join-Path $WebRoot "package-lock.json"

if (-not (Test-Path $PackageLock)) {
  throw "Missing package-lock.json at $PackageLock."
}

Get-Command npm.cmd -ErrorAction Stop | Out-Null

Write-Host ""
Write-Host "Installing web dependencies"
Write-Host "  Project: D:\revenge-tour\transcriber"
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
Write-Host "  D:\revenge-tour\transcriber\scripts\serve-web.ps1"
