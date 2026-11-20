@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Ghost-OS Universal Hardware Intelligence Platform

:: Unblock Mark-of-the-Web if files were transferred across machines
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-ChildItem -Path '%~dp0' -Recurse -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue" >nul 2>&1

call "%~dp0Launch-GhostOS.cmd" %*
