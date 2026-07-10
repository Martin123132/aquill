param(
  [string]$ApiHost = "127.0.0.1",
  [int]$ApiPort = 8091,
  [int]$WebPort = 5190
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "dev-env.ps1")

$ProjectRoot = $env:TRANSCRIBER_ROOT
$TmpRoot = Join-Path $ProjectRoot "tmp"
$PidFile = Join-Path $TmpRoot "local-server-pids.json"
$StopScript = Join-Path $ProjectRoot "scripts\stop-local.ps1"
$ApiUrl = "http://$ApiHost`:$ApiPort"
$WebUrl = "http://127.0.0.1:$WebPort"

if ($WebPort -ne 5190) {
  throw "The Vite development wrapper uses the fixed port 5190."
}

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

function Get-NonProjectListeners {
  $Connections = Get-NetTCPConnection -LocalPort $ApiPort, $WebPort -State Listen -ErrorAction SilentlyContinue
  $Blocked = @()

  foreach ($Connection in @($Connections)) {
    $Process = Get-CimInstance Win32_Process -Filter "ProcessId = $($Connection.OwningProcess)" -ErrorAction SilentlyContinue
    if (-not $Process -or -not $Process.CommandLine -or -not $Process.CommandLine.Contains($ProjectRoot)) {
      $Blocked += $Connection
    }
  }

  return $Blocked
}

& $StopScript -ApiPort $ApiPort -WebPort $WebPort -Quiet

$BlockedListeners = Get-NonProjectListeners
if ($BlockedListeners) {
  $BlockedSummary = $BlockedListeners | ForEach-Object { "$($_.LocalAddress):$($_.LocalPort) owned by PID $($_.OwningProcess)" }
  throw "Required local port is already in use by another process: $($BlockedSummary -join '; ')"
}

$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$ApiOut = Join-Path $TmpRoot "local-api-$Stamp.out.log"
$ApiErr = Join-Path $TmpRoot "local-api-$Stamp.err.log"
$WebOut = Join-Path $TmpRoot "local-web-$Stamp.out.log"
$WebErr = Join-Path $TmpRoot "local-web-$Stamp.err.log"

$ApiProcess = $null
$WebProcess = $null

try {
  $ApiProcess = Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    (Join-Path $ProjectRoot "scripts\serve-api.ps1"),
    "--host",
    $ApiHost,
    "--port",
    [string]$ApiPort
  ) -WorkingDirectory $ProjectRoot -WindowStyle Hidden -RedirectStandardOutput $ApiOut -RedirectStandardError $ApiErr -PassThru

  $WebProcess = Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    (Join-Path $ProjectRoot "scripts\serve-web.ps1")
  ) -WorkingDirectory $ProjectRoot -WindowStyle Hidden -RedirectStandardOutput $WebOut -RedirectStandardError $WebErr -PassThru

  $State = [pscustomobject]@{
    mode = "development"
    project_root = $ProjectRoot
    started_at = (Get-Date).ToString("o")
    api_url = $ApiUrl
    web_url = $WebUrl
    logs = [pscustomobject]@{
      api_stdout = $ApiOut
      api_stderr = $ApiErr
      web_stdout = $WebOut
      web_stderr = $WebErr
    }
    processes = @(
      [pscustomobject]@{ name = "api-wrapper"; id = $ApiProcess.Id },
      [pscustomobject]@{ name = "web-wrapper"; id = $WebProcess.Id }
    )
  }
  $State | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $PidFile -Encoding UTF8

  Wait-HttpOk -Uri "$ApiUrl/api/health"
  Wait-HttpOk -Uri "$WebUrl/"
}
catch {
  & $StopScript -ApiPort $ApiPort -WebPort $WebPort -Quiet
  throw
}

Write-Output ""
Write-Output "Aquill development servers are running."
Write-Output "  API: $ApiUrl"
Write-Output "  Web: $WebUrl"
Write-Output "  PID file: $PidFile"
Write-Output ""
Write-Output "Stop with:"
Write-Output "  $ProjectRoot\scripts\stop-local.ps1"
