@echo off
setlocal EnableDelayedExpansion
title Ghost-OS - Cryptographic Tamper-Detection Engine

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
echo       GHOST-OS ASYMMETRIC CRYPTOGRAPHIC FORENSIC VERIFIER         
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
    echo [!] Python runtime not detected.
    pause
    exit /b 1
)

set "PYTHONPATH=%USB_ROOT%;%USB_ROOT%\ghost_core;%USB_ROOT%\ghost_vault;%USB_ROOT%\ghost_ai;%PYTHONPATH%"

%PY_BIN% "%USB_ROOT%\scripts\verify_tamper_demo.py"

echo.
pause
