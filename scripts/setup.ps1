$ErrorActionPreference = "Stop"

. "D:\revenge-tour\transcriber\scripts\dev-env.ps1"

$VenvPath = "D:\revenge-tour\transcriber\.venv"
$Python = Get-Command python -ErrorAction Stop

if (-not (Test-Path $VenvPath)) {
  & $Python.Source -m venv $VenvPath
}

$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -e "D:\revenge-tour\transcriber\app"

Write-Host "Setup complete. CLI available through:"
Write-Host "  D:\revenge-tour\transcriber\scripts\transcribe.ps1 <input-file>"
Write-Host ""
Write-Host "For web UI dependencies, run:"
Write-Host "  D:\revenge-tour\transcriber\scripts\setup-web.ps1"
