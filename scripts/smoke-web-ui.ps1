param(
  [string]$WebBase = "http://127.0.0.1:5190",
  [string]$ApiBase = "http://127.0.0.1:8091"
)

$ErrorActionPreference = "Stop"

. "D:\revenge-tour\transcriber\scripts\dev-env.ps1"

$ProjectRoot = "D:\revenge-tour\transcriber"

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
Assert-Contains -Text $Index -Needle "<title>Revenge Transcriber</title>" -Label "Web index"

Write-Host "2/4 Checking frontend source wiring..."
$AppSource = Invoke-Text -Uri "$WebBase/src/App.tsx"
Assert-Contains -Text $AppSource -Needle "/api/system/storage" -Label "App source"
Assert-Contains -Text $AppSource -Needle "archive-import-input" -Label "App source"
Assert-Contains -Text $AppSource -Needle "job-export-button" -Label "App source"
Assert-Contains -Text $AppSource -Needle "D-drive local" -Label "App source"

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

Write-Host "4/4 Checking web proxy reaches the API..."
$ProxyHealth = Invoke-Json -Uri "$WebBase/api/health"
if ($ProxyHealth.status -ne "ok") {
  throw "Web proxy health was '$($ProxyHealth.status)', expected 'ok'."
}
Assert-DPath -Value ([string]$ProxyHealth.root) -Label "Proxy health root"

Write-Host ""
Write-Host "Web UI smoke passed."
