@echo off
setlocal EnableDelayedExpansion
title Ghost-OS - DEBUG_TREE Multi-Node Type-C Orchestrator
cd /d "%~dp0"

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
echo       GHOST-OS DEBUG_TREE MULTI-NODE TYPE-C TOPOLOGY ENGINE       
echo   4-Node Synchronized Audit & Physical Camera/Mic Sensor Bench
echo ==================================================================
echo.

set "SCRIPT_DIR=%~dp0"
set "USB_ROOT=%SCRIPT_DIR%"
if "%USB_ROOT:~-1%"=="\" set "USB_ROOT=%USB_ROOT:~0,-1%"

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
    echo [*] Opening pre-compiled verified DEBUG_TREE certificate in browser...
    if exist "%USB_ROOT%\reports\certificates\Certificate_DEBUG_TREE_Topology.html" (
        start "" "%USB_ROOT%\reports\certificates\Certificate_DEBUG_TREE_Topology.html"
    )
    pause
    exit /b 0
)

:: Set PYTHONPATH to Ghost-OS modules
set "PYTHONPATH=%USB_ROOT%;%USB_ROOT%\ghost_core;%USB_ROOT%\ghost-core;%USB_ROOT%\ghost_vault;%USB_ROOT%\ghost-vault;%USB_ROOT%\ghost_ai;%USB_ROOT%\ghost-ai;%PYTHONPATH%"

echo [*] Interrogating 4-Node Hardware Interlink Topology over USB Type-C:
echo     [NODE 1] Master Controller (Host Laptop & Physical Sensors)
echo     [NODE 2] Android Smartphone (Type-C Bridge)
echo     [NODE 3] Secondary Workstation (Client Laptop over Type-C Interlink)
echo     [NODE 4] Digital Camera (Digi Cam on Laptop 2 via Type-C)
echo.

%PY_BIN% -m ghost_core.diagnostics.debug_tree

echo.
echo ==================================================================
echo [✓] Synchronization Complete! Launching Verified Hardware Certificate...
echo ==================================================================
echo.

if exist "%USB_ROOT%\reports\certificates\Certificate_DEBUG_TREE_Topology.html" (
    start "" "%USB_ROOT%\reports\certificates\Certificate_DEBUG_TREE_Topology.html"
)

pause
