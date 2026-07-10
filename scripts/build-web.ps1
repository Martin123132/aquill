$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "dev-env.ps1")

$WebRoot = Join-Path $env:TRANSCRIBER_ROOT "web"
$NodeModules = Join-Path $WebRoot "node_modules"

if (-not (Test-Path $NodeModules)) {
  throw "Web dependencies not found. Run $env:TRANSCRIBER_ROOT\scripts\setup-web.ps1 first."
}

Get-Command npm.cmd -ErrorAction Stop | Out-Null

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
