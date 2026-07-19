param(
  [switch]$SkipBuild,
  [switch]$SkipWebBuild,
  [string]$ExecutablePath = ""
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "dev-env.ps1")

$ProjectRoot = $env:TRANSCRIBER_ROOT
$BuildScript = Join-Path $ProjectRoot "scripts\build-windows-app.ps1"
$Executable = if ($ExecutablePath) {
  [System.IO.Path]::GetFullPath($ExecutablePath)
}
else {
  Join-Path $ProjectRoot "app\dist\windows\Aquill\Aquill.exe"
}
$SmokeRoot = Join-Path $ProjectRoot "tmp\packaged-desktop-smoke"
$StandardOutput = Join-Path $ProjectRoot "tmp\packaged-desktop-smoke.stdout.log"
$StandardError = Join-Path $ProjectRoot "tmp\packaged-desktop-smoke.stderr.log"
$Process = $null
$ProcessStarted = $false

function Remove-SmokePath {
  param([string]$Path)

  $Resolved = [System.IO.Path]::GetFullPath($Path)
  $ProjectPrefix = $ProjectRoot.TrimEnd("\") + "\"
  if (-not $Resolved.StartsWith($ProjectPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to remove smoke output outside the D-drive project: $Resolved"
  }
  if (Test-Path -LiteralPath $Resolved) {
    Remove-Item -LiteralPath $Resolved -Recurse -Force
  }
}

if (-not $SkipBuild) {
  & $BuildScript -SkipWebBuild:$SkipWebBuild
}
if (-not $Executable.StartsWith("D:\", [System.StringComparison]::OrdinalIgnoreCase)) {
  throw "Packaged executable must be on D:. Requested path: $Executable"
}
if (-not (Test-Path -LiteralPath $Executable)) {
  throw "Packaged executable not found. Run $BuildScript first."
}

Remove-SmokePath $SmokeRoot
Remove-SmokePath $StandardOutput
Remove-SmokePath $StandardError
New-Item -ItemType Directory -Force -Path $SmokeRoot | Out-Null

Write-Host "Running packaged Aquill startup/shutdown smoke..."
try {
  $StartInfo = New-Object System.Diagnostics.ProcessStartInfo
  $StartInfo.FileName = $Executable
  $StartInfo.Arguments = "--headless-smoke --data-root `"$SmokeRoot`""
  $StartInfo.UseShellExecute = $false
  $StartInfo.CreateNoWindow = $true
  $StartInfo.RedirectStandardOutput = $true
  $StartInfo.RedirectStandardError = $true
  $Process = New-Object System.Diagnostics.Process
  $Process.StartInfo = $StartInfo
  if (-not $Process.Start()) {
    throw "Packaged Aquill process could not be started."
  }
  $ProcessStarted = $true

  if (-not $Process.WaitForExit(60000)) {
    Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
    throw "Packaged Aquill did not exit within 60 seconds."
  }
  $Process.WaitForExit()
  $OutputText = $Process.StandardOutput.ReadToEnd()
  $ErrorText = $Process.StandardError.ReadToEnd()
  $OutputText | Set-Content -LiteralPath $StandardOutput -Encoding UTF8
  $ErrorText | Set-Content -LiteralPath $StandardError -Encoding UTF8
  $ExitCode = $Process.ExitCode
  if ($ExitCode -ne 0) {
    if (-not $ErrorText) {
      $ErrorText = "No packaged error log was produced."
    }
    throw "Packaged Aquill exited with code $ExitCode. $ErrorText"
  }
}
finally {
  if ($ProcessStarted -and -not $Process.HasExited) {
    Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
  }
  Remove-SmokePath $SmokeRoot
}

Write-Host "Packaged Aquill smoke passed and its local service stopped."
