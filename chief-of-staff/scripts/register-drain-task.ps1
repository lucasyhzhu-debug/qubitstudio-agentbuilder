# chief-of-staff/scripts/register-drain-task.ps1
#
# Registers (or updates) the "CoS Drain" Windows scheduled task that runs the
# continuous inbox drain every 5 minutes. Idempotent: re-run any time to repair
# the task definition.
#
# Why this exists instead of a raw `schtasks /create` one-liner:
#   1. -WindowStyle Hidden + LogonType S4U  -> NO PowerShell console flashes up
#      every 5 minutes. (A bare `schtasks` interactive task pops a visible window
#      on each run, which is jarring at a 5-minute cadence.)
#   2. MultipleInstances IgnoreNew          -> runs never stack if one overruns.
#   3. ExecutionTimeLimit 20 min            -> headroom for a BUSY cycle (many issues /
#      long Discord threads accumulated over hours). IgnoreNew means a run that finishes
#      early costs nothing, so a larger ceiling only protects against a genuinely wedged
#      `claude -p` - it still can't run forever. Do NOT re-tighten to 10: a live busy drain
#      hit the old 10-min limit and Task Scheduler killed it mid-run
#      (SCHED_S_TASK_TERMINATED, last-result 267014).
# Run from an ELEVATED PowerShell (creating a scheduled task needs admin).

$ErrorActionPreference = 'Stop'
$taskName = 'CoS Drain'
$script   = Join-Path $PSScriptRoot 'drain-precheck.ps1'

if (-not (Test-Path $script)) { throw "drain-precheck.ps1 not found at $script" }

$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument (
    "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`""
)

# Every 5 minutes, indefinitely, starting now.
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes 5)

# S4U = "run whether logged on or not", no stored password -> non-interactive
# session, so the hidden PowerShell host never surfaces a window.
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME `
    -LogonType S4U -RunLevel Limited

$settings = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 20) `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings -Force | Out-Null

Write-Host "Registered/updated scheduled task '$taskName' (5-min, hidden, no-overlap)." -ForegroundColor Green
(Get-ScheduledTask -TaskName $taskName).Actions | ForEach-Object {
    Write-Host "  Action: $($_.Execute) $($_.Arguments)"
}
