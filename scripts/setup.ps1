$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "dev-env.ps1")

$VenvPath = Join-Path $env:TRANSCRIBER_ROOT ".venv"
$Python = Get-Command python -ErrorAction Stop

if (-not (Test-Path $VenvPath)) {
  & $Python.Source -m venv $VenvPath
}

$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -e (Join-Path $env:TRANSCRIBER_ROOT "app")

Write-Host "Setup complete. CLI available through:"
Write-Host "  $env:TRANSCRIBER_ROOT\scripts\transcribe.ps1 <input-file>"
Write-Host ""
Write-Host "For web UI dependencies, run:"
Write-Host "  $env:TRANSCRIBER_ROOT\scripts\setup-web.ps1"
