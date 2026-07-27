@echo off
setlocal
set "SCRIPT_DIR=%~dp0"

REM ──────────────────────────────────────────────────────────────────────────
REM  install.bat — Double-click / CMD launcher for install.ps1
REM ──────────────────────────────────────────────────────────────────────────
REM
REM  The main entry point for fresh installs is the PowerShell one-liner:
REM      iwr -useb https://raw.githubusercontent.com/aidgcreator-prog/SmolAgent/smolagent_modular/install.ps1 | iex
REM
REM  This .bat is here for convenience: if you already have the repo cloned
REM  (or saved the script locally), you can double-click this file instead
REM  of typing out the one-liner.
REM
REM  Any arguments are forwarded straight through to install.ps1, e.g.:
REM      install.bat -NonInteractive
REM      install.bat -InstallDir "D:\MyApps"
REM ──────────────────────────────────────────────────────────────────────────

if not exist "%SCRIPT_DIR%install.ps1" (
    echo [ERROR] install.ps1 not found next to this file.
    echo.
    echo Download the installer with:
    echo   iwr -useb https://raw.githubusercontent.com/aidgcreator-prog/SmolAgent/smolagent_modular/install.ps1 ^| iex
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%install.ps1" %*
set EXITCODE=%errorlevel%

if %EXITCODE% neq 0 (
    echo.
    echo Installer exited with code %EXITCODE%. See messages above.
    pause
)

exit /b %EXITCODE%
