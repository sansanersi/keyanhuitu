param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$HostAddress = $env:SCI_WEB_HOST,
    [int]$Port = $(if ($env:SCI_WEB_PORT) { [int]$env:SCI_WEB_PORT } else { 5000 }),
    [string]$BioiconsRoot = $env:BIOICONS_ROOT,
    [string]$WebMode = $(if ($env:SCI_WEB_MODE) { $env:SCI_WEB_MODE } else { "stable" })
)

$ErrorActionPreference = "Stop"

if (-not $HostAddress) {
    $HostAddress = "127.0.0.1"
}

$webAppDir = Join-Path $RepoRoot "sci-illust-system\web_app"
$systemDir = Join-Path $RepoRoot "sci-illust-system"
$appEntry = Join-Path $webAppDir "app.py"

if (-not (Test-Path -LiteralPath $appEntry)) {
    throw "找不到 Web 启动入口：$appEntry"
}

if ($BioiconsRoot) {
    New-Item -ItemType Directory -Force -Path $BioiconsRoot | Out-Null
    $env:BIOICONS_ROOT = $BioiconsRoot
}

$env:PYTHONPATH = "$webAppDir;$systemDir;$RepoRoot;$env:PYTHONPATH"
$env:SCI_WEB_MODE = $WebMode
$env:SCI_WEB_HOST = $HostAddress
$env:SCI_WEB_PORT = [string]$Port

Write-Host "Starting sci-illust web service..."
Write-Host "RepoRoot: $RepoRoot"
Write-Host "Url: http://$HostAddress`:$Port"
Write-Host "Mode: $WebMode"

python $appEntry
