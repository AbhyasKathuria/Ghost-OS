@echo off
setlocal
title Ghost-OS USB Arrival Watcher Uninstaller

echo ==================================================================
echo       GHOST-OS USB ARRIVAL WATCHER UNINSTALLER                    
echo ==================================================================
echo.

powershell -NoProfile -Command "Unregister-ScheduledTask -TaskName 'GhostOS_USB_Watcher' -Confirm:$false -ErrorAction SilentlyContinue; Stop-Process -Name powershell -ErrorAction SilentlyContinue"
rmdir /S /Q "%LOCALAPPDATA%\GhostOS" >nul 2>&1

echo   ✓ USB Arrival Watcher removed from this computer.
echo.
pause
