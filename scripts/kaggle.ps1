param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $KaggleArgs
)

$token = [Environment]::GetEnvironmentVariable("KAGGLE_API_TOKEN", "Process")
if (-not $token) {
    $token = [Environment]::GetEnvironmentVariable("KAGGLE_API_TOKEN", "User")
}

if (-not $token) {
    throw "KAGGLE_API_TOKEN is not set. Create a Kaggle API token and store it as a user environment variable."
}

$env:KAGGLE_API_TOKEN = $token

$kaggleCommand = Get-Command kaggle -ErrorAction SilentlyContinue
if ($kaggleCommand) {
    $kagglePath = $kaggleCommand.Source
} else {
    $fallbackPath = Join-Path $env:LOCALAPPDATA "Programs\Python\Python313\Scripts\kaggle.exe"
    if (Test-Path -LiteralPath $fallbackPath) {
        $kagglePath = $fallbackPath
    } else {
        throw "Kaggle CLI was not found on PATH or at $fallbackPath."
    }
}

& $kagglePath @KaggleArgs
exit $LASTEXITCODE
