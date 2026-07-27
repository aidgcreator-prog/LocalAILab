<#
.SYNOPSIS
    One-click Windows installer for SmolAgent — local AI assistant by LocalAiLab.
.DESCRIPTION
    Checks/installs Python and Git, clones the repo, sets up the Python
    environment (venv + PyTorch + all dependencies), and creates a desktop
    shortcut. Run this script on a FRESH machine to go from zero to running.

    USAGE (one-liner — paste into PowerShell):
        iwr -useb https://raw.githubusercontent.com/aidgcreator-prog/SmolAgent/smolagent_modular/install.ps1 | iex

.PARAMETER InstallDir
    Directory to clone the repo into  (default: current directory).
.PARAMETER NonInteractive
    Skip all interactive prompts — for unattended / CI installs.
    llama-cpp-python is skipped when this flag is set.
.PARAMETER NoShortcut
    Skip creating a desktop shortcut.
#>

param(
    [string]$InstallDir    = "",
    [switch]$NonInteractive,
    [switch]$NoShortcut
)

$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$REPO_URL  = "https://github.com/aidgcreator-prog/SmolAgent.git"
$REPO_NAME = "SmolAgent"

if ([string]::IsNullOrWhiteSpace($InstallDir)) {
    $InstallDir = (Get-Location).Path
}
$targetDir = Join-Path $InstallDir $REPO_NAME


# ══════════════════════════════════════════════════════════════════
# Helper functions
# ══════════════════════════════════════════════════════════════════

function Write-Step($s) {
    Write-Host ""
    Write-Host "  $s" -ForegroundColor Cyan
}
function Write-Ok($s)   { Write-Host "  $([char]0x2713) $s" -ForegroundColor Green }
function Write-Warn($s) { Write-Host "  $([char]0x26A0) $s" -ForegroundColor Yellow }
function Write-Err($s)  { Write-Host "  $([char]0x2717) $s" -ForegroundColor Red }

function Refresh-Path {
    $sys = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $usr = [System.Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$sys;$usr"
}

function Test-Command($name) {
    return $null -ne (Get-Command $name -ErrorAction SilentlyContinue)
}

function New-DesktopShortcut {
    param([string]$Target, [string]$Arguments, [string]$WorkingDir, [string]$Name, [string]$IconPath)
    $desktop = [Environment]::GetFolderPath("Desktop")
    $path = Join-Path $desktop "$Name.lnk"
    $wshell = New-Object -ComObject WScript.Shell
    $sc = $wshell.CreateShortcut($path)
    $sc.TargetPath = $Target
    if ($Arguments) { $sc.Arguments = $Arguments }
    $sc.WorkingDirectory = $WorkingDir
    $sc.Description = "$Name by LocalAiLab"
    if ($IconPath) { $sc.IconLocation = "$IconPath, 0" }
    $sc.Save()
    return $path
}

function Convert-JpgToIco {
    param([string]$JpgPath, [string]$IcoPath)
    Add-Type -AssemblyName System.Drawing
    $img = [System.Drawing.Image]::FromFile($JpgPath)
    $icon = [System.Drawing.Icon]::FromHandle($img.GetHicon())
    $fs = [System.IO.File]::OpenWrite($IcoPath)
    $icon.Save($fs)
    $fs.Close()
    $img.Dispose()
    $icon.Dispose()
}


# ══════════════════════════════════════════════════════════════════
# Banner
# ══════════════════════════════════════════════════════════════════

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " SmolAgent — Multipurpose AI Assistant" -ForegroundColor Green
Write-Host " by LocalAiLab  |  smolagents + ChromaDB + llama.cpp" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host " Installing to: $targetDir"
Write-Host ""


# ══════════════════════════════════════════════════════════════════
# STEP 1: Check / Install Python
# ══════════════════════════════════════════════════════════════════

Write-Step "STEP 1/5: Python"

$needPython = $false
$pyVer = $null

$pyCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pyCmd) {
    Write-Warn "Python not found in PATH."
    $needPython = $true
} else {
    $verOut = (& python --version) 2>&1
    $pyVer = ($verOut -replace "Python\s+", "").Trim()
    $parts = $pyVer.Split(".")
    $major = [int]$parts[0]
    $minor = [int]$parts[1]

    if ($major -eq 2) {
        Write-Warn "Python 2 is not supported (found $pyVer)."
        $needPython = $true
    } elseif ($major -eq 3 -and $minor -lt 9) {
        Write-Warn "Python $pyVer is too old (need 3.9+)."
        $needPython = $true
    } else {
        Write-Ok "Python $pyVer found."
    }
}

if ($needPython) {
    Write-Host "  Downloading Python 3.11.9..."
    $installer = Join-Path $env:TEMP "python-3.11.9-amd64.exe"
    try {
        Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe" -OutFile $installer -UseBasicParsing
    } catch {
        Write-Err "Failed to download Python. Install manually from https://www.python.org/downloads/"
        exit 1
    }
    Write-Host "  Installing Python 3.11.9 (per-user)..."
    $proc = Start-Process -FilePath $installer -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_launcher=1 Include_test=0" -Wait -PassThru
    if ($proc.ExitCode -ne 0 -and $proc.ExitCode -ne 3010) {
        Write-Err "Python installer exited with code $($proc.ExitCode)."
        Write-Err "Install manually from https://www.python.org/downloads/ then re-run this installer."
        exit 1
    }
    Refresh-Path
    $pyCheck = (& python --version) 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "Python $($pyCheck -replace 'Python\s+', '') installed."
    } else {
        Write-Err "Python was installed but is not in PATH. Restart PowerShell and re-run the installer."
        exit 1
    }
}

# Verify pip works
& python -m pip --version *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Installing pip..."
    & python -m ensurepip --upgrade
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Failed to install pip. Try: python -m ensurepip --upgrade"
        exit 1
    }
}
Write-Ok "pip is ready."


# ══════════════════════════════════════════════════════════════════
# STEP 2: Check / Install Git
# ══════════════════════════════════════════════════════════════════

Write-Step "STEP 2/5: Git"

if (-not (Test-Command git)) {
    Write-Warn "Git not found in PATH. Installing Git for Windows..."
    $gitVer = "2.47.1"
    $gitUrl = "https://github.com/git-for-windows/git/releases/download/v${gitVer}.windows.1/Git-${gitVer}-64-bit.exe"
    $gitInstaller = Join-Path $env:TEMP "git-installer.exe"
    try {
        Invoke-WebRequest -Uri $gitUrl -OutFile $gitInstaller -UseBasicParsing
    } catch {
        Write-Err "Failed to download Git. Install manually from https://git-scm.com/download/win"
        exit 1
    }
    Write-Host "  Installing Git $gitVer (per-user)..."
    $proc = Start-Process -FilePath $gitInstaller -ArgumentList "/VERYSILENT /NORESTART /SUPPRESSMSGBOXES /CURRENTUSER /COMPONENTS=`"git,icons,gitlfs`"" -Wait -PassThru
    if ($proc.ExitCode -ne 0) {
        Write-Err "Git installer exited with code $($proc.ExitCode)."
        Write-Err "Install manually from https://git-scm.com/download/win then re-run."
        exit 1
    }
    Refresh-Path
    if (Test-Command git) {
        Write-Ok "Git $((git --version) 2>&1) installed."
    } else {
        Write-Err "Git was installed but is not in PATH. Restart PowerShell and re-run."
        exit 1
    }
} else {
    Write-Ok "Git $((git --version) 2>&1) found."
}


# ══════════════════════════════════════════════════════════════════
# STEP 3: Clone the repository
# ══════════════════════════════════════════════════════════════════

Write-Step "STEP 3/5: Downloading SmolAgent"

if (Test-Path $targetDir) {
    if (Test-Path (Join-Path $targetDir ".git")) {
        Write-Ok "Repo already exists at $targetDir (skipping clone)."
    } else {
        Write-Err "Directory '$targetDir' already exists but is not a git repo."
        Write-Err "Remove it or specify a different -InstallDir, then re-run."
        exit 1
    }
} else {
    Write-Host "  Cloning $REPO_URL ..."
    git clone --branch smolagent_modular $REPO_URL $targetDir 2>&1 | ForEach-Object { "  $_" }
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Failed to clone repository. Check your internet connection."
        exit 1
    }
    Write-Ok "Repo cloned to $targetDir"
}
Set-Location $targetDir


# ══════════════════════════════════════════════════════════════════
# STEP 4: Run SETUP.ps1 (GPU detection, venv, PyTorch, deps, Playwright)
# ══════════════════════════════════════════════════════════════════

Write-Step "STEP 4/5: Installing Python environment and dependencies"

$setupPs1 = Join-Path $targetDir "SETUP.ps1"
if (-not (Test-Path $setupPs1)) {
    Write-Err "SETUP.ps1 not found — the repo clone may be incomplete."
    Write-Err "Expected at: $setupPs1"
    exit 1
}

Write-Host "  This will download ~2-3 GB of packages (PyTorch, transformers, etc.)"
Write-Host "  and may take 10-30 minutes depending on your internet speed."
Write-Host ""

& powershell -NoProfile -ExecutionPolicy Bypass -File $setupPs1 -NonInteractive

if ($LASTEXITCODE -ne 0) {
    Write-Warn "SETUP.ps1 exited with code $LASTEXITCODE — some components may not be installed."
    Write-Warn "Review the messages above and re-run SETUP.bat if needed."
} else {
    Write-Ok "Dependencies installed."
}


# ══════════════════════════════════════════════════════════════════
# STEP 5: Desktop shortcut + finish
# ══════════════════════════════════════════════════════════════════

Write-Step "STEP 5/5: Creating desktop shortcut"

if (-not $NoShortcut) {
    $runBat = Join-Path $targetDir "RUN.bat"
    if (Test-Path $runBat) {
        $logoJpg = Join-Path $targetDir "logo.jpg"
        $logoIco = Join-Path $targetDir "logo.ico"
        if (Test-Path $logoJpg) {
            try { Convert-JpgToIco -JpgPath $logoJpg -IcoPath $logoIco } catch {}
        }
        $scPath = New-DesktopShortcut -Target $runBat -WorkingDir $targetDir -Name "Multipurpose AI Assistant" -IconPath $logoIco
        Write-Ok "Desktop shortcut created: $scPath"
    } else {
        Write-Warn "RUN.bat not found at $runBat — skipping desktop shortcut."
    }
} else {
    Write-Ok "Skipped (disabled by -NoShortcut)."
}


# ══════════════════════════════════════════════════════════════════
# Done
# ══════════════════════════════════════════════════════════════════

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  $([char]0x2705) Installation complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  $([System.Char]::ConvertFromUtf32(0x1F4C1))  Location:    $targetDir"
if (-not $NoShortcut) {
    Write-Host "  $([System.Char]::ConvertFromUtf32(0x1F5A5))  Shortcut:    Desktop $([char]0x2192) Multipurpose AI Assistant"
}
Write-Host ""
Write-Host "  $([char]0x25B6)  To run:"
Write-Host "       - double-click RUN.bat in the folder above"
Write-Host "       - or click the desktop shortcut"
Write-Host ""
Write-Host "  $([System.Char]::ConvertFromUtf32(0x1F527))  Setup:       Open $([char]0x2699) Settings in the app to configure"
Write-Host "                your model provider and model assignments."
Write-Host ""

if (-not $NonInteractive) {
    $launch = Read-Host "  Launch the app now? (Y/n) "
    if ($launch -notmatch '^(n|no)') {
        $runBat = Join-Path $targetDir "RUN.bat"
        if (Test-Path $runBat) {
            Write-Host ""
            Write-Host "  Starting app..."
            Start-Process -FilePath $runBat -WorkingDirectory $targetDir -WindowStyle Normal
            Write-Host "  App launched in a new window. Close this installer when ready."
        }
    }
}

Write-Host ""
