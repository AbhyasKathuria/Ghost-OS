@echo off
cd /d "%~dp0"
title Ghost-OS Mobile Operator Mode (Remote Dashboard)

echo ==================================================================
echo         GHOST-OS REMOTE OPERATOR & MOBILE DASHBOARD LAUNCHER       
echo ==================================================================
echo.
echo This starts Ghost-OS bound to all network interfaces (0.0.0.0:8000)
echo so you can access the Command Center Dashboard from your smartphone,
echo tablet, or technician laptop over local Wi-Fi or hotspot.
echo.

:: Get local IP address
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address"') do (
    set "LOCAL_IP=%%a"
    goto :found_ip
)
:found_ip
set "LOCAL_IP=%LOCAL_IP: =%"

if defined LOCAL_IP (
    echo [OPERATOR URL] Access dashboard on your phone at:
    echo                http://%LOCAL_IP%:8000
    echo.
)

call "%~dp0Launch-GhostOS.cmd" --remote %*
