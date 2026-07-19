param(
  [switch]$SkipAppBuild
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "dev-env.ps1")

$ProjectRoot = $env:TRANSCRIBER_ROOT
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$AppOutput = Join-Path $ProjectRoot "app\dist\windows\Aquill"
$Executable = Join-Path $AppOutput "Aquill.exe"
$InstallerScript = Join-Path $ProjectRoot "installer\aquill.iss"
$ReleaseRoot = Join-Path $ProjectRoot "release"
$ReleaseManifest = Join-Path $ReleaseRoot "aquill-release.json"

if (-not $SkipAppBuild) {
  & (Join-Path $ProjectRoot "scripts\build-windows-app.ps1")
}
if (-not (Test-Path -LiteralPath $Executable)) {
  throw "Portable application not found. Build it before compiling the installer."
}

$Compiler = $null
if ($env:INNO_SETUP_COMPILER -and (Test-Path -LiteralPath $env:INNO_SETUP_COMPILER)) {
  $Compiler = $env:INNO_SETUP_COMPILER
}
if (-not $Compiler) {
  $Command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
  if ($Command) {
    $Compiler = $Command.Source
  }
}
if (-not $Compiler) {
  $Candidates = @(
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
    (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
  )
  $Compiler = $Candidates | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
}
if (-not $Compiler) {
  throw "Inno Setup 6 was not found. Install JRSoftware.InnoSetup with winget, then rerun this script."
}

$Version = (& $Python -c "from revenge_transcriber import __version__; print(__version__)").Trim()
New-Item -ItemType Directory -Force -Path $ReleaseRoot | Out-Null

Write-Host "Building Aquill $Version installer with $Compiler..."
& $Compiler "/DAppVersion=$Version" "/DSourceDir=$AppOutput" "/DOutputDir=$ReleaseRoot" $InstallerScript
if ($LASTEXITCODE -ne 0) {
  throw "Inno Setup build failed with exit code $LASTEXITCODE."
}

$Installer = Join-Path $ReleaseRoot "Aquill-Setup-$Version-x64.exe"
if (-not (Test-Path -LiteralPath $Installer)) {
  throw "Installer output was not created: $Installer"
}

$Manifest = if (Test-Path -LiteralPath $ReleaseManifest) {
  Get-Content -LiteralPath $ReleaseManifest -Raw | ConvertFrom-Json
}
else {
  [pscustomobject]@{
    schemaVersion = 1
    id = "uk.co.twohandsnetwork.aquill"
    name = "Aquill"
    publisher = "Two Hands Network"
    version = $Version
    platform = "windows"
    architecture = "x64"
    license = "PolyForm Noncommercial License 1.0.0"
    dataRoot = "D:\Aquill"
    builtAtUtc = [DateTime]::UtcNow.ToString("o")
    artifacts = @()
  }
}
$ExistingArtifacts = @($Manifest.artifacts | Where-Object { $_.kind -ne "installer" })
$InstallerFile = Get-Item -LiteralPath $Installer
$InstallerArtifact = [pscustomobject]@{
  kind = "installer"
  file = $InstallerFile.Name
  sha256 = (Get-FileHash -LiteralPath $Installer -Algorithm SHA256).Hash.ToLowerInvariant()
  bytes = $InstallerFile.Length
  silentArguments = "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART"
}
$Manifest.artifacts = @($ExistingArtifacts) + $InstallerArtifact
$Manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $ReleaseManifest -Encoding UTF8

Write-Host "Installer: $Installer"
Write-Host "Release metadata: $ReleaseManifest"
