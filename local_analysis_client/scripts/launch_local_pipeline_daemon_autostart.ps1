param(
    [string]$DeliveryRoot = "captures_local_delivery",
    [string]$ConfigPath = "config.yaml",
    [string]$PendingUploadDir = "processed_results\pending_upload",
    [string]$ManifestPath = "processed_results\session_consume_manifest.json",
    [string]$CloudHost = "127.0.0.1",
    [int]$PollSeconds = 15,
    [int]$ConsumeLimit = 0,
    [int]$RetryLimit = 0,
    [int]$RetryEveryCycles = 4
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$daemonScript = Join-Path $repoRoot "run_local_pipeline_daemon.ps1"
$logDir = Join-Path $repoRoot "processed_results\daemon_logs"
$logPath = Join-Path $logDir "local_pipeline_daemon_latest.log"

New-Item -ItemType Directory -Force -Path $logDir | Out-Null
Set-Location $repoRoot

try {
    Start-Transcript -Path $logPath -Append | Out-Null
}
catch {
    # If transcript cannot start, continue with daemon startup instead of blocking autostart.
}

try {
    & $daemonScript `
        -DeliveryRoot $DeliveryRoot `
        -ConfigPath $ConfigPath `
        -PendingUploadDir $PendingUploadDir `
        -ManifestPath $ManifestPath `
        -CloudHost $CloudHost `
        -PollSeconds $PollSeconds `
        -ConsumeLimit $ConsumeLimit `
        -RetryLimit $RetryLimit `
        -RetryEveryCycles $RetryEveryCycles
}
finally {
    try {
        Stop-Transcript | Out-Null
    }
    catch {
    }
}
