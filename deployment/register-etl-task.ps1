$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$etlScript = Join-Path $repoRoot 'etl\main.py'
$python = Join-Path $repoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    $python = (Get-Command python.exe -ErrorAction Stop).Source
}
$taskName = 'WideWorldImporters Incremental ETL'

$action = New-ScheduledTaskAction `
    -Execute $python `
    -Argument ('"{0}" --mode incremental' -f $etlScript) `
    -WorkingDirectory $repoRoot
$trigger = New-ScheduledTaskTrigger -Daily -At '2:00AM'
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -RestartCount 2 `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -ExecutionTimeLimit (New-TimeSpan -Hours 8)

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description 'Carga incremental diaria de staging de WideWorldImporters.' `
    -RunLevel Limited `
    -Force | Out-Null

Write-Host "Tarea '$taskName' registrada para ejecutarse diariamente a las 2:00 AM."
Write-Host "Se ejecuta con el usuario actual; debe tener una sesion iniciada."
