$ErrorActionPreference = "Stop"

. "D:\revenge-tour\transcriber\scripts\dev-env.ps1"

$WebRoot = "D:\revenge-tour\transcriber\web"
$NodeModules = Join-Path $WebRoot "node_modules"

if (-not (Test-Path $NodeModules)) {
  throw "Web dependencies not found. Run D:\revenge-tour\transcriber\scripts\setup-web.ps1 first."
}

Set-Location $WebRoot
npm.cmd run dev
