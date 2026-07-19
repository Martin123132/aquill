param(
  [switch]$Upgrade
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "dev-env.ps1")

$ProjectRoot = $env:TRANSCRIBER_ROOT
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$AppRoot = Join-Path $ProjectRoot "app"

if (-not (Test-Path -LiteralPath $Python)) {
  throw "Virtual environment not found. Run $ProjectRoot\scripts\setup.ps1 first."
}

$InstallArguments = @("-m", "pip", "install")
if ($Upgrade) {
  $InstallArguments += "--upgrade"
}
$InstallArguments += @("-e", "${AppRoot}[packaging]")

Write-Host "Installing Aquill Windows packaging tools into the D-drive virtual environment..."
& $Python @InstallArguments
if ($LASTEXITCODE -ne 0) {
  throw "Packaging dependency setup failed with exit code $LASTEXITCODE."
}

& $Python -c "from importlib.metadata import version; print('PyInstaller ' + version('pyinstaller')); print('pywebview ' + version('pywebview'))"
if ($LASTEXITCODE -ne 0) {
  throw "Packaging dependencies were installed but could not be imported."
}
