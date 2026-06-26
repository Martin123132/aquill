$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "dev-env.ps1")

$WebRoot = Join-Path $env:TRANSCRIBER_ROOT "web"
$NodeModules = Join-Path $WebRoot "node_modules"

if (-not (Test-Path $NodeModules)) {
  throw "Web dependencies not found. Run $env:TRANSCRIBER_ROOT\scripts\setup-web.ps1 first."
}

Set-Location $WebRoot
npm.cmd run dev
