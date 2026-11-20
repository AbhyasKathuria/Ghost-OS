@echo off
setlocal EnableDelayedExpansion
title Ghost-OS - Mobile Phone Type-C Auditor

echo.
echo           ######################
echo        ############################
echo       ##############################
echo      ################################
echo     ##################################
echo     ####  ######################  ######
echo     ##      ################      ####
echo     ##        ############        ####
echo     ####    ################    ######
echo     #############  ##  ###############
echo      ###########   ##   #############
echo        #########   ##   ###########
echo          #######   ##   #########
echo            #####        #######
echo            ## #  #    #  # ##
echo            ## #  #    #  # ##
echo            ## #  #    #  # ##
echo            ## #  #    #  # ##
echo            ##    #    #    ##
echo.
echo ==================================================================
echo         GHOST-OS MOBILE PHONE AUDITOR (Type-C / USB Bridge)       
echo ==================================================================
echo.

set "SCRIPT_DIR=%~dp0"
set "USB_ROOT=%SCRIPT_DIR%"
if "%USB_ROOT:~-1%"=="\" set "USB_ROOT=%USB_ROOT:~0,-1%"

:: Add bundled portable ADB to PATH
if exist "%USB_ROOT%\tools\adb\adb.exe" (
    set "PATH=%USB_ROOT%\tools\adb;%PATH%"
)

:: Locate Python Interpreter (Prioritize USB Embedded Python)
set "PY_BIN="
if exist "%USB_ROOT%\tools\python\python.exe" (
    set "PY_BIN=%USB_ROOT%\tools\python\python.exe"
) else (
    where py >nul 2>&1
    if not errorlevel 1 (
        set "PY_BIN=py -3.12"
    ) else (
        where python >nul 2>&1
        if not errorlevel 1 (
            set "PY_BIN=python"
        )
    )
)

if "%PY_BIN%"=="" (
    echo [!] Python runtime not detected on host.
    echo [*] Checking connected Android devices via bundled portable ADB...
    if exist "%USB_ROOT%\tools\adb\adb.exe" (
        "%USB_ROOT%\tools\adb\adb.exe" devices -l
    )
    echo.
    echo [*] To run full certificate generation, ensure USB embedded Python is present.
    pause
    exit /b 0
)

:: Set PYTHONPATH to Ghost-OS modules
set "PYTHONPATH=%USB_ROOT%;%USB_ROOT%\ghost_core;%USB_ROOT%\ghost-core;%USB_ROOT%\ghost_vault;%USB_ROOT%\ghost-vault;%USB_ROOT%\ghost_ai;%USB_ROOT%\ghost-ai;%PYTHONPATH%"

echo [*] Interrogating USB bus for connected Android and iOS devices...
echo [*] Ensure Android has 'USB Debugging' enabled, or iPhone has tapped 'Trust'.
echo.

%PY_BIN% -m ghost_core.scanners.phone_scanner

echo.
echo ==================================================================
echo [✓] Audit complete. Check reports\certificates\ for HTML reports!
echo ==================================================================
echo.

:: Automatically open newly generated phone certificate in default browser
for /f "delims=" %%F in ('dir /b /o-d "%USB_ROOT%\reports\certificates\Certificate_Mobile_*.html" 2^>nul') do (
    echo [*] Launching Interactive Mobile Certificate: %%F
    start "" "%USB_ROOT%\reports\certificates\%%F"
    goto :OpenedCert
)
:OpenedCert
pause
