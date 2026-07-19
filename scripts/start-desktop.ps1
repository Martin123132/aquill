param(
  [string]$DataRoot = "D:\Aquill",
  [switch]$Debug
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "dev-env.ps1")

$ProjectRoot = $env:TRANSCRIBER_ROOT
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$WebIndex = Join-Path $ProjectRoot "web\dist\index.html"
$ResolvedDataRoot = [System.IO.Path]::GetFullPath($DataRoot)

if (-not $ResolvedDataRoot.StartsWith("D:\", [System.StringComparison]::OrdinalIgnoreCase)) {
  throw "Aquill desktop data must stay on D:. Requested root: $ResolvedDataRoot"
}
if (-not (Test-Path -LiteralPath $Python)) {
  throw "Virtual environment not found. Run $ProjectRoot\scripts\setup.ps1 first."
}
if (-not (Test-Path -LiteralPath $WebIndex)) {
  & (Join-Path $ProjectRoot "scripts\build-web.ps1")
}

& $Python -c "import webview" 2>$null
if ($LASTEXITCODE -ne 0) {
  throw "pywebview is not installed. Run $ProjectRoot\scripts\setup-packaging.ps1 first."
}

$DesktopArguments = @("-m", "revenge_transcriber.desktop", "--data-root", $ResolvedDataRoot)
if ($Debug) {
  $DesktopArguments += "--debug"
}

& $Python @DesktopArguments
if ($LASTEXITCODE -ne 0) {
  throw "Aquill desktop exited with code $LASTEXITCODE."
}
