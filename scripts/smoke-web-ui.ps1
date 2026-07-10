param(
  [string]$WebBase = "http://127.0.0.1:5190",
  [string]$ApiBase = "http://127.0.0.1:5190"
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "dev-env.ps1")

$ProjectRoot = $env:TRANSCRIBER_ROOT

function Invoke-Text {
  param([string]$Uri)

  try {
    return (Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec 10).Content
  }
  catch {
    throw "Request failed: GET $Uri. $($_.Exception.Message)"
  }
}

function Invoke-Json {
  param([string]$Uri)

  try {
    return Invoke-RestMethod -Uri $Uri -TimeoutSec 10
  }
  catch {
    throw "Request failed: GET $Uri. $($_.Exception.Message)"
  }
}

function Assert-Contains {
  param(
    [string]$Text,
    [string]$Needle,
    [string]$Label
  )

  if (-not $Text.Contains($Needle)) {
    throw "$Label did not contain expected text: $Needle"
  }
}

function Assert-DPath {
  param(
    [string]$Value,
    [string]$Label
  )

  if (-not $Value.StartsWith($ProjectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "$Label is outside the project root: $Value"
  }
}

Write-Host ""
Write-Host "Web UI smoke"
Write-Host "  Web:     $WebBase"
Write-Host "  API:     $ApiBase"
Write-Host "  Project: $ProjectRoot"
Write-Host ""

Write-Host "1/4 Checking web page shell..."
$Index = Invoke-Text -Uri "$WebBase/"
Assert-Contains -Text $Index -Needle "<title>Aquill</title>" -Label "Web index"

Write-Host "2/4 Checking compiled frontend wiring..."
$ScriptMatch = [regex]::Match($Index, '<script[^>]+src="([^"]+)"')
if (-not $ScriptMatch.Success) {
  throw "Web index did not contain a compiled script asset."
}
$ScriptPath = $ScriptMatch.Groups[1].Value
$BundleUri = "$($WebBase.TrimEnd('/'))/$($ScriptPath.TrimStart('/'))"
$AppBundle = Invoke-Text -Uri $BundleUri
Assert-Contains -Text $AppBundle -Needle "/api/system/storage" -Label "Compiled app"
Assert-Contains -Text $AppBundle -Needle "/api/jobs/import/preview" -Label "Compiled app"
Assert-Contains -Text $AppBundle -Needle "archive-import-input" -Label "Compiled app"
Assert-Contains -Text $AppBundle -Needle "archive-preview" -Label "Compiled app"
Assert-Contains -Text $AppBundle -Needle "job-export-button" -Label "Compiled app"
Assert-Contains -Text $AppBundle -Needle "job-search-input" -Label "Compiled app"
Assert-Contains -Text $AppBundle -Needle "lyrics-input" -Label "Compiled app"
Assert-Contains -Text $AppBundle -Needle "lyrics-preview-button" -Label "Compiled app"
Assert-Contains -Text $AppBundle -Needle "lyrics-align-button" -Label "Compiled app"
Assert-Contains -Text $AppBundle -Needle "restore-original-button" -Label "Compiled app"
Assert-Contains -Text $AppBundle -Needle "preset-song-button" -Label "Compiled app"
Assert-Contains -Text $AppBundle -Needle "D-drive local" -Label "Compiled app"
Assert-Contains -Text $AppBundle -Needle "license-panel" -Label "Compiled app"
Assert-Contains -Text $AppBundle -Needle "PolyForm Noncommercial License 1.0.0" -Label "Compiled app"

Write-Host "3/4 Checking API health and storage..."
$Health = Invoke-Json -Uri "$ApiBase/api/health"
if ($Health.status -ne "ok") {
  throw "API health was '$($Health.status)', expected 'ok'."
}
Assert-DPath -Value ([string]$Health.root) -Label "Health root"
Assert-DPath -Value ([string]$Health.database_path) -Label "Health database path"

$Storage = Invoke-Json -Uri "$ApiBase/api/system/storage"
foreach ($Property in $Storage.PSObject.Properties) {
  Assert-DPath -Value ([string]$Property.Value) -Label "Storage $($Property.Name)"
}

Write-Host "4/4 Checking the same-origin app reaches the API..."
$ProxyHealth = Invoke-Json -Uri "$WebBase/api/health"
if ($ProxyHealth.status -ne "ok") {
  throw "Web proxy health was '$($ProxyHealth.status)', expected 'ok'."
}
Assert-DPath -Value ([string]$ProxyHealth.root) -Label "Same-origin health root"

Write-Host ""
Write-Host "Web UI smoke passed."
