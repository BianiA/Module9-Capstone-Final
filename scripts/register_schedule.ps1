# Run from PowerShell after installing Python and extracting the project.
# Registers a real daily local task for the current Windows user.
$ProjectPath = Split-Path -Parent $PSScriptRoot
$PythonExe = (Get-Command python -ErrorAction Stop).Source
$ScriptPath = Join-Path $PSScriptRoot 'pipeline.py'
$Action = New-ScheduledTaskAction -Execute $PythonExe -Argument ('"' + $ScriptPath + '"') -WorkingDirectory $ProjectPath
$Trigger = New-ScheduledTaskTrigger -Daily -At '08:17'
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName 'Capstone09-CustomerPipeline' -Action $Action -Trigger $Trigger -Settings $Settings -Description 'Validate customer purchases and refresh SQLite and CSV outputs' -Force
