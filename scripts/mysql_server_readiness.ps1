param(
    [string]$SqliteDb = (Join-Path $PSScriptRoot "..\sci-illust-system\web_app\data\knowledge.db"),
    [string]$SchemaOutput = (Join-Path $PSScriptRoot "..\build\mysql_schema.sql"),
    [switch]$Offline,
    [switch]$CheckConnection,
    [switch]$ApplySchema,
    [switch]$ApplyMigration,
    [string]$HealthBaseUrl = "",
    [string]$OllamaUrl = "http://127.0.0.1:11434"
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$scriptPath = Join-Path $repoRoot "scripts\mysql_server_readiness.py"

if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "找不到联调脚本：$scriptPath"
}

$args = @(
    "--sqlite-db", $SqliteDb,
    "--schema-output", $SchemaOutput
)

if ($Offline) { $args += "--offline" }
if ($CheckConnection) { $args += "--check-connection" }
if ($ApplySchema) { $args += "--apply-schema" }
if ($ApplyMigration) { $args += "--apply-migration" }
if ($HealthBaseUrl) {
    $args += "--health-base-url"
    $args += $HealthBaseUrl
}
if ($OllamaUrl) {
    $args += "--ollama-url"
    $args += $OllamaUrl
}

python $scriptPath @args
