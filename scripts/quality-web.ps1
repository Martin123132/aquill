$ErrorActionPreference = "Stop"

. "D:\revenge-tour\transcriber\scripts\dev-env.ps1"

$WebRoot = "D:\revenge-tour\transcriber\web"
$NodeModules = Join-Path $WebRoot "node_modules"

if (-not (Test-Path $NodeModules)) {
  throw "Web dependencies not found. Run D:\revenge-tour\transcriber\scripts\setup-web.ps1 first."
}

Get-Command npm.cmd -ErrorAction Stop | Out-Null

Write-Host ""
Write-Host "Web quality check"
Write-Host "  Project: D:\revenge-tour\transcriber"
Write-Host "  Web:     $WebRoot"
Write-Host ""

Push-Location $WebRoot
try {
  npm.cmd run build
  if ($LASTEXITCODE -ne 0) {
    throw "Web build failed with exit code $LASTEXITCODE."
  }
}
finally {
  Pop-Location
}

Write-Host ""
Write-Host "Web quality check passed."
