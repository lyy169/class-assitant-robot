param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("analyze", "retry", "consume")]
    [string]$Mode,

    [string]$CloudHost = "8.148.205.228",

    [string]$PackageDir = "captures_local_delivery/classroom_101/session_001",

    [string]$DeliveryRoot = "captures_local_delivery",

    [string]$ConfigPath = "config.yaml",

    [string]$PendingUploadDir = "",

    [string]$ManifestPath = "",

    [int]$Limit = 0,

    [bool]$EnrichMissingSignals = $true,

    [string]$EnrichmentRoot = "processed_results\delivery_enrichment",

    [string]$EnrichEngine = "auto",

    [string]$EnrichModel = "C:\Users\lyy\Desktop\gradu\asr_models\faster-whisper-base",

    [string]$EnrichLanguage = "auto",

    [string]$EnrichDevice = "cpu",

    [string]$EnrichComputeType = "int8",

    [switch]$EnrichForceTranscript,

    [switch]$EnrichForceQuestions
)

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptRoot "..\..")

Write-Host "HTTP_PROXY=$env:HTTP_PROXY"
Write-Host "HTTPS_PROXY=$env:HTTPS_PROXY"
Write-Host "ALL_PROXY=$env:ALL_PROXY"
Write-Host "NO_PROXY=$env:NO_PROXY"

$noProxyValue = "$CloudHost,localhost,127.0.0.1,::1"
$env:NO_PROXY = $noProxyValue
$env:no_proxy = $noProxyValue

Remove-Item Env:HTTP_PROXY -ErrorAction SilentlyContinue
Remove-Item Env:HTTPS_PROXY -ErrorAction SilentlyContinue
Remove-Item Env:ALL_PROXY -ErrorAction SilentlyContinue
Remove-Item Env:http_proxy -ErrorAction SilentlyContinue
Remove-Item Env:https_proxy -ErrorAction SilentlyContinue
Remove-Item Env:all_proxy -ErrorAction SilentlyContinue

Write-Host "effective_NO_PROXY=$env:NO_PROXY"
Write-Host "mode=$Mode"
Write-Host "enrich_missing_signals=$EnrichMissingSignals"
if (-not (Test-Path $EnrichModel) -and $EnrichModel -eq "C:\Users\lyy\Desktop\gradu\asr_models\faster-whisper-base") {
    $EnrichModel = "base"
}
Write-Host "enrich_model=$EnrichModel"

Push-Location $repoRoot
try {
    if ($Mode -eq "retry") {
        $args = @("local-processor/scripts/retry_pending_uploads.py")
        if ($ConfigPath) {
            $args += @("--config-path", $ConfigPath)
        }
        if ($PendingUploadDir) {
            $args += @("--pending-upload-dir", $PendingUploadDir)
        }
        if ($Limit -gt 0) {
            $args += @("--limit", "$Limit")
        }
        & python @args
        exit $LASTEXITCODE
    }

    if ($Mode -eq "consume") {
        $args = @(
            "local-processor/scripts/consume_ready_sessions.py",
            "--delivery-root",
            $DeliveryRoot,
            "--upload-mode",
            "auto"
        )
        if ($ConfigPath) {
            $args += @("--config-path", $ConfigPath)
        }
        if ($PendingUploadDir) {
            $args += @("--pending-upload-dir", $PendingUploadDir)
        }
        if ($ManifestPath) {
            $args += @("--manifest-path", $ManifestPath)
        }
        if ($EnrichmentRoot) {
            $args += @("--enrichment-root", $EnrichmentRoot)
        }
        if ($EnrichMissingSignals) {
            $args += @("--enrich-missing-signals")
            $args += @("--enrich-engine", $EnrichEngine)
            $args += @("--enrich-model", $EnrichModel)
            $args += @("--enrich-language", $EnrichLanguage)
            $args += @("--enrich-device", $EnrichDevice)
            $args += @("--enrich-compute-type", $EnrichComputeType)
            if ($EnrichForceTranscript) {
                $args += @("--enrich-force-transcript")
            }
            if ($EnrichForceQuestions) {
                $args += @("--enrich-force-questions")
            }
        }
        if ($Limit -gt 0) {
            $args += @("--limit", "$Limit")
        }
        & python @args
        exit $LASTEXITCODE
    }

    $args = @(
        "scripts/phase3_5c_enrich_and_analyze_delivery_package.py",
        $PackageDir,
        "--upload-mode",
        "auto"
    )
    if ($ConfigPath) {
        $args += @("--config-path", $ConfigPath)
    }
    if ($PendingUploadDir) {
        $args += @("--pending-upload-dir", $PendingUploadDir)
    }
    if ($EnrichmentRoot) {
        $args += @("--enrichment-root", $EnrichmentRoot)
    }
    $args += @("--engine", $EnrichEngine)
    $args += @("--model", $EnrichModel)
    $args += @("--language", $EnrichLanguage)
    $args += @("--device", $EnrichDevice)
    $args += @("--compute-type", $EnrichComputeType)
    if ($EnrichForceTranscript) {
        $args += @("--force-transcript")
    }
    if ($EnrichForceQuestions) {
        $args += @("--force-questions")
    }
    & python @args
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
