@echo off
title LumiDim Launcher
cd /d "%~dp0"

:: Check if pythonw is available
where pythonw >nul 2>nul
if %errorlevel% equ 0 (
    start "" pythonw main.py %*
) else (
    where python >nul 2>nul
    if %errorlevel% equ 0 (
        start "" python main.py %*
    ) else (
        echo [ERROR] Python was not found in PATH!
        pause
    )
)
