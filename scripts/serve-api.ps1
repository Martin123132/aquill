$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "dev-env.ps1")

$VenvPython = Join-Path $env:TRANSCRIBER_ROOT ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
  throw "Virtual environment not found. Run $env:TRANSCRIBER_ROOT\scripts\setup.ps1 first."
}

& $VenvPython -m revenge_transcriber.server @args
