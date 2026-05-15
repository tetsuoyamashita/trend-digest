# Register Task Scheduler entry for trend-digest daily ingest (06:00 JST)
# Pattern B: wscript -> run-hidden.vbs -> dpapi_run.ps1 -> pythonw daily_ingest.py
# Usage: Run from Windows Terminal (non-elevated is fine for current user)
#   powershell -NoProfile -ExecutionPolicy Bypass -File _scripts\register_daily_task.ps1

$ErrorActionPreference = 'Stop'

$taskName    = 'trend-digest-daily'
$workDir     = 'C:\Users\yamas\ClaudeCode\trend-digest'
$envTemplate = "$workDir\_scripts\.env.template"
$script      = "$workDir\_scripts\daily_ingest.py"
$dpapiPs1    = "$env:USERPROFILE\.claude\scripts\dpapi_run.ps1"
$vbs         = "$env:USERPROFILE\.claude\scripts\run-hidden.vbs"

foreach ($p in @($dpapiPs1, $vbs, $script, $envTemplate)) {
    if (-not (Test-Path $p)) { throw "Required file missing: $p" }
}

# powershell -File chain that VBS will exec hidden
$psCmd = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$dpapiPs1`" -EnvTemplate `"$envTemplate`" pythonw `"$script`""

$action = New-ScheduledTaskAction -Execute 'wscript.exe' -Argument "`"$vbs`" `"$psCmd`""
# Trigger 1: Daily 06:00 JST (通常運用)
$trigger1 = New-ScheduledTaskTrigger -Daily -At '6:00am'
# Trigger 2: AtLogOn + 5 分 delay (Windows Update reboot 等で 06:00 を逃した場合のフォールバック)
# daily_ingest.py 側の --force/Run DB 当日成功 skip ガードで二重実行は防ぐ
$trigger2 = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$trigger2.Delay = 'PT5M'
$triggers = @($trigger1, $trigger2)
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -RestartCount 1 `
    -RestartInterval (New-TimeSpan -Minutes 10) `
    -DontStopIfGoingOnBatteries `
    -AllowStartIfOnBatteries

if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Write-Host "[register] removing existing task $taskName"
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $triggers `
    -Settings $settings `
    -User $env:USERNAME `
    -RunLevel Limited `
    -Description 'trend-digest daily ingest (Readwise -> LLM screen + summarize -> Notion -> Slack #ai-digest). Pattern B hidden. Trigger: Daily 06:00 + AtLogOn (delay 5min) fallback.'

Write-Host "[register] registered."
Get-ScheduledTask -TaskName $taskName | Format-List TaskName, State, Author
(Get-ScheduledTask -TaskName $taskName | Get-ScheduledTaskInfo) | Format-List LastRunTime, LastTaskResult, NextRunTime
