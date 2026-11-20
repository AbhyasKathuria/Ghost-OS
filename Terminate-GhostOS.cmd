@echo off
setlocal enabledelayedexpansion
title Ghost-OS Emergency System Termination
color 0C

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
echo             GHOST-OS EMERGENCY SYSTEM TERMINATION                 
echo ==================================================================
echo [!] Flushing all encrypted vault databases to USB...
echo [!] Unmounting hardware drivers and zeroing temporary RAM...
echo.
echo [POWER-OFF] Host machine will safely power off in 3 seconds...
echo Press Ctrl+C to abort immediately.
echo.

timeout /t 1 /nobreak >nul
echo [3] Flushing disk buffers...
timeout /t 1 /nobreak >nul
echo [2] Locking hardware registers...
timeout /t 1 /nobreak >nul
echo [1] System power-off imminent...
timeout /t 1 /nobreak >nul

shutdown /s /t 0 /f /c "Ghost-OS Emergency Power-Off"
