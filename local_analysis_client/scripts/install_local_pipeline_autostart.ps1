param(
    [string]$TaskName = "ClassroomLocalPipelineDaemon",
    [string]$CloudHost = "127.0.0.1",
    [int]$PollSeconds = 15,
    [int]$ConsumeLimit = 0,
    [int]$RetryLimit = 0,
    [int]$RetryEveryCycles = 4,
    [switch]$StartNow
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$launcherPath = Join-Path $repoRoot "scripts\launch_local_pipeline_daemon_autostart.ps1"
$powershellPath = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

if (-not (Test-Path $launcherPath)) {
    throw "Launcher script not found: $launcherPath"
}

$argumentList = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-WindowStyle", "Hidden",
    "-File", ('"{0}"' -f $launcherPath),
    "-CloudHost", $CloudHost,
    "-PollSeconds", "$PollSeconds",
    "-ConsumeLimit", "$ConsumeLimit",
    "-RetryLimit", "$RetryLimit",
    "-RetryEveryCycles", "$RetryEveryCycles"
)

$action = New-ScheduledTaskAction -Execute $powershellPath -Argument ($argumentList -join " ")
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $currentUser
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId $currentUser -LogonType Interactive -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Auto-start the local classroom pipeline daemon at user logon." `
    -Force | Out-Null

if ($StartNow) {
    Start-ScheduledTask -TaskName $TaskName
}

$task = Get-ScheduledTask -TaskName $TaskName
$info = Get-ScheduledTaskInfo -TaskName $TaskName

Write-Output "LOCAL_PIPELINE_AUTOSTART_TASK_NAME=$TaskName"
Write-Output "LOCAL_PIPELINE_AUTOSTART_USER=$currentUser"
Write-Output "LOCAL_PIPELINE_AUTOSTART_REGISTERED=true"
Write-Output ("LOCAL_PIPELINE_AUTOSTART_ENABLED={0}" -f ($task.State -ne "Disabled").ToString().ToLower())
Write-Output "LOCAL_PIPELINE_AUTOSTART_TRIGGER=AtLogOn"
Write-Output "LOCAL_PIPELINE_AUTOSTART_ACTION=$powershellPath"
Write-Output ("LOCAL_PIPELINE_AUTOSTART_STARTNOW={0}" -f $StartNow.ToString().ToLower())
Write-Output ("LOCAL_PIPELINE_AUTOSTART_LAST_RESULT={0}" -f $info.LastTaskResult)
