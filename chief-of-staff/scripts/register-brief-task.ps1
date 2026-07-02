# chief-of-staff/scripts/register-brief-task.ps1
#
# Registers (or updates) the "CoS Morning Brief" Windows scheduled task that runs the
# meeting-aware morning brief weekdays at 08:00 local. Idempotent: re-run any time to
# repair the task definition.
#
# Why this exists instead of a raw `schtasks /create` one-liner:
#   1. -WindowStyle Hidden + LogonType S4U  -> NO PowerShell console flashes up
#      every morning. (A bare `schtasks` interactive task pops a visible window
#      at 08:00, which is disruptive.)
#   2. MultipleInstances IgnoreNew          -> runs never stack if one overruns.
#   3. ExecutionTimeLimit 15 min            -> a wedged `claude -p` can't run forever.
# Run from an ELEVATED PowerShell (creating a scheduled task needs admin).

$ErrorActionPreference = 'Stop'
$taskName = 'CoS Morning Brief'
$script   = Join-Path $PSScriptRoot 'brief-precheck.ps1'

if (-not (Test-Path $script)) { throw "brief-precheck.ps1 not found at $script" }

$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument (
    "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`""
)

# Weekdays at 08:00 local, weekly.
$trigger = New-ScheduledTaskTrigger -Weekly `
    -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday `
    -At 8:00am

# S4U = "run whether logged on or not", no stored password -> non-interactive
# session, so the hidden PowerShell host never surfaces a window.
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME `
    -LogonType S4U -RunLevel Limited

$settings = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15) `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings -Force | Out-Null

Write-Host "Registered/updated scheduled task '$taskName' (MON-FRI 08:00, hidden, no-overlap)." -ForegroundColor Green
(Get-ScheduledTask -TaskName $taskName).Actions | ForEach-Object {
    Write-Host "  Action: $($_.Execute) $($_.Arguments)"
}
