@echo off
setlocal enabledelayedexpansion
title Ghost-OS 1-Click UEFI Boot Helper
color 0C

cd /d "%~dp0"

cls
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
echo           GHOST-OS: 1-CLICK DIRECT USB REBOOT HELPER               
echo    Zero Key-Spamming * 100% Reliable Boot for ASUS ZenBook / PCs   
echo ==================================================================
echo.
echo On modern ASUS ZenBook OLED laptops and Windows 11 PCs, Fast Boot
echo skips the keyboard detection window, making the [Esc] key fail.
echo.
echo Choose how you want to boot into Ghost-OS:
echo.
echo   [1] Direct USB Boot via Windows Advanced Menu (RECOMMENDED)
echo       - Automatically pauses BitLocker for 1 reboot (prevents recovery key prompt)
echo       - Reboots directly to the blue "Use a Device" menu
echo       - Just click: "Use a device" -> "UEFI: SanDisk" -> DONE!
echo.
echo   [2] Reboot directly into ASUS UEFI BIOS Setup
echo       - Reboots directly into the ASUS BIOS screen without pressing F2
echo       - From BIOS: Press [F7] for Advanced -> "Boot" -> "Boot Override: SanDisk"
echo.
echo   [3] Learn the ASUS ZenBook Hardware Key Trick (Manual Cold Boot)
echo.
echo   [4] Cancel and Exit
echo.
set /p choice="Enter your choice (1, 2, 3, or 4): "

if "%choice%"=="1" (
    echo.
    echo [*] Safely preparing BitLocker for 1 reboot...
    manage-bde -protectors -disable C: -RebootCount 1 >nul 2>&1
    echo [*] Rebooting to Windows Advanced Boot Menu in 3 seconds...
    echo [*] When the blue screen appears, click: "Use a device" -> "UEFI: SanDisk"
    timeout /t 3
    shutdown /r /o /t 0
    exit /b 0
)

if "%choice%"=="2" (
    echo.
    echo [*] Safely preparing BitLocker for 1 reboot...
    manage-bde -protectors -disable C: -RebootCount 1 >nul 2>&1
    echo [*] Rebooting directly to ASUS BIOS Setup in 3 seconds...
    timeout /t 3
    shutdown /r /fw /t 0
    if !ERRORLEVEL! NEQ 0 (
        echo [!] Direct firmware reboot not supported by OS. Falling back to Advanced Menu...
        shutdown /r /o /t 0
    )
    exit /b 0
)

if "%choice%"=="3" (
    cls
    echo.
    echo ==================================================================
    echo        WHY [Esc] DID NOT WORK AND HOW TO FIX IT ON ASUS
    echo ==================================================================
    echo.
    echo 1. ASUS ZENBOOK FAST BOOT TIMING:
    echo    ZenBook 14 OLED boots in 0.3 seconds. If you click Restart and tap
    echo    [Esc] after the screen lights up, it is ALREADY TOO LATE!
    echo.
    echo    THE CORRECT ASUS HARDWARE METHOD:
    echo    a) Shut down the laptop COMPLETELY (Power OFF).
    echo    b) Press and HOLD DOWN the [Esc] key (or [F2] key) FIRST.
    echo    c) KEEP HOLDING [Esc] while you tap the Power button ONCE.
    echo    d) DO NOT LET GO of [Esc] until the blue Boot Menu appears!
    echo.
    echo 2. FN-LOCK KEY TOGGLE:
    echo    On some ASUS ZenBooks, the top row defaults to Media keys.
    echo    Try holding [Fn] + [Esc] or [Fn] + [F2] while powering on.
    echo.
    echo 3. OR SIMPLY USE OPTION 1 IN THIS TOOL:
    echo    Option 1 reboots directly into the USB device menu with 0 keys!
    echo.
    pause
    goto :EOF
)

exit /b 0
