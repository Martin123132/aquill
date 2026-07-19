param(
  [switch]$SkipQuality
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "dev-env.ps1")

$ProjectRoot = $env:TRANSCRIBER_ROOT
$ExpectedProductName = "Aquill"
$ExpectedPythonPackageName = "aquill"
$ExpectedWebPackageName = "aquill-web"
$ExpectedLicense = "PolyForm Noncommercial License 1.0.0"
$ExpectedWebLicense = "SEE LICENSE IN ../LICENSE"
$CDrivePrefix = "C:" + [System.IO.Path]::DirectorySeparatorChar

function Assert-ReleaseCheck {
  param(
    [bool]$Condition,
    [string]$Message
  )

  if (-not $Condition) {
    throw $Message
  }
}

function Assert-FileContains {
  param(
    [string]$Path,
    [string]$Needle,
    [string]$Label
  )

  Assert-ReleaseCheck -Condition (Test-Path -LiteralPath $Path) -Message "$Label is missing: $Path"
  $Content = Get-Content -LiteralPath $Path -Raw
  Assert-ReleaseCheck -Condition $Content.Contains($Needle) -Message "$Label does not contain expected text: $Needle"
}

function Assert-FileNotContains {
  param(
    [string]$Path,
    [string]$Needle,
    [string]$Label
  )

  Assert-ReleaseCheck -Condition (Test-Path -LiteralPath $Path) -Message "$Label is missing: $Path"
  $Content = Get-Content -LiteralPath $Path -Raw
  Assert-ReleaseCheck -Condition (-not $Content.Contains($Needle)) -Message "$Label still contains disallowed text: $Needle"
}

function Assert-NoLiteralInFiles {
  param(
    [string[]]$Roots,
    [string]$Needle,
    [string]$Label
  )

  $Files = foreach ($Root in $Roots) {
    Get-ChildItem -LiteralPath $Root -Recurse -File
  }

  $Findings = $Files | Select-String -SimpleMatch -Pattern $Needle
  if ($Findings) {
    $First = $Findings | Select-Object -First 1
    throw "$Label found '$Needle' in $($First.Path):$($First.LineNumber)"
  }
}

function Assert-DDrivePath {
  param(
    [string]$Path,
    [string]$Label
  )

  Assert-ReleaseCheck -Condition $Path.StartsWith($ProjectRoot, [System.StringComparison]::OrdinalIgnoreCase) -Message "$Label is outside project root: $Path"
}

Write-Host ""
Write-Host "Release posture check"
Write-Host "  Project: $ProjectRoot"
Write-Host "  Quality: $(-not $SkipQuality.IsPresent)"
Write-Host ""

if (-not $SkipQuality) {
  Write-Host "1/5 Running full local quality..."
  & (Join-Path $ProjectRoot "scripts\quality-all.ps1")
}
else {
  Write-Host "1/5 Full local quality skipped by request."
}

Write-Host ""
Write-Host "2/5 Checking license files and docs..."
$LicensePath = Join-Path $ProjectRoot "LICENSE"
$CommercialUsePath = Join-Path $ProjectRoot "COMMERCIAL_USE.md"
$ContactPath = Join-Path $ProjectRoot "CONTACT.md"
$SecurityPath = Join-Path $ProjectRoot "SECURITY.md"
$ChangelogPath = Join-Path $ProjectRoot "CHANGELOG.md"
$ReadmePath = Join-Path $ProjectRoot "README.md"
$AppReadmePath = Join-Path $ProjectRoot "app\README.md"
$AppSourcePath = Join-Path $ProjectRoot "web\src\App.tsx"
$DoctorPath = Join-Path $ProjectRoot "scripts\doctor.ps1"
$BuildWebPath = Join-Path $ProjectRoot "scripts\build-web.ps1"
$StartLocalPath = Join-Path $ProjectRoot "scripts\start-local.ps1"
$StartDevPath = Join-Path $ProjectRoot "scripts\start-dev.ps1"
$StopLocalPath = Join-Path $ProjectRoot "scripts\stop-local.ps1"
$StartDesktopPath = Join-Path $ProjectRoot "scripts\start-desktop.ps1"
$PackagingQualityPath = Join-Path $ProjectRoot "scripts\quality-packaging.ps1"
$AppBuildPath = Join-Path $ProjectRoot "scripts\build-windows-app.ps1"
$InstallerBuildPath = Join-Path $ProjectRoot "scripts\build-windows-installer.ps1"
$InstallerDefinitionPath = Join-Path $ProjectRoot "installer\aquill.iss"
$StoreManifestPath = Join-Path $ProjectRoot "installer\app-store-manifest.template.json"

Assert-FileContains -Path $LicensePath -Needle $ExpectedLicense -Label "LICENSE"
Assert-FileContains -Path $LicensePath -Needle "$ExpectedProductName contributors" -Label "LICENSE"
Assert-FileContains -Path $CommercialUsePath -Needle "paid subscription" -Label "COMMERCIAL_USE.md"
Assert-FileContains -Path $CommercialUsePath -Needle $ExpectedProductName -Label "COMMERCIAL_USE.md"
Assert-FileContains -Path $CommercialUsePath -Needle "glyn@twohandsnetwork.co.uk" -Label "COMMERCIAL_USE.md"
Assert-FileContains -Path $ContactPath -Needle "glyn@twohandsnetwork.co.uk" -Label "CONTACT.md"
Assert-FileContains -Path $SecurityPath -Needle "glyn@twohandsnetwork.co.uk" -Label "SECURITY.md"
Assert-FileContains -Path $SecurityPath -Needle "local-first" -Label "SECURITY.md"
Assert-FileContains -Path $ChangelogPath -Needle $ExpectedLicense -Label "CHANGELOG.md"
Assert-FileContains -Path $ChangelogPath -Needle "scripts\release-check.ps1" -Label "CHANGELOG.md"
Assert-FileContains -Path $ChangelogPath -Needle "scripts\doctor.ps1" -Label "CHANGELOG.md"
Assert-FileContains -Path $ChangelogPath -Needle "scripts\start-local.ps1" -Label "CHANGELOG.md"
Assert-FileContains -Path $ChangelogPath -Needle "scripts\stop-local.ps1" -Label "CHANGELOG.md"
Assert-FileContains -Path $ChangelogPath -Needle $ExpectedProductName -Label "CHANGELOG.md"
Assert-FileContains -Path $ReadmePath -Needle "# $ExpectedProductName" -Label "README.md"
Assert-FileContains -Path $ReadmePath -Needle "source-available" -Label "README.md"
Assert-FileContains -Path $ReadmePath -Needle $ExpectedLicense -Label "README.md"
Assert-FileContains -Path $ReadmePath -Needle "CONTACT.md" -Label "README.md"
Assert-FileContains -Path $ReadmePath -Needle "SECURITY.md" -Label "README.md"
Assert-FileContains -Path $ReadmePath -Needle "CHANGELOG.md" -Label "README.md"
Assert-FileContains -Path $ReadmePath -Needle "scripts\doctor.ps1" -Label "README.md"
Assert-FileContains -Path $ReadmePath -Needle "scripts\start-local.ps1" -Label "README.md"
Assert-FileContains -Path $ReadmePath -Needle "scripts\start-dev.ps1" -Label "README.md"
Assert-FileContains -Path $ReadmePath -Needle "scripts\stop-local.ps1" -Label "README.md"
Assert-FileContains -Path $AppReadmePath -Needle "# $ExpectedProductName" -Label "app README"
Assert-FileContains -Path $AppReadmePath -Needle "Source-available" -Label "app README"
Assert-FileContains -Path $AppSourcePath -Needle "<h1>$ExpectedProductName</h1>" -Label "App source"
Assert-FileContains -Path $AppSourcePath -Needle "license-panel" -Label "App source"
Assert-FileContains -Path $AppSourcePath -Needle "lyrics-preview-button" -Label "App source"
Assert-FileContains -Path $AppSourcePath -Needle "lyrics-align-button" -Label "App source"
Assert-FileContains -Path $AppSourcePath -Needle "restore-original-button" -Label "App source"
Assert-FileContains -Path $AppSourcePath -Needle "preset-song-button" -Label "App source"
Assert-FileContains -Path $AppSourcePath -Needle "transcript-editor-toolbar" -Label "App source"
Assert-FileContains -Path $AppSourcePath -Needle "Split at cursor" -Label "App source"
Assert-FileContains -Path $AppSourcePath -Needle "Replace all" -Label "App source"
Assert-FileContains -Path $AppSourcePath -Needle $ExpectedLicense -Label "App source"
Assert-FileContains -Path $AppSourcePath -Needle "Commercial hosting, resale, paid subscription use" -Label "App source"
Assert-ReleaseCheck -Condition (Test-Path -LiteralPath $StartLocalPath) -Message "start-local.ps1 is missing."
Assert-FileContains -Path $StartLocalPath -Needle 'mode = "single-process"' -Label "start-local.ps1"
Assert-ReleaseCheck -Condition (Test-Path -LiteralPath $StartDevPath) -Message "start-dev.ps1 is missing."
Assert-ReleaseCheck -Condition (Test-Path -LiteralPath $BuildWebPath) -Message "build-web.ps1 is missing."
Assert-ReleaseCheck -Condition (Test-Path -LiteralPath $StopLocalPath) -Message "stop-local.ps1 is missing."
Assert-ReleaseCheck -Condition (Test-Path -LiteralPath $DoctorPath) -Message "doctor.ps1 is missing."
Assert-ReleaseCheck -Condition (Test-Path -LiteralPath $StartDesktopPath) -Message "start-desktop.ps1 is missing."
Assert-ReleaseCheck -Condition (Test-Path -LiteralPath $PackagingQualityPath) -Message "quality-packaging.ps1 is missing."
Assert-ReleaseCheck -Condition (Test-Path -LiteralPath $AppBuildPath) -Message "build-windows-app.ps1 is missing."
Assert-ReleaseCheck -Condition (Test-Path -LiteralPath $InstallerBuildPath) -Message "build-windows-installer.ps1 is missing."
Assert-FileContains -Path $InstallerDefinitionPath -Needle "DefaultDirName=D:\Apps\Aquill" -Label "installer definition"
Assert-FileContains -Path $InstallerDefinitionPath -Needle $ExpectedLicense -Label "installer license posture"
Assert-FileContains -Path $StoreManifestPath -Needle "D:\\Aquill" -Label "app-store manifest data root"
Assert-FileContains -Path $StoreManifestPath -Needle "glyn@twohandsnetwork.co.uk" -Label "app-store manifest contact"

Write-Host "3/5 Checking package metadata..."
$PyProjectPath = Join-Path $ProjectRoot "app\pyproject.toml"
$WebPackagePath = Join-Path $ProjectRoot "web\package.json"
$WebLockPath = Join-Path $ProjectRoot "web\package-lock.json"

Assert-FileContains -Path $PyProjectPath -Needle "name = `"$ExpectedPythonPackageName`"" -Label "pyproject package name"
Assert-FileContains -Path $PyProjectPath -Needle "license = { text = `"$ExpectedLicense`" }" -Label "pyproject license"
Assert-FileNotContains -Path $PyProjectPath -Needle "AGPL" -Label "pyproject license"

$WebPackage = Get-Content -LiteralPath $WebPackagePath -Raw | ConvertFrom-Json
Assert-ReleaseCheck -Condition ($WebPackage.name -eq $ExpectedWebPackageName) -Message "web package name was '$($WebPackage.name)', expected '$ExpectedWebPackageName'."
Assert-ReleaseCheck -Condition ($WebPackage.license -eq $ExpectedWebLicense) -Message "web package license was '$($WebPackage.license)', expected '$ExpectedWebLicense'."
Assert-ReleaseCheck -Condition ($WebPackage.scripts.test -eq "vitest run") -Message "web test script is missing or unexpected."

Assert-FileContains -Path $WebLockPath -Needle "`"name`": `"$ExpectedWebPackageName`"" -Label "web package-lock root name"
Assert-FileContains -Path $WebLockPath -Needle "`"license`": `"$ExpectedWebLicense`"" -Label "web package-lock root license"

Write-Host "4/5 Checking D-drive runtime environment and source paths..."
Assert-DDrivePath -Path $env:TRANSCRIBER_ROOT -Label "TRANSCRIBER_ROOT"
Assert-DDrivePath -Path $env:TEMP -Label "TEMP"
Assert-DDrivePath -Path $env:TMP -Label "TMP"
Assert-DDrivePath -Path $env:PIP_CACHE_DIR -Label "PIP_CACHE_DIR"
Assert-DDrivePath -Path $env:HF_HOME -Label "HF_HOME"
Assert-DDrivePath -Path $env:npm_config_cache -Label "npm cache"

Assert-NoLiteralInFiles -Roots @(
  (Join-Path $ProjectRoot "scripts"),
  (Join-Path $ProjectRoot "app\src"),
  (Join-Path $ProjectRoot "web\src")
) -Needle $CDrivePrefix -Label "Executable source path audit"

Write-Host "5/5 Checking old release wording..."
Assert-FileNotContains -Path $ReadmePath -Needle "Open-source" -Label "README.md"
Assert-FileNotContains -Path $AppReadmePath -Needle "Open-source" -Label "app README"
Assert-FileNotContains -Path $ReadmePath -Needle "AGPL" -Label "README.md"
Assert-FileNotContains -Path $AppReadmePath -Needle "AGPL" -Label "app README"
Assert-FileNotContains -Path $ReadmePath -Needle "Revenge Transcriber" -Label "README.md"
Assert-FileNotContains -Path $AppReadmePath -Needle "Revenge Transcriber" -Label "app README"

Write-Host ""
Write-Host "Release posture check passed."
