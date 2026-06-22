$ErrorActionPreference = "Stop"

. "D:\revenge-tour\transcriber\scripts\dev-env.ps1"

$VenvPython = "D:\revenge-tour\transcriber\.venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
  throw "Virtual environment not found. Run D:\revenge-tour\transcriber\scripts\setup.ps1 first."
}

& $VenvPython -m revenge_transcriber.server @args
