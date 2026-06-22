$ErrorActionPreference = "Stop"

. "D:\revenge-tour\transcriber\scripts\dev-env.ps1"

$ProjectRoot = "D:\revenge-tour\transcriber"
$AppSource = Join-Path $ProjectRoot "app\src\revenge_transcriber"
$AppTests = Join-Path $ProjectRoot "app\tests"
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
  throw "Virtual environment not found. Run D:\revenge-tour\transcriber\scripts\setup.ps1 first."
}

Write-Host ""
Write-Host "Backend quality check"
Write-Host "  Project: $ProjectRoot"
Write-Host "  Python:  $VenvPython"
Write-Host ""

Write-Host "1/2 Compiling backend package and tests..."
& $VenvPython -m compileall $AppSource $AppTests
if ($LASTEXITCODE -ne 0) {
  throw "Backend compile check failed with exit code $LASTEXITCODE."
}

Write-Host ""
Write-Host "2/2 Running backend unittest suite..."
& $VenvPython -m unittest discover -s $AppTests -v
if ($LASTEXITCODE -ne 0) {
  throw "Backend unittest suite failed with exit code $LASTEXITCODE."
}

Write-Host ""
Write-Host "Backend quality check passed."
