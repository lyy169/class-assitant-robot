param(
    [string]$DeliveryRoot = "captures_local_delivery",
    [string]$ConfigPath = "config.yaml",
    [string]$PendingUploadDir = "",
    [string]$ManifestPath = "",
    [int]$Limit = 0,
    [string]$CloudHost = "8.148.205.228"
)

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$runnerPath = Join-Path $repoRoot "local-processor\scripts\run_upload_with_no_proxy.ps1"

Write-Host "run_local_pipeline.ps1"
Write-Host "delivery_root=$DeliveryRoot"
Write-Host "config_path=$ConfigPath"

$args = @(
    "-ExecutionPolicy", "Bypass",
    "-File", $runnerPath,
    "-Mode", "consume",
    "-DeliveryRoot", $DeliveryRoot,
    "-ConfigPath", $ConfigPath,
    "-CloudHost", $CloudHost
)

if ($PendingUploadDir) {
    $args += @("-PendingUploadDir", $PendingUploadDir)
}
if ($ManifestPath) {
    $args += @("-ManifestPath", $ManifestPath)
}
if ($Limit -gt 0) {
    $args += @("-Limit", "$Limit")
}

& powershell @args
exit $LASTEXITCODE
