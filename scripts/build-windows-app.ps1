param(
  [switch]$SkipWebBuild,
  [switch]$SkipPortableZip
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "dev-env.ps1")

$ProjectRoot = $env:TRANSCRIBER_ROOT
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$SpecPath = Join-Path $ProjectRoot "installer\aquill.spec"
$BuildRoot = Join-Path $ProjectRoot "app\build\windows"
$DistRoot = Join-Path $ProjectRoot "app\dist\windows"
$AppOutput = Join-Path $DistRoot "Aquill"
$Executable = Join-Path $AppOutput "Aquill.exe"
$ReleaseRoot = Join-Path $ProjectRoot "release"
$WebIndex = Join-Path $ProjectRoot "web\dist\index.html"

function Assert-GeneratedProjectPath {
  param([string]$Path)

  $Resolved = [System.IO.Path]::GetFullPath($Path)
  $ProjectPrefix = $ProjectRoot.TrimEnd("\") + "\"
  if (-not $Resolved.StartsWith($ProjectPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to modify generated path outside the D-drive project: $Resolved"
  }
  return $Resolved
}

function Remove-GeneratedPath {
  param([string]$Path)

  $Resolved = Assert-GeneratedProjectPath $Path
  if (Test-Path -LiteralPath $Resolved) {
    Remove-Item -LiteralPath $Resolved -Recurse -Force
  }
}

if (-not (Test-Path -LiteralPath $Python)) {
  throw "Virtual environment not found. Run $ProjectRoot\scripts\setup.ps1 first."
}

& $Python -c "import PyInstaller, webview" 2>$null
if ($LASTEXITCODE -ne 0) {
  throw "Packaging dependencies are missing. Run $ProjectRoot\scripts\setup-packaging.ps1 first."
}

if (-not $SkipWebBuild) {
  & (Join-Path $ProjectRoot "scripts\build-web.ps1")
}
if (-not (Test-Path -LiteralPath $WebIndex)) {
  throw "Compiled web interface not found: $WebIndex"
}

$Version = (& $Python -c "from revenge_transcriber import __version__; print(__version__)").Trim()
if (-not $Version) {
  throw "Could not determine the Aquill version."
}

Remove-GeneratedPath $BuildRoot
Remove-GeneratedPath $DistRoot
New-Item -ItemType Directory -Force -Path $BuildRoot, $DistRoot, $ReleaseRoot | Out-Null
$env:PYINSTALLER_CONFIG_DIR = Join-Path $ProjectRoot "cache\pyinstaller"
New-Item -ItemType Directory -Force -Path $env:PYINSTALLER_CONFIG_DIR | Out-Null

Write-Host "Building Aquill $Version portable Windows application..."
& $Python -m PyInstaller --noconfirm --clean --workpath $BuildRoot --distpath $DistRoot $SpecPath
if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller build failed with exit code $LASTEXITCODE."
}
if (-not (Test-Path -LiteralPath $Executable)) {
  throw "Packaged executable was not created: $Executable"
}

$Artifacts = @()
if (-not $SkipPortableZip) {
  $PortableZip = Join-Path $ReleaseRoot "Aquill-$Version-windows-x64-portable.zip"
  Remove-GeneratedPath $PortableZip
  Compress-Archive -LiteralPath $AppOutput -DestinationPath $PortableZip -CompressionLevel Optimal
  $PortableFile = Get-Item -LiteralPath $PortableZip
  $Artifacts += [ordered]@{
    kind = "portable"
    file = $PortableFile.Name
    sha256 = (Get-FileHash -LiteralPath $PortableZip -Algorithm SHA256).Hash.ToLowerInvariant()
    bytes = $PortableFile.Length
  }
}

$ManifestPath = Join-Path $ReleaseRoot "aquill-release.json"
$Manifest = [ordered]@{
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
  artifacts = $Artifacts
}
$Manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $ManifestPath -Encoding UTF8

Write-Host "Portable application: $AppOutput"
Write-Host "Release metadata:     $ManifestPath"
