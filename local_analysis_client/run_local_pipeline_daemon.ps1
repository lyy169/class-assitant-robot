param(
    [string]$DeliveryRoot = "captures_local_delivery",
    [string]$ConfigPath = "config.yaml",
    [string]$PendingUploadDir = "processed_results\pending_upload",
    [string]$ManifestPath = "processed_results\session_consume_manifest.json",
    [string]$CloudHost = "8.148.205.228",
    [int]$PollSeconds = 15,
    [int]$ConsumeLimit = 0,
    [int]$RetryLimit = 0,
    [int]$RetryEveryCycles = 4,
    [switch]$Once
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$runnerPath = Join-Path $repoRoot "local-processor\scripts\run_upload_with_no_proxy.ps1"
$cycle = 0

function Invoke-Mode {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Mode,
        [int]$Limit = 0
    )

    $args = @(
        "-ExecutionPolicy", "Bypass",
        "-File", $runnerPath,
        "-Mode", $Mode,
        "-CloudHost", $CloudHost
    )

    if ($Mode -eq "consume") {
        $args += @("-DeliveryRoot", $DeliveryRoot)
        if ($ManifestPath) {
            $args += @("-ManifestPath", $ManifestPath)
        }
    }

    if ($ConfigPath) {
        $args += @("-ConfigPath", $ConfigPath)
    }
    if ($PendingUploadDir) {
        $args += @("-PendingUploadDir", $PendingUploadDir)
    }
    if ($Limit -gt 0) {
        $args += @("-Limit", "$Limit")
    }

    & powershell @args | ForEach-Object { Write-Host $_ }
    return $LASTEXITCODE
}

Write-Host "run_local_pipeline_daemon.ps1"
Write-Host "delivery_root=$DeliveryRoot"
Write-Host "config_path=$ConfigPath"
Write-Host "pending_upload_dir=$PendingUploadDir"
Write-Host "manifest_path=$ManifestPath"
Write-Host "cloud_host=$CloudHost"
Write-Host "poll_seconds=$PollSeconds"
Write-Host "retry_every_cycles=$RetryEveryCycles"
Write-Host "once=$Once"

while ($true) {
    $cycle += 1
    $startedAt = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host ""
    Write-Host "[$startedAt] cycle=$cycle consume:start"

    try {
        $consumeExit = Invoke-Mode -Mode "consume" -Limit $ConsumeLimit
        Write-Host "[$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")] cycle=$cycle consume:exit_code=$consumeExit"
    }
    catch {
        Write-Host "[$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")] cycle=$cycle consume:exception=$($_.Exception.Message)"
    }

    if ($RetryEveryCycles -gt 0 -and (($cycle % $RetryEveryCycles) -eq 0 -or $Once)) {
        Write-Host "[$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")] cycle=$cycle retry:start"
        try {
            $retryExit = Invoke-Mode -Mode "retry" -Limit $RetryLimit
            Write-Host "[$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")] cycle=$cycle retry:exit_code=$retryExit"
        }
        catch {
            Write-Host "[$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")] cycle=$cycle retry:exception=$($_.Exception.Message)"
        }
    }

    if ($Once) {
        break
    }

    Start-Sleep -Seconds $PollSeconds
}
