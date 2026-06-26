param(
  [int]$ApiPort = 8091,
  [int]$WebPort = 5190,
  [switch]$Quiet
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "dev-env.ps1")

$ProjectRoot = $env:TRANSCRIBER_ROOT
$PidFile = Join-Path $ProjectRoot "tmp\local-server-pids.json"

function Get-RecordedProcessIds {
  if (-not (Test-Path -LiteralPath $PidFile)) {
    return @()
  }

  try {
    $State = Get-Content -LiteralPath $PidFile -Raw | ConvertFrom-Json
  }
  catch {
    return @()
  }

  $RecordedIds = @()
  foreach ($ProcessInfo in @($State.processes)) {
    if ($ProcessInfo.id) {
      $RecordedIds += [int]$ProcessInfo.id
    }
  }
  return $RecordedIds
}

function Get-ProjectProcessIds {
  $Processes = Get-CimInstance Win32_Process | Where-Object {
    $_.ProcessId -ne $PID -and
    $_.CommandLine -and
    $_.CommandLine.Contains($ProjectRoot) -and
    (
      $_.CommandLine.Contains("serve-api.ps1") -or
      $_.CommandLine.Contains("serve-web.ps1") -or
      $_.CommandLine.Contains("revenge_transcriber.server") -or
      ($_.CommandLine.Contains("vite") -and $_.CommandLine.Contains("--port $WebPort")) -or
      ($_.Name -eq "esbuild.exe" -and $_.CommandLine.Contains($ProjectRoot))
    )
  }

  return @($Processes | Select-Object -ExpandProperty ProcessId)
}

function Get-ProjectPortOwnerIds {
  $Connections = Get-NetTCPConnection -LocalPort $ApiPort, $WebPort -State Listen -ErrorAction SilentlyContinue
  $OwnerIds = @()

  foreach ($Connection in @($Connections)) {
    $Process = Get-CimInstance Win32_Process -Filter "ProcessId = $($Connection.OwningProcess)" -ErrorAction SilentlyContinue
    if ($Process -and $Process.CommandLine -and $Process.CommandLine.Contains($ProjectRoot)) {
      $OwnerIds += [int]$Connection.OwningProcess
    }
  }

  return $OwnerIds
}

$TargetIds = @()
$TargetIds += Get-RecordedProcessIds
$TargetIds += Get-ProjectProcessIds
$TargetIds += Get-ProjectPortOwnerIds
$TargetIds = @($TargetIds | Where-Object { $_ -and $_ -ne $PID } | Sort-Object -Unique)

if ($TargetIds.Count -eq 0) {
  if (-not $Quiet) {
    Write-Host "No Aquill local server processes found."
  }
  if (Test-Path -LiteralPath $PidFile) {
    Remove-Item -LiteralPath $PidFile -Force
  }
  return
}

foreach ($TargetId in $TargetIds) {
  Stop-Process -Id $TargetId -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Milliseconds 500

$RemainingIds = @()
$RemainingIds += Get-ProjectProcessIds
$RemainingIds += Get-ProjectPortOwnerIds
$RemainingIds = @($RemainingIds | Where-Object { $_ -and $_ -ne $PID } | Sort-Object -Unique)

if ($RemainingIds.Count -gt 0) {
  throw "Some local server processes did not stop: $($RemainingIds -join ', ')"
}

if (Test-Path -LiteralPath $PidFile) {
  Remove-Item -LiteralPath $PidFile -Force
}

if (-not $Quiet) {
  Write-Host "Stopped Aquill local servers."
}
