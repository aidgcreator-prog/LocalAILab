@echo off
setlocal
set "SCRIPT_DIR=%~dp0"

REM This launcher is intentionally hardware-agnostic — it never assumes
REM any specific GPU/CPU. All hardware detection (NVIDIA/AMD/CPU-only,
REM driver CUDA version, per-GPU compute capability) and the real-kernel
REM verification of the installed PyTorch build happen dynamically inside
REM SETUP.ps1 for WHATEVER machine this is run on, since this app is
REM distributed to end users with unknown/varied hardware — see SETUP.ps1
REM Step 4 (GPU detection), Step 5b (GPU wheel verification + automatic
REM CPU fallback), and Step 8 (Playwright + Chromium install/verification
REM for Deep Research's optional browser tools) for the actual logic.
REM
REM Any arguments passed to this .bat are forwarded straight through to
REM SETUP.ps1 — e.g. pass -NonInteractive for unattended/CI runs.
REM llama-cpp-python is no longer installed by default. To use GGUF
REM models (.gguf) in-process, install it manually after setup:
REM   pip install llama-cpp-python
REM Or use the "llama-server (external process)" backend — just download
REM llama-server.exe from llama.cpp releases and set its path in the app UI.

if not exist "%SCRIPT_DIR%SETUP.ps1" (
    echo [ERROR] SETUP.ps1 not found next to this file.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%SETUP.ps1" %*
set EXITCODE=%errorlevel%

exit /b %EXITCODE%
