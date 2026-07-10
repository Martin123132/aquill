param(
  [string]$ApiBase = "http://127.0.0.1:5190",
  [string]$SourceJobId = ""
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "dev-env.ps1")

Add-Type -AssemblyName System.Net.Http

$ProjectRoot = $env:TRANSCRIBER_ROOT
$TmpRoot = Join-Path $ProjectRoot "tmp"
$ArchivePath = Join-Path $TmpRoot ("archive-roundtrip-{0}.zip" -f [guid]::NewGuid().ToString("N"))
$ImportedJobId = $null

function Invoke-Json {
  param(
    [string]$Uri,
    [string]$Method = "GET"
  )

  try {
    return Invoke-RestMethod -Uri $Uri -Method $Method -TimeoutSec 10
  }
  catch {
    throw "Request failed: $Method $Uri. $($_.Exception.Message)"
  }
}

function Import-Archive {
  param(
    [string]$Uri,
    [string]$Path
  )

  $Client = New-Object System.Net.Http.HttpClient
  $Form = New-Object System.Net.Http.MultipartFormDataContent
  $Stream = [System.IO.File]::OpenRead($Path)
  $FileContent = New-Object System.Net.Http.StreamContent($Stream)

  try {
    $FileContent.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse("application/zip")
    $Form.Add($FileContent, "file", [System.IO.Path]::GetFileName($Path))
    $Response = $Client.PostAsync($Uri, $Form).GetAwaiter().GetResult()
    $Body = $Response.Content.ReadAsStringAsync().GetAwaiter().GetResult()

    if (-not $Response.IsSuccessStatusCode) {
      throw "Import failed with HTTP $([int]$Response.StatusCode): $Body"
    }

    return $Body | ConvertFrom-Json
  }
  finally {
    $FileContent.Dispose()
    $Stream.Dispose()
    $Form.Dispose()
    $Client.Dispose()
  }
}

Write-Host ""
Write-Host "Archive round-trip smoke"
Write-Host "  API:     $ApiBase"
Write-Host "  Project: $ProjectRoot"
Write-Host "  Temp:    $TmpRoot"
Write-Host ""

$JobsResponse = Invoke-Json -Uri "$ApiBase/api/jobs"
$Jobs = @($JobsResponse.jobs)
if ($Jobs.Count -eq 0) {
  throw "No jobs found. Run or import a completed local job before this smoke check."
}

if ($SourceJobId) {
  $SourceJob = $Jobs | Where-Object { $_.id -eq $SourceJobId } | Select-Object -First 1
  if (-not $SourceJob) {
    throw "Source job '$SourceJobId' was not found."
  }
}
else {
  $SourceJob = $Jobs | Where-Object { $_.status -eq "completed" -and $_.archive_url } | Select-Object -First 1
}

if (-not $SourceJob -or $SourceJob.status -ne "completed" -or -not $SourceJob.archive_url) {
  throw "A completed source job with an archive URL is required."
}

try {
  Write-Host "1/4 Exporting archive from job $($SourceJob.id)..."
  Invoke-WebRequest -Uri "$ApiBase$($SourceJob.archive_url)" -OutFile $ArchivePath -TimeoutSec 20 | Out-Null
  $Archive = Get-Item -LiteralPath $ArchivePath
  if ($Archive.Length -le 0) {
    throw "Exported archive is empty."
  }

  Write-Host "2/4 Importing archive through POST /api/jobs/import..."
  $ImportResponse = Import-Archive -Uri "$ApiBase/api/jobs/import" -Path $ArchivePath
  $ImportedJob = $ImportResponse.job
  $ImportedJobId = $ImportedJob.id

  if (-not $ImportedJobId) {
    throw "Import response did not include a job id."
  }
  if ($ImportedJob.status -ne "completed") {
    throw "Imported job status was '$($ImportedJob.status)', expected 'completed'."
  }
  if (-not $ImportedJob.archive_url) {
    throw "Imported job did not expose an archive URL."
  }
  if (-not $ImportedJob.output_dir.StartsWith($ProjectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Imported output directory is outside the project root: $($ImportedJob.output_dir)"
  }

  $ArtifactNames = @()
  if ($ImportedJob.artifacts) {
    $ArtifactNames = @($ImportedJob.artifacts.PSObject.Properties.Name)
  }
  if ($ArtifactNames.Count -eq 0) {
    throw "Imported job did not expose any downloadable artifacts."
  }

  Write-Host "3/4 Verifying imported job can be fetched..."
  $ImportedJobs = @((Invoke-Json -Uri "$ApiBase/api/jobs").jobs)
  $Fetched = $ImportedJobs | Where-Object { $_.id -eq $ImportedJobId } | Select-Object -First 1
  if (-not $Fetched) {
    throw "Imported job '$ImportedJobId' was not present in /api/jobs."
  }

  Write-Host "4/4 Deleting imported smoke job $ImportedJobId..."
  Invoke-Json -Uri "$ApiBase/api/jobs/$ImportedJobId" -Method "DELETE" | Out-Null
  $ImportedJobId = $null

  Write-Host ""
  Write-Host "Archive round-trip smoke passed."
  Write-Host "  Source job:   $($SourceJob.id)"
  Write-Host "  Archive size: $($Archive.Length) bytes"
  Write-Host "  Artifacts:    $($ArtifactNames -join ', ')"
}
finally {
  if ($ImportedJobId) {
    try {
      Invoke-Json -Uri "$ApiBase/api/jobs/$ImportedJobId" -Method "DELETE" | Out-Null
    }
    catch {
      Write-Warning "Could not clean up imported smoke job '$ImportedJobId': $($_.Exception.Message)"
    }
  }
  Remove-Item -LiteralPath $ArchivePath -ErrorAction SilentlyContinue
}
