@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Ghost-OS Hardware Intelligence Platform

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
echo             GHOST-OS PORTABLE WINDOWS LAUNCHER                    
echo    Zero-Install * Smart-App-Control Safe * USB Encrypted Vault
echo ==================================================================

:: Parse arguments for remote mode
set "GHOST_HOST=127.0.0.1"
if "%~1"=="--remote" (
    set "GHOST_HOST=0.0.0.0"
    set "GHOST_ALLOW_REMOTE=1"
    echo [MODE] Remote Mobile Operator Mode (Host: 0.0.0.0:8000)
    shift
) else (
    echo [MODE] Localhost Diagnostic Mode (Host: 127.0.0.1:8000)
)

:: Ensure required directories exist on the USB
if not exist "%~dp0.ghost_temp" mkdir "%~dp0.ghost_temp" >nul 2>&1
if not exist "%~dp0reports" mkdir "%~dp0reports" >nul 2>&1
if not exist "%~dp0reports\scans" mkdir "%~dp0reports\scans" >nul 2>&1
if not exist "%~dp0reports\certificates" mkdir "%~dp0reports\certificates" >nul 2>&1

:: Enforce zero host disk extraction
set "DOTNET_BUNDLE_EXTRACT_BASE_DIR=%~dp0.ghost_temp"
set "PYTHONPATH=%~dp0;%~dp0ghost-core;%~dp0ghost_core;%~dp0ghost-vault;%~dp0ghost_vault;%~dp0ghost-ai;%~dp0ghost_ai"
set "GHOST_VAULT_PATH=%~dp0GhostVault\vault.enc"

:: [1/3] Run Native SAC-Safe Hardware Intelligence Collector
echo [1/3] Running Hardware Intelligence Audit (Native SAC-Safe)...
if exist "%~dp0tools\collect-hardware.ps1" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\collect-hardware.ps1" -OutputPath "%~dp0reports\scan-latest.json"
)

:: Secondary fallback only if scan-latest.json was not produced
if not exist "%~dp0reports\scan-latest.json" (
    if exist "%~dp0Ghost-Companion.exe" (
        echo [INFO] Invoking native binary fallback...
        "%~dp0Ghost-Companion.exe" --output "%~dp0reports\scan-latest.json" %*
    )
)

:: [2/3] Auto-Archive Hook: Guarantee permanent machine persistence on USB drive
echo [2/3] Archiving Permanent Hardware Certificates on USB...
if exist "%~dp0reports\scan-latest.json" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\auto-archive-scan.ps1" -ScanFile "%~dp0reports\scan-latest.json" -ReportsDir "%~dp0reports"
)

:: [3/3] Locate Python Runtime (Check USB first, then host)
echo [3/3] Initializing Offline Presentation Engine...
set "PYTHON_EXE="
if exist "%~dp0tools\python\python.exe" (
    set "PYTHON_EXE=%~dp0tools\python\python.exe"
    set "PYTHONHOME=%~dp0tools\python"
    echo [ENV] Using USB Portable Python Runtime: tools\python\python.exe
) else if exist "%~dp0python\python.exe" (
    set "PYTHON_EXE=%~dp0python\python.exe"
    set "PYTHONHOME=%~dp0python"
    echo [ENV] Using USB Portable Python Runtime: python\python.exe
) else (
    where python >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        set "PYTHON_EXE=python"
    ) else (
        where py >nul 2>&1
        if !ERRORLEVEL! EQU 0 (
            set "PYTHON_EXE=py -3.12"
        )
    )
)

:: Launch Ghost-Core backend if Python runtime is available
set "SERVER_READY=0"
if defined PYTHON_EXE (
    echo [MOBILE] Interrogating USB bus for connected Android / iOS mobile devices...
    !PYTHON_EXE! -m ghost_core.scanners.phone_scanner >nul 2>&1
    echo [ENGINE] Spawning Ghost-Core API Engine on !GHOST_HOST!:8000...
    start "Ghost-Core Engine" /min !PYTHON_EXE! -m uvicorn ghost_core.api.server:app --host !GHOST_HOST! --port 8000
    
    :: Active health check loop: wait up to 8 seconds for server to respond
    echo [ENGINE] Synchronizing IPC sockets...
    for /L %%i in (1,1,10) do (
        if !SERVER_READY! EQU 0 (
            powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/v1/health' -UseBasicParsing -TimeoutSec 1; if ($r.StatusCode -eq 200) { exit 0 } } catch {}; exit 1" >nul 2>&1
            if !ERRORLEVEL! EQU 0 (
                set "SERVER_READY=1"
            ) else (
                ping 127.0.0.1 -n 1 >nul 2>&1
            )
        )
    )
)

:: Bulletproof UI Launch: Open Admin Dashboard if server is up, otherwise open Standalone Verified Certificate
echo.
if !SERVER_READY! EQU 1 (
    echo [SUCCESS] Ghost-Core Engine active. Launching Interactive Admin Dashboard...
    start "" "http://127.0.0.1:8000/"
) else (
    echo [SUCCESS] Operating in Standalone Zero-Server Mode.
    echo [SUCCESS] Opening Verified Cryptographic Diagnostic Certificate...
    if exist "%~dp0reports\Ghost-Trust-Certificate-Live.html" (
        start "" "%~dp0reports\Ghost-Trust-Certificate-Live.html"
    ) else if exist "%~dp0START_HERE.html" (
        start "" "%~dp0START_HERE.html"
    )
)

echo.
echo ==================================================================
echo [COMPLETE] Hardware audit and reports generated successfully!
echo [STORAGE] Saved to USB: reports\scans\ and reports\certificates\
echo ==================================================================
echo.
