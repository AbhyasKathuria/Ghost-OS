@echo off
setlocal
title Ghost-OS USB Arrival Watcher Installer

echo ==================================================================
echo       GHOST-OS ZERO-CLICK USB ARRIVAL WATCHER INSTALLER           
echo ==================================================================
echo.
echo Installing background USB arrival watcher for this PC...

set "TARGET_DIR=%LOCALAPPDATA%\GhostOS"
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%" >nul 2>&1

copy /Y "%~dp0ghost-watcher.ps1" "%TARGET_DIR%\ghost-watcher.ps1" >nul

powershell -NoProfile -Command @"
$taskName = 'GhostOS_USB_Watcher'
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-WindowStyle Hidden -ExecutionPolicy Bypass -File \"$env:LOCALAPPDATA\GhostOS\ghost-watcher.ps1\"'
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances Parallel -ExecutionTimeLimit 0

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description 'Ghost-OS USB Arrival Watcher' -Force | Out-Null
Start-ScheduledTask -TaskName $taskName | Out-Null
Write-Host '  ✓ Zero-Click USB Arrival Watcher installed and ACTIVE!' -ForegroundColor Green
"@

echo.
echo ==================================================================
echo               INSTALLATION SUCCESSFUL!                            
echo ==================================================================
echo.
echo You can now test it immediately on this PC:
echo   1. Unplug your 128GB USB pendrive.
echo   2. Plug it back in.
echo   3. Ghost-OS will automatically launch within 1 second!
echo.
pause
