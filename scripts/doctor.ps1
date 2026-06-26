$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "dev-env.ps1")

$ProjectRoot = $env:TRANSCRIBER_ROOT
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$WebRoot = Join-Path $ProjectRoot "web"
$NodeModules = Join-Path $WebRoot "node_modules"
$Checks = New-Object System.Collections.Generic.List[object]

function Add-Check {
  param(
    [string]$Name,
    [string]$Status,
    [string]$Detail
  )

  $Checks.Add([pscustomobject]@{
    Check = $Name
    Status = $Status
    Detail = $Detail
  }) | Out-Null
}

function Get-CommandPath {
  param([string]$Name)

  $Command = Get-Command $Name -ErrorAction SilentlyContinue
  if ($Command) {
    return $Command.Source
  }
  return $null
}

function Invoke-ToolText {
  param(
    [string]$FilePath,
    [string[]]$Arguments
  )

  $Output = & $FilePath @Arguments 2>&1
  if ($LASTEXITCODE -ne 0) {
    throw ($Output -join "`n")
  }
  return ($Output -join "`n").Trim()
}

Write-Host ""
Write-Host "Aquill doctor"
Write-Host "  Project: $ProjectRoot"
Write-Host ""

if ($ProjectRoot.StartsWith("D:\", [System.StringComparison]::OrdinalIgnoreCase)) {
  Add-Check "Project root" "OK" $ProjectRoot
}
else {
  Add-Check "Project root" "FAIL" "Aquill must be cloned and run from D:."
}

foreach ($DirectoryName in @("app", "web", "scripts", "inputs", "outputs", "data", "models", "cache", "tmp")) {
  $Directory = Join-Path $ProjectRoot $DirectoryName
  if (Test-Path -LiteralPath $Directory) {
    Add-Check $DirectoryName "OK" $Directory
  }
  else {
    Add-Check $DirectoryName "FAIL" "Missing directory: $Directory"
  }
}

$PythonPath = Get-CommandPath "python"
if ($PythonPath) {
  Add-Check "Python" "OK" $PythonPath
}
else {
  Add-Check "Python" "FAIL" "Install Python, then run scripts\setup.ps1."
}

if (Test-Path -LiteralPath $VenvPython) {
  try {
    $Version = Invoke-ToolText -FilePath $VenvPython -Arguments @("--version")
    Add-Check "Virtual environment" "OK" "$VenvPython ($Version)"
  }
  catch {
    Add-Check "Virtual environment" "FAIL" $_.Exception.Message
  }

  try {
    $ImportCheck = Invoke-ToolText -FilePath $VenvPython -Arguments @("-c", "import revenge_transcriber; print('backend import ok')")
    Add-Check "Backend import" "OK" $ImportCheck
  }
  catch {
    Add-Check "Backend import" "FAIL" "Run scripts\setup.ps1. $($_.Exception.Message)"
  }

  try {
    $FfmpegPath = Invoke-ToolText -FilePath $VenvPython -Arguments @("-c", "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())")
    Add-Check "FFmpeg helper" "OK" $FfmpegPath
  }
  catch {
    Add-Check "FFmpeg helper" "FAIL" "Run scripts\setup.ps1. $($_.Exception.Message)"
  }
}
else {
  Add-Check "Virtual environment" "FAIL" "Run scripts\setup.ps1."
  Add-Check "Backend import" "FAIL" "Run scripts\setup.ps1."
  Add-Check "FFmpeg helper" "FAIL" "Run scripts\setup.ps1."
}

$NodePath = Get-CommandPath "node"
if ($NodePath) {
  Add-Check "Node.js" "OK" $NodePath
}
else {
  Add-Check "Node.js" "FAIL" "Install Node.js, then run scripts\setup-web.ps1."
}

$NpmPath = Get-CommandPath "npm.cmd"
if ($NpmPath) {
  Add-Check "npm" "OK" $NpmPath
}
else {
  Add-Check "npm" "FAIL" "Install npm, then run scripts\setup-web.ps1."
}

if (Test-Path -LiteralPath (Join-Path $WebRoot "package-lock.json")) {
  Add-Check "Web lockfile" "OK" (Join-Path $WebRoot "package-lock.json")
}
else {
  Add-Check "Web lockfile" "FAIL" "Missing web\package-lock.json."
}

if (Test-Path -LiteralPath $NodeModules) {
  Add-Check "Web dependencies" "OK" $NodeModules
}
else {
  Add-Check "Web dependencies" "FAIL" "Run scripts\setup-web.ps1."
}

$Checks | Format-Table -AutoSize

$Failures = @($Checks | Where-Object { $_.Status -eq "FAIL" })
if ($Failures.Count -gt 0) {
  throw "Doctor found $($Failures.Count) issue(s). Fix the FAIL rows above and run this again."
}

Write-Host ""
Write-Host "Aquill doctor passed."
