@echo off
setlocal enabledelayedexpansion
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo ======================================================================
echo  Building Installer for LocalAiLab Assistant (LocalAiLab_Setup.exe)
echo ======================================================================
echo.

set "ISCC_PATH="

REM Check PATH
where iscc >nul 2>nul
if %errorlevel% equ 0 (
    set "ISCC_PATH=iscc"
    goto FOUND
)

REM Check standard 64-bit path
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=C:\Program Files\Inno Setup 6\ISCC.exe"
    goto FOUND
)

REM Check standard 32-bit (x86) path
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    goto FOUND
)

:NOT_FOUND
echo [ERROR] Inno Setup Compiler (ISCC.exe) was not found on your system.
echo.
echo To build LocalAiLab_Setup.exe, please install Inno Setup 6 (Free & Open Source):
echo   Download Link: https://jrsoftware.org/isdl.php
echo.
echo After installing Inno Setup, run this batch file again.
echo.
pause
exit /b 1

:FOUND
echo [INFO] Found Inno Setup Compiler: "%ISCC_PATH%"
echo [INFO] Compiling installer.iss...
echo.

"%ISCC_PATH%" "%SCRIPT_DIR%installer.iss"
set EXITCODE=%errorlevel%

echo.
if %EXITCODE% equ 0 (
    echo ======================================================================
    echo  SUCCESS: Installer built successfully!
    echo  Output Location: "%SCRIPT_DIR%Output\LocalAiLab_Setup.exe"
    echo ======================================================================
) else (
    echo [ERROR] Installer build failed with exit code %EXITCODE%.
)

echo.
pause
exit /b %EXITCODE%
