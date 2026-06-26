$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
if (-not $ProjectRoot.StartsWith("D:\", [System.StringComparison]::OrdinalIgnoreCase)) {
  throw "Aquill must be run from a D-drive checkout. Current project root: $ProjectRoot"
}

$AppRoot = Join-Path $ProjectRoot "app"
$CacheRoot = Join-Path $ProjectRoot "cache"
$TmpRoot = Join-Path $ProjectRoot "tmp"

$RequiredDirectories = @(
  $ProjectRoot,
  $AppRoot,
  (Join-Path $ProjectRoot "models"),
  (Join-Path $ProjectRoot "inputs"),
  (Join-Path $ProjectRoot "outputs"),
  (Join-Path $ProjectRoot "data"),
  $TmpRoot,
  $CacheRoot,
  (Join-Path $CacheRoot "pip"),
  (Join-Path $CacheRoot "huggingface"),
  (Join-Path $CacheRoot "huggingface\hub"),
  (Join-Path $CacheRoot "huggingface\transformers"),
  (Join-Path $CacheRoot "torch"),
  (Join-Path $CacheRoot "npm"),
  (Join-Path $CacheRoot "pycache"),
  (Join-Path $CacheRoot "python-user"),
  (Join-Path $CacheRoot "uv")
)

foreach ($Directory in $RequiredDirectories) {
  New-Item -ItemType Directory -Force -Path $Directory | Out-Null
}

$env:TRANSCRIBER_ROOT = $ProjectRoot
$env:TEMP = $TmpRoot
$env:TMP = $TmpRoot
$env:PIP_CACHE_DIR = Join-Path $CacheRoot "pip"
$env:PIP_DISABLE_PIP_VERSION_CHECK = "1"
$env:HF_HOME = Join-Path $CacheRoot "huggingface"
$env:HUGGINGFACE_HUB_CACHE = Join-Path $CacheRoot "huggingface\hub"
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"
$env:TRANSFORMERS_CACHE = Join-Path $CacheRoot "huggingface\transformers"
$env:TORCH_HOME = Join-Path $CacheRoot "torch"
$env:XDG_CACHE_HOME = $CacheRoot
$env:PYTHONPYCACHEPREFIX = Join-Path $CacheRoot "pycache"
$env:PYTHONUSERBASE = Join-Path $CacheRoot "python-user"
$env:npm_config_cache = Join-Path $CacheRoot "npm"
$env:UV_CACHE_DIR = Join-Path $CacheRoot "uv"

Write-Host "D-drive transcription environment active:"
Write-Host "  TRANSCRIBER_ROOT=$env:TRANSCRIBER_ROOT"
Write-Host "  TEMP=$env:TEMP"
Write-Host "  HF_HOME=$env:HF_HOME"
