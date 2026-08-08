param(
    [string]$BaseUrl = "http://127.0.0.1:5000",
    [string]$OllamaUrl = "http://127.0.0.1:11434",
    [int]$TimeoutSec = 10
)

$ErrorActionPreference = "Stop"

function Test-HttpEndpoint {
    param(
        [string]$Name,
        [string]$Url
    )

    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec $TimeoutSec
        [PSCustomObject]@{
            Name = $Name
            Url = $Url
            StatusCode = [int]$response.StatusCode
            Ok = $true
            Error = ""
        }
    }
    catch {
        [PSCustomObject]@{
            Name = $Name
            Url = $Url
            StatusCode = 0
            Ok = $false
            Error = $_.Exception.Message
        }
    }
}

$checks = @(
    @{ Name = "web.home"; Url = "$BaseUrl/" },
    @{ Name = "web.dashboard"; Url = "$BaseUrl/api/dashboard" },
    @{ Name = "text.dashboard"; Url = "$BaseUrl/api/text-library/dashboard" },
    @{ Name = "image.dashboard"; Url = "$BaseUrl/api/image-library/dashboard" },
    @{ Name = "draw.models"; Url = "$BaseUrl/api/draw/models" },
    @{ Name = "ollama.root"; Url = "$OllamaUrl/" }
)

$results = foreach ($check in $checks) {
    Test-HttpEndpoint -Name $check.Name -Url $check.Url
}

$results | Format-Table -AutoSize

$failed = @($results | Where-Object { -not $_.Ok })
if ($failed.Count -gt 0) {
    Write-Error "Health check failed: $($failed.Count) endpoint(s) unavailable"
    exit 1
}

Write-Host "Health check passed: $($results.Count) endpoint(s) available"
