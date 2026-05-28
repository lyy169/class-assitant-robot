param(
    [string]$TaskName = "ClassroomLocalPipelineDaemon"
)

$ErrorActionPreference = "Stop"

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($task) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Output "LOCAL_PIPELINE_AUTOSTART_REMOVED=true"
}
else {
    Write-Output "LOCAL_PIPELINE_AUTOSTART_REMOVED=false"
}
