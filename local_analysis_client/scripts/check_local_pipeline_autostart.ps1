param(
    [string]$TaskName = "ClassroomLocalPipelineDaemon"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$logPath = Join-Path $repoRoot "processed_results\daemon_logs\local_pipeline_daemon_latest.log"
$logActive = $false
if (Test-Path $logPath) {
    $ageSeconds = ((Get-Date) - (Get-Item $logPath).LastWriteTime).TotalSeconds
    $logActive = $ageSeconds -lt 120
}

$processes = @()
try {
    $processes = Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -ieq "powershell.exe" -or $_.Name -ieq "pwsh.exe") -and
        $_.CommandLine -and
        (
            $_.CommandLine -like "*run_local_pipeline_daemon.ps1*" -or
            $_.CommandLine -like "*launch_local_pipeline_daemon_autostart.ps1*"
        )
    }
}
catch {
    $processes = @()
}

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    $running = ($processes.Count -gt 0) -or $logActive
    Write-Output "LOCAL_PIPELINE_AUTOSTART_TASK_PRESENT=false"
    Write-Output ("LOCAL_PIPELINE_AUTOSTART_RUNNING={0}" -f ($running.ToString().ToLower()))
    Write-Output ("LOCAL_PIPELINE_AUTOSTART_PROCESS_COUNT={0}" -f $processes.Count)
    Write-Output ("LOCAL_PIPELINE_AUTOSTART_LOG_ACTIVE={0}" -f ($logActive.ToString().ToLower()))
    exit 0
}

$info = Get-ScheduledTaskInfo -TaskName $TaskName

Write-Output "LOCAL_PIPELINE_AUTOSTART_TASK_PRESENT=true"
Write-Output ("LOCAL_PIPELINE_AUTOSTART_TASK_ENABLED={0}" -f ($task.State -ne "Disabled").ToString().ToLower())
Write-Output ("LOCAL_PIPELINE_AUTOSTART_TASK_STATE={0}" -f $task.State)
Write-Output ("LOCAL_PIPELINE_AUTOSTART_RUNNING={0}" -f ((($processes.Count -gt 0) -or $logActive).ToString().ToLower()))
Write-Output ("LOCAL_PIPELINE_AUTOSTART_PROCESS_COUNT={0}" -f $processes.Count)
Write-Output ("LOCAL_PIPELINE_AUTOSTART_LOG_ACTIVE={0}" -f ($logActive.ToString().ToLower()))
Write-Output ("LOCAL_PIPELINE_AUTOSTART_LAST_RESULT={0}" -f $info.LastTaskResult)
Write-Output ("LOCAL_PIPELINE_AUTOSTART_LAST_RUN={0}" -f $info.LastRunTime)
Write-Output ("LOCAL_PIPELINE_AUTOSTART_NEXT_RUN={0}" -f $info.NextRunTime)
