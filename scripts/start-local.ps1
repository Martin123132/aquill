param(
  [string]$HostName = "127.0.0.1",
  [int]$Port = 5190,
  [switch]$NoBrowser,
  [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "dev-env.ps1")

$ProjectRoot = $env:TRANSCRIBER_ROOT
$TmpRoot = Join-Path $ProjectRoot "tmp"
$PidFile = Join-Path $TmpRoot "local-server-pids.json"
$StopScript = Join-Path $ProjectRoot "scripts\stop-local.ps1"
$BuildScript = Join-Path $ProjectRoot "scripts\build-web.ps1"
$AppUrl = "http://$HostName`:$Port"

function Wait-HttpOk {
  param(
    [string]$Uri,
    [int]$Seconds = 60
  )

  $Deadline = (Get-Date).AddSeconds($Seconds)
  do {
    try {
      Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec 3 | Out-Null
      return
    }
    catch {
      Start-Sleep -Milliseconds 700
    }
  } while ((Get-Date) -lt $Deadline)

  throw "Timed out waiting for $Uri"
}

& $StopScript -ApiPort 8091 -WebPort $Port -Quiet

$Connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($Connection) {
  throw "Required local port $Port is already in use by PID $($Connection.OwningProcess)."
}

if (-not $SkipBuild) {
  Write-Output "Building Aquill's local interface..."
  & $BuildScript
}

$WebIndex = Join-Path $ProjectRoot "web\dist\index.html"
if (-not (Test-Path -LiteralPath $WebIndex)) {
  throw "Built web interface not found. Run $BuildScript first."
}

$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$ApiOut = Join-Path $TmpRoot "local-app-$Stamp.out.log"
$ApiErr = Join-Path $TmpRoot "local-app-$Stamp.err.log"
$AppProcess = $null

try {
  $AppProcess = Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    (Join-Path $ProjectRoot "scripts\serve-api.ps1"),
    "--host",
    $HostName,
    "--port",
    [string]$Port
  ) -WorkingDirectory $ProjectRoot -WindowStyle Hidden -RedirectStandardOutput $ApiOut -RedirectStandardError $ApiErr -PassThru

  $State = [pscustomobject]@{
    mode = "single-process"
    project_root = $ProjectRoot
    started_at = (Get-Date).ToString("o")
    api_url = $AppUrl
    web_url = $AppUrl
    logs = [pscustomobject]@{
      app_stdout = $ApiOut
      app_stderr = $ApiErr
    }
    processes = @(
      [pscustomobject]@{ name = "app-wrapper"; id = $AppProcess.Id }
    )
  }
  $State | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $PidFile -Encoding UTF8

  Wait-HttpOk -Uri "$AppUrl/api/health"
  Wait-HttpOk -Uri "$AppUrl/"
}
catch {
  & $StopScript -ApiPort 8091 -WebPort $Port -Quiet
  throw
}

Write-Output ""
Write-Output "Aquill is running locally in one process."
Write-Output "  App: $AppUrl"
Write-Output "  Logs: $ApiOut"
Write-Output "        $ApiErr"
Write-Output ""
Write-Output "Stop with:"
Write-Output "  $ProjectRoot\scripts\stop-local.ps1"

if (-not $NoBrowser) {
  Start-Process -FilePath $AppUrl | Out-Null
}
