param(
    [switch]$NonInteractive
)

$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
try { $Host.UI.RawUI.WindowTitle = "ជំនួយការ AI ពហុមុខងារ - ការដំឡើង" } catch {}

function Refresh-Path {
    $sys = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $usr = [System.Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$sys;$usr"
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " ការដំឡើងជំនួយការ AI ពហុមុខងារ ដោយ LocalAiLab - smolagents + ChromaDB + llama.cpp" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$ProgressFile = Join-Path $root "install_progress.txt"
$StatusFile   = Join-Path $root "install_status.txt"

function Write-InstallProgress([int]$Percent, [string]$Title, [string]$Detail) {
    if ($Detail) {
        Write-Host "[$Percent%] $Title - $Detail"
    } else {
        Write-Host "[$Percent%] $Title"
    }
    try {
        Write-FileUtf8NoBom $ProgressFile "$Percent|$Title|$Detail"
    } catch {}
}

function Set-InstallStatus([int]$Code) {
    try {
        [System.IO.File]::WriteAllText($StatusFile, "$Code", (New-Object System.Text.UTF8Encoding($false)))
    } catch {}
}

function Pause-Exit {
    # Every terminal exit point in this script (success and every failure
    # branch) calls this instead of a bare Read-Host. When the installer
    # GUI (installer.iss) launches this script hidden with -NonInteractive,
    # a bare Read-Host blocks forever on a console nobody can type into --
    # installer.iss's own polling loop only watches install_status.txt to
    # decide the run is "done" and does NOT terminate the process on a
    # successful exit (only on cancel/failure), so the real process tree
    # (cmd.exe -> SETUP.bat -> this script) was leaking as a permanently
    # hung, hidden orphan after every automated install. Skipping the
    # pause when $NonInteractive is set closes that leak; interactive
    # double-click runs (SETUP.bat with no args) keep the pause so the
    # window doesn't vanish before the user can read the final status.
    if (-not $NonInteractive) {
        Read-Host "ចុច Enter ដើម្បីបិទ"
    }
}

function Write-FileUtf8NoBom([string]$Path, [string]$Content) {
    [System.IO.File]::WriteAllText($Path, $Content, (New-Object System.Text.UTF8Encoding($false)))
}

function Invoke-PipRetry([string[]]$PipArgs, [int]$MaxAttempts = 2) {
    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        & $venvPython -m pip @PipArgs
        if ($LASTEXITCODE -eq 0) { return $true }
        if ($attempt -lt $MaxAttempts) {
            Write-Host "  [ព្យាយាមម្តងទៀត] pip បរាជ័យ (exit $LASTEXITCODE) - កំពុងព្យាយាមម្តងទៀត ($($attempt + 1)/$MaxAttempts)..." -ForegroundColor Yellow
            Start-Sleep -Seconds 5
        }
    }
    return $false
}

# Run a subprocess and capture its stdout/stderr WITHOUT deadlocking.
# Redirecting the child's streams to pipes while never reading them is a
# classic hang: once a pipe's buffer (~4 KB) fills, the child blocks
# forever writing to it and the parent then times out and gives up. This
# helper drains both streams asynchronously so the child never blocks,
# regardless of how much it writes.
function Invoke-CapturedProcess([string]$FileName, [string]$Arguments, [int]$TimeoutSec = 60) {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName               = $FileName
    $psi.Arguments              = $Arguments
    $psi.UseShellExecute        = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError  = $true
    $psi.CreateNoWindow         = $true

    $outLines = New-Object System.Collections.Generic.List[string]
    $errLines = New-Object System.Collections.Generic.List[string]

    try {
        $proc = [System.Diagnostics.Process]::Start($psi)
    } catch {
        return @{ TimedOut = $false; ExitCode = $null; Output = ""; Error = "Failed to start process: $_" }
    }

    $outEvt = $null
    $errEvt = $null
    try {
        $outEvt = Register-ObjectEvent -InputObject $proc -EventName OutputDataReceived -Action { if ($EventArgs.Data) { $Event.MessageData.Add($EventArgs.Data) } } -MessageData $outLines
        $errEvt = Register-ObjectEvent -InputObject $proc -EventName ErrorDataReceived  -Action { if ($EventArgs.Data) { $Event.MessageData.Add($EventArgs.Data) } } -MessageData $errLines
        $proc.BeginOutputReadLine()
        $proc.BeginErrorReadLine()
    } catch {}

    $finished = $proc.WaitForExit($TimeoutSec * 1000)
    if ($finished) {
        Start-Sleep -Milliseconds 200
    } else {
        try { $proc.Kill() } catch {}
    }

    if ($outEvt) { try { Unregister-Event -SourceIdentifier $outEvt.Name } catch {} }
    if ($errEvt) { try { Unregister-Event -SourceIdentifier $errEvt.Name } catch {} }

    return @{
        TimedOut = (-not $finished)
        ExitCode = if ($finished) { $proc.ExitCode } else { $null }
        Output   = ($outLines -join "`n")
        Error    = ($errLines -join "`n")
    }
}

$isElevated = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

# ── STEP 0: Check we are in the right folder & Path Length ─────────────────────
if (-not (Test-Path -LiteralPath (Join-Path $root "app.py"))) {
    Write-Host "[កំហុស] រកមិនឃើញ app.py ។ សូមដំណើរការស្គ្រីបនេះពីក្នុងថតឫសនៃកម្មវិធី (ថតដែលមាន app.py) ។" -ForegroundColor Red
    Set-InstallStatus 1
        Pause-Exit
        exit 1
}

# Warn about Windows MAX_PATH limit if the path is too long
if ($root.Length -gt 50) {
    Write-Host ""
    Write-Host "[ព្រមាន] ផ្លូវដំឡើងនេះវែងពេក ($($root.Length) តួអក្សរ) អាចបណ្តាលឱ្យការដំឡើងបរាជ័យ (ជាពិសេស PyTorch)" -ForegroundColor Yellow
    Write-Host "         ដោយសារដែនកំណត់ប្រវែងផ្លូវអតិបរមារបស់ Windows (MAX_PATH) ។" -ForegroundColor Yellow
    Write-Host "         ប្រសិនបើការដំឡើងបរាជ័យ សូមដំឡើងកម្មវិធីនៅផ្លូវខ្លីជាងនេះ (ឧទាហរណ៍ C:\LocalAiLab) ។" -ForegroundColor Yellow
    Write-Host ""
}

# ── STEP 1: Check / Install Python (requires 3.9+) ───────────────
Write-InstallProgress 5 "[1/8] កំពុងពិនិត្យមើលការដំឡើង Python..." "Verifying Python 3.9+ installation..."
$needPython = $false
$pyVer = $null

$pyCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pyCmd) {
    Write-Host "[ព្រមាន] រកមិនឃើញ Python នៅក្នុង PATH ។" -ForegroundColor Yellow
    $needPython = $true
} else {
    $verOut = (& python --version) 2>&1
    $pyVer = ($verOut -replace "Python\s+", "").Trim()
    Write-Host " បានរកឃើញ Python $pyVer"
    $parts = $pyVer.Split(".")
    $major = [int]$parts[0]
    $minor = [int]$parts[1]

    if ($major -eq 2) {
        Write-Host "[ព្រមាន] មិនគាំទ្រ Python 2 ទេ (បានរកឃើញ $pyVer) ។" -ForegroundColor Yellow
        Write-Host "        Python 3.9 ឬខ្ពស់ជាងនេះ ត្រូវបានទាមទារ។"
        $needPython = $true
    } elseif ($major -eq 3 -and $minor -lt 9) {
        Write-Host "[ព្រមាន] Python $pyVer ចាស់ពេក។ ត្រូវការយ៉ាងតិច Python 3.9" -ForegroundColor Yellow
        Write-Host "        នឹងដំឡើង Python 3.11 ជាមួយកំណែបច្ចុប្បន្នរបស់អ្នក។"
        $needPython = $true
    } else {
        Write-Host "[OK] Python $pyVer បំពេញតម្រូវការអប្បបរមា (3.9+) ។" -ForegroundColor Green
    }
}

if ($needPython) {
    Write-Host ""
    Write-InstallProgress 10 "[1/8] កំពុងទាញយក Python 3.11.9..." "Downloading Python 3.11.9 installer..."
    $installerPath = Join-Path $env:TEMP "python_installer.exe"
    try {
        Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe" -OutFile $installerPath -UseBasicParsing
    } catch {
        Write-Host ""
        Write-Host "[កំហុស] ការទាញយកបានបរាជ័យ។ សូមពិនិត្យការតភ្ជាប់អ៊ីនធឺណិតរបស់អ្នក ហើយសាកល្បងម្តងទៀត។" -ForegroundColor Red
        Write-Host "        ឬដំឡើង Python 3.11 ដោយផ្ទាល់ពី: https://www.python.org/downloads/"
        Set-InstallStatus 1
        Pause-Exit
        exit 1
    }

    Write-InstallProgress 15 "[1/8] កំពុងដំឡើង Python 3.11.9..." "Installing Python 3.11.9 (silent)..."
    $installAllUsers = if ($isElevated) { "1" } else { "0" }
    $installArgs = @("/quiet", "InstallAllUsers=$installAllUsers", "PrependPath=1", "Include_pip=1", "Include_launcher=1", "Include_test=0")
    $proc = Start-Process -FilePath $installerPath -ArgumentList $installArgs -Wait -PassThru
    if ($proc.ExitCode -ne 0) {
        Write-Host "[កំហុស] ការដំឡើង Python បានបរាជ័យ (exit code $($proc.ExitCode)) ។" -ForegroundColor Red
        Write-Host "        សូមដំឡើងដោយផ្ទាល់ពី: https://www.python.org/downloads/"
        Set-InstallStatus 1
        Pause-Exit
        exit 1
    }

    Refresh-Path
    $pyCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pyCmd) {
        Write-Host ""
        Write-Host "[កំហុស] Python ត្រូវបានដំឡើងរួចហើយ ប៉ុន្តែនៅតែរកមិនឃើញនៅក្នុង PATH ។" -ForegroundColor Red
        Write-Host "        ករណីនេះកើតឡើងនៅពេលការផ្លាស់ប្តូរ PATH ត្រូវការសម័យបញ្ជាថ្មី។"
        Write-Host ""
        Write-Host "        សូម បិទ បង្អួចនេះ បើក PowerShell ថ្មី ហើយ"
        Write-Host "        ដំណើរការ SETUP.bat ម្តងទៀត។"
        Set-InstallStatus 1
        Pause-Exit
        exit 1
    }
    $pyVer = ((& python --version) 2>&1) -replace "Python\s+", ""
    Write-Host "[OK] Python $pyVer បានដំឡើងដោយជោគជ័យ។" -ForegroundColor Green
}
Write-InstallProgress 20 "[1/8] Python បំពេញតម្រូវការ" "Python $pyVer is ready"

# Final sanity — pip
& python -m pip --version *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ព្រមាន] រកមិនឃើញ pip - កំពុងព្យាយាមដំឡើងវា..." -ForegroundColor Yellow
    & python -m ensurepip --upgrade
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[កំហុស] មិនអាចដំឡើង pip បានទេ។ សូមដំណើរការ:  python -m ensurepip --upgrade" -ForegroundColor Red
        Set-InstallStatus 1
        Pause-Exit
        exit 1
    }
}
Write-Host "[OK] pip អាចប្រើប្រាស់បាន។" -ForegroundColor Green

# ── STEP 2: Create virtual environment ────────────────────────────
Write-Host ""
Write-InstallProgress 22 "[2/8] កំពុងបង្កើត virtual environment (.venv)..." "Setting up .venv folder..."
$venvPython = Join-Path $root ".venv\Scripts\python.exe"
$venvDir    = Join-Path $root ".venv"

# A previous run that was interrupted (killed installer, crashed setup,
# disk full mid-copy, etc.) can leave behind a ".venv" folder where
# python.exe exists but the venv itself is incomplete — no pip, a
# truncated site-packages, or a missing activation script. Simply
# checking "does python.exe exist" (the old check) treats that broken
# venv as valid, skips recreation, and then every later step (pip
# upgrade, requirements install, PyTorch install) silently runs against
# a broken interpreter — producing confusing failures anywhere from
# Step 3 onward instead of a clear "venv is broken" message right here.
# A real smoke test (actually launching the interpreter and confirming
# pip is importable) catches this up front instead.
$venvOk = $false
if (Test-Path -LiteralPath $venvPython) {
    Write-Host " [*] .venv រកឃើញ — កំពុងផ្ទៀងផ្ទាត់ថាវានៅដំណើរការត្រឹមត្រូវ..." -ForegroundColor Cyan
    & $venvPython -c "import sys, pip" *> $null
    if ($LASTEXITCODE -eq 0) {
        $venvOk = $true
    } else {
        Write-Host " [ព្រមាន] .venv មានស្រាប់ ប៉ុន្តែហាក់ដូចជាខូច/មិនពេញលេញ (python ដំណើរការមិនបាន ឬ pip បាត់)។" -ForegroundColor Yellow
    }
}

if ($venvOk) {
    Write-Host "[OK] .venv មានរួចហើយ និងដំណើរការត្រឹមត្រូវ — កំពុងរំលងការបង្កើត។" -ForegroundColor Green
} else {
    if (Test-Path -LiteralPath $venvDir) {
        Write-InstallProgress 23 "[2/8] កំពុងលុប .venv ដែលខូច..." "Removing broken/incomplete .venv before recreating..."
        Write-Host " [*] កំពុងលុបថត .venv ចាស់ (មិនពេញលេញ) ជាមុនសិន..." -ForegroundColor Yellow
        try {
            Remove-Item -LiteralPath $venvDir -Recurse -Force -ErrorAction Stop
        } catch {
            Write-Host "[កំហុស] មិនអាចលុបថត .venv ចាស់បានទេ: $($_.Exception.Message)" -ForegroundColor Red
            Write-Host "        សូមបិទកម្មវិធីណាមួយដែលអាចកំពុងប្រើឯកសារក្នុងថតនោះ (ឧ. Explorer, terminal) ហើយសាកល្បងម្តងទៀត," -ForegroundColor Red
            Write-Host "        ឬលុប '$venvDir' ដោយដៃ ហើយដំណើរការ SETUP.bat ម្តងទៀត។" -ForegroundColor Red
            Set-InstallStatus 1
            Pause-Exit
            exit 1
        }
    }

    & python -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[កំហុស] បរាជ័យក្នុងការបង្កើត virtual environment ។" -ForegroundColor Red
        Set-InstallStatus 1
        Pause-Exit
        exit 1
    }

    # Confirm the FRESH venv is actually usable too — a venv creation
    # that exits 0 but still produces a broken interpreter (e.g. an
    # interrupted disk write, antivirus quarantining a DLL mid-copy) is
    # rare but not impossible, and failing loudly here is far more useful
    # than the same failure resurfacing three steps later during
    # requirements install.
    & $venvPython -c "import sys, pip" *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[កំហុស] Virtual environment ត្រូវបានបង្កើត ប៉ុន្តែហាក់ដូចជាមិនដំណើរការត្រឹមត្រូវទេ (python/pip ប្រើមិនបាន)។" -ForegroundColor Red
        Write-Host "        សូមព្យាយាមលុប '$venvDir' ដោយដៃ ហើយដំណើរការ SETUP.bat ម្តងទៀត។" -ForegroundColor Red
        Set-InstallStatus 1
        Pause-Exit
        exit 1
    }

    Write-Host "[OK] Virtual environment ត្រូវបានបង្កើត និងផ្ទៀងផ្ទាត់ថាដំណើរការត្រឹមត្រូវ។" -ForegroundColor Green
}
Write-InstallProgress 25 "[2/8] Virtual environment រួចរាល់" ".venv created/verified and ready"

$activateScript = Join-Path $root ".venv\Scripts\Activate.ps1"
try {
    & $activateScript
    Write-Host "[OK] Virtual environment ត្រូវបានធ្វើឱ្យសកម្ម។" -ForegroundColor Green
} catch {
    Write-Host "[ព្រមាន] មិនអាចធ្វើឱ្យ venv សកម្មបានទេ - នឹងប្រើ .venv\Scripts\python.exe ដោយផ្ទាល់។" -ForegroundColor Yellow
}

# ── STEP 3: Upgrade pip ────────────────────────────────────────────
Write-Host ""
Write-InstallProgress 27 "[3/8] កំពុងធ្វើបច្ចុប្បន្នភាព pip..." "Upgrading pip package manager..."
& $venvPython -m pip install --upgrade pip
Write-Host "[OK] pip ទាន់សម័យហើយ។" -ForegroundColor Green
Write-InstallProgress 30 "[3/8] pip ទាន់សម័យហើយ" "pip upgraded successfully"

# ── STEP 4: Detect GPU — NVIDIA / AMD ROCm / CPU ──────────────────
Write-Host ""
Write-InstallProgress 32 "[4/8] កំពុងរកឃើញ GPU..." "Detecting NVIDIA / AMD / CPU hardware..."
$gpuBrand = "none"
$cudaVersion = "cpu"
$torchIndex = "https://download.pytorch.org/whl/cpu"
$cudaCandidates = @()

$nvidiaSmi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
$gpuDone = $false
# Compute capability of GPU 0 (e.g. "6.1" for a Pascal-class card like an
# MX230, "8.6" for an RTX 30-series, etc). Queried directly from
# nvidia-smi — works without torch installed yet — used purely for an
# informative log line here; the REAL compatibility decision is made by
# actually running a CUDA kernel after installing torch (see the
# Test-TorchCudaReal smoke test in STEP 5 below), since PyTorch's
# supported-architecture list changes between releases and hardcoding a
# "CC >= X is fine" cutoff here would silently go stale.
$computeCap = $null

if ($nvidiaSmi) {
    $smiOut = & nvidia-smi 2>$null
    if ($LASTEXITCODE -eq 0) {
        $gpuBrand = "nvidia"
        # Newer NVIDIA drivers (r580+) changed nvidia-smi's header: instead
        # of "CUDA Version: 13.3" it now prints "CUDA UMD Version: 13.3".
        # Match BOTH spellings so the driver tier is parsed (and logged)
        # instead of silently falling through to the "unknown" default.
        $cudaLine = $smiOut | Select-String "CUDA (UMD )?Version"
        $rawCuda = $null
        if ($cudaLine) {
            if ($cudaLine.Line -match "CUDA (?:UMD )?Version:\s*([0-9]+\.[0-9]+)") {
                $rawCuda = $matches[1]
            }
        }
        try {
            $ccOut = & nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>$null
            if ($LASTEXITCODE -eq 0 -and $ccOut) {
                $computeCap = ($ccOut -split "`r?`n")[0].Trim()
            }
        } catch {}

        $gpuNameOut = $null
        try {
            $gpuNameOut = (& nvidia-smi --query-gpu=name --format=csv,noheader 2>$null | Select-Object -First 1)
        } catch {}

        Write-Host "[OK] រកឃើញ GPU NVIDIA: $gpuNameOut | កំណែ CUDA Driver: $rawCuda | Compute Capability: $computeCap" -ForegroundColor Green

        # Driver CUDA version -> PyTorch wheel tier. NVIDIA drivers are
        # backward-compatible with older CUDA toolkits, so a driver
        # reporting a NEWER major CUDA version than any known PyTorch
        # wheel tier (e.g. CUDA 13.x, as shipped by newer drivers even on
        # old GPUs) is intentionally mapped to the newest known-good tier
        # rather than treated as an "unknown version" error — the driver
        # being new does NOT mean the GPU itself is new/supported; that's
        # exactly what the real-kernel smoke test after install (STEP 5
        # below) exists to verify, since guessing from the driver version
        # alone (as this script previously did) is exactly what let an
        # old Pascal-class GPU silently get a "cu128 is probably fine"
        # verdict that then crashed on first real use.
        # Build an ordered list of candidate PyTorch wheel tiers. The
        # FIRST entry is the best match for this driver; the rest are
        # automatic fallbacks walked by STEP 5/5b below. Each tier also
        # carries a DIFFERENT torch version (e.g. cu118 tops out at torch
        # 2.7.1, which still ships kernels for older GPUs that torch 2.11
        # dropped), so stepping down the list is a real second chance, not
        # just a retry. CPU is only used if EVERY tier fails. NVIDIA
        # drivers are backward-compatible with older CUDA toolkits, so a
        # driver reporting a NEWER CUDA version than any known tier just
        # starts at the newest tier with Windows wheels.
        $cudaCandidates = @()
        if ($rawCuda) {
            $cmajor = [int]($rawCuda.Split(".")[0])
            $cfull = $rawCuda
            if ($cmajor -eq 11) {
                $cudaCandidates = @("cu118")
            } elseif ($cmajor -eq 12) {
                if ($cfull -match "^12\.(8|9)") {
                    $cudaCandidates = @("cu128", "cu126", "cu124", "cu118")
                } elseif ($cfull -match "^12\.(6|7)") {
                    $cudaCandidates = @("cu126", "cu124", "cu118")
                } elseif ($cfull -match "^12\.(4|5)") {
                    $cudaCandidates = @("cu124", "cu121", "cu118")
                } elseif ($cfull -match "^12\.(1|2|3)") {
                    $cudaCandidates = @("cu121", "cu118")
                } else {
                    $cudaCandidates = @("cu118")
                }
            } elseif ($cmajor -ge 13) {
                Write-Host "[ចំណាំ] Driver CUDA version ($rawCuda) ថ្មីជាង wheel tier ដែលស្គាល់ - កំពុងចាប់ផ្តើមពី tier ដែលមាន wheel។ driver ថ្មីមិនមានន័យថា GPU ត្រូវបានគាំទ្រដោយ PyTorch ថ្មីៗនោះទេ - ការសាកល្បងផ្ទុកគំរូខាងក្រោមនឹងផ្ទៀងផ្ទាត់រឿងនេះឱ្យប្រាកដ។" -ForegroundColor Cyan
                $cudaCandidates = @("cu128", "cu130", "cu126", "cu118")
            } else {
                $cudaCandidates = @("cu118")
            }
        } else {
            # nvidia-smi worked but the "CUDA Version" line didn't parse —
            # assume a modern driver and start at the proven RTX-tier.
            $cudaCandidates = @("cu128", "cu130", "cu126", "cu118")
        }
        $cudaVersion = $cudaCandidates[0]
        $torchIndex = "https://download.pytorch.org/whl/$cudaVersion"
        Write-Host "[OK] នឹងដំឡើង PyTorch សម្រាប់ CUDA $cudaVersion (tier fallbacks: $($cudaCandidates -join ', '))" -ForegroundColor Green
        $gpuDone = $true
    }
}

if (-not $gpuDone) {
    $vc = $null
    try {
        $vc = Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue
    } catch {}
    $vcNames = if ($vc) { $vc.Name -join ";" } else { "" }

    if ($vcNames -match "Radeon|AMD") {
        # AMD GPU present. On Windows, AMD publishes torch wheels ONLY on
        # its own repo (repo.radeon.com) — download.pytorch.org has no
        # Windows ROCm wheels. They require Python 3.12 and the pip
        # ROCm SDK; SETUP step 5 handles that (auto-installing Python
        # 3.12 + recreating .venv if needed). No separate ROCm toolkit
        # install is needed anymore — the SDK ships as pip wheels now.
        $gpuBrand = "amd_rocm"
        Write-Host "[OK] រកឃើញ GPU AMD (Radeon / Ryzen AI) ។" -ForegroundColor Green
        $cudaVersion = "rocm7.2.1"
        $torchIndex = "https://repo.radeon.com/rocm/windows/rocm-rel-7.2.1"
        $cudaCandidates = @("rocm7.2.1")
        Write-Host "[OK] នឹងដំឡើង PyTorch សម្រាប់ ROCm (wheel: $cudaVersion) ពី repo.radeon.com" -ForegroundColor Green
        Write-Host "[ចំណាំ] តម្រូវឲ្យមាន AMD Adrenalin driver 26.2.2+ និង Python 3.12 (ដំឡើងស្វ័យប្រវត្តិបើចាំបាច់)។ ទាញយកសរុប ~2.2 GB ។" -ForegroundColor Yellow
        $gpuDone = $true
    } elseif ($vcNames -match "Intel") {
        # Intel GPU present (Arc / Iris Xe / UHD). Intel XPU wheels ship
        # on download.pytorch.org. Only reached when no NVIDIA (nvidia-smi
        # failed above) and no AMD GPU — i.e. an Intel-only machine.
        $gpuBrand = "intel_xpu"
        Write-Host "[OK] រកឃើញ GPU Intel (Arc / Iris Xe / UHD) ។" -ForegroundColor Green
        $cudaVersion = "xpu"
        $torchIndex = "https://download.pytorch.org/whl/xpu"
        $cudaCandidates = @("xpu")
        Write-Host "[OK] នឹងដំឡើង PyTorch សម្រាប់ Intel XPU (wheel: $cudaVersion)" -ForegroundColor Green
        Write-Host "[ចំណាំ] តម្រូវឲ្យមាន Intel GPU driver ចុងក្រោយ។" -ForegroundColor Yellow
        $gpuDone = $true
    } elseif ($vcNames -match "NVIDIA|GeForce|RTX|GTX|Quadro|Titan|NVS") {
        # NVIDIA card present but nvidia-smi couldn't be run/parsed (e.g.
        # it's not on PATH in this session, or it failed mid-run). WITHOUT
        # this branch the old code fell into the final "no GPU detected"
        # catch-all and silently installed CPU PyTorch on a perfectly good
        # NVIDIA machine — exactly the trap that bit the v0.0.3 installs
        # (nvidia-smi detection failing during the hidden installer run
        # while the driver was fine). Fall back to the proven RTX-tier
        # candidates; the real-kernel smoke test in Step 5b still verifies
        # the choice, so this is safe for genuinely old/unsupported cards.
        $gpuBrand = "nvidia"
        $cudaVersion = "cu128"
        $cudaCandidates = @("cu128", "cu130", "cu126", "cu118")
        $torchIndex = "https://download.pytorch.org/whl/$cudaVersion"
        Write-Host "[OK] រកឃើញ GPU NVIDIA ($vcNames) តាមរយៈ Windows device list (nvidia-smi មិនអាចប្រើបាន) — កំពុងព្យាយាម CUDA $cudaVersion ។" -ForegroundColor Green
        $gpuDone = $true
    } else {
        Write-Host "[ព្រមាន] រកមិនឃើញ GPU ទេ (គ្មាន nvidia-smi ឬ GPU NVIDIA/AMD/Intel ក្នុងបញ្ជីឧបករណ៍) ។" -ForegroundColor Yellow
        Write-Host "        កំពុងដំឡើង PyTorch សម្រាប់ CPU ។"
        $gpuBrand = "cpu"
        $cudaVersion = "cpu"
        $torchIndex = "https://download.pytorch.org/whl/cpu"
        $cudaCandidates = @()
    }
}

# ── STEP 5 + 5b: Install PyTorch with automatic tier fallback ───────
# torch is pinned to <2.12 ON PURPOSE: colpali_engine (pulled in by
# requirements.txt via `byaldi`) requires `torch<2.12.0,>=2.2.0`. If we
# installed the newest torch here (2.13.x+), the Step 6 requirements
# install would then DOWNGRADE torch to 2.11.x from the default index —
# re-downloading a second multi-GB wheel and silently replacing this
# GPU-matched build with a plain/CPU one. Pinning the same upper bound
# here keeps the GPU/CPU wheel selected in this step consistent with what
# Step 6 will accept, so no second download and no GPU-torch wipe.
#
# `pip install` succeeding — and even torch.cuda.is_available() returning
# True — do NOT guarantee this PyTorch build ships compiled kernels for
# THIS GPU's compute capability. PyTorch wheels only include kernels for
# a fixed list of architectures, and older cards (Pascal/sm_6x such as
# the GeForce MX series, Maxwell/sm_5x) have been dropped from recent
# stable releases; the model then LOADS onto the device with no error and
# only crashes when a real kernel launches (tie_weights(), ...) with a
# confusing "CUDA error: no kernel image is available". So we launch a
# REAL kernel (mirroring the Test-LlamaCppRealModelLoad pattern) and, on
# failure, move to the next candidate tier (each tier also carries a
# DIFFERENT torch version — e.g. cu118 tops out at torch 2.7.1, which
# still ships kernels for GPUs that torch 2.11 dropped) before ever
# giving up on GPU. CPU is used only after EVERY tier fails, so no
# user is ever left with a hard-failed install for a reachable GPU.
# The same real-kernel test runs for AMD ROCm (which exposes the CUDA API
# surface, so device 'cuda') and for Intel XPU (torch.xpu), so every
# backend shares the "only trust a real kernel launch" guarantee.
function Test-TorchKernelReal([string]$Device = "cuda", [int]$TimeoutSec = 90) {
    $sync = if ($Device -eq "xpu") { "torch.xpu.synchronize()" } else { "torch.cuda.synchronize()" }
    $code = "import torch; x = torch.randn(64, 64, device='$Device'); y = x @ x; $sync; print('OK')"
    $last = $null
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        $last = Invoke-CapturedProcess -FileName $venvPython -Arguments "-c `"$code`"" -TimeoutSec $TimeoutSec
        if (-not $last.TimedOut -and $last.ExitCode -eq 0) { return $true }
        if ($attempt -lt 3) {
            Write-Host "  [ព្យាយាមម្តងទៀត] GPU kernel test បរាជ័យ ($attempt/3) - កំពុងព្យាយាមម្តងទៀត..." -ForegroundColor Yellow
            Start-Sleep -Seconds 5
        }
    }
    try {
        $log = @(
            "Torch $Device kernel smoke test FAILED after 3 attempts.",
            ("TimedOut: {0} | ExitCode: {1}" -f $last.TimedOut, $last.ExitCode),
            "--- STDOUT ---",
            $last.Output,
            "--- STDERR ---",
            $last.Error
        ) -join "`r`n"
        [System.IO.File]::WriteAllText((Join-Path $root "install_torch_smoke.log"), $log)
    } catch {}
    return $false
}

function Test-VenvPythonVersion([string]$VerRegex) {
    $ver = (& $venvPython --version 2>&1 | Select-Object -First 1)
    return ($ver -match $VerRegex)
}

# AMD's Windows ROCm wheels (repo.radeon.com) are Python 3.12 ONLY. If
# the current venv isn't 3.12, silently install Python 3.12.x and recreate
# the venv with it, then re-upgrade pip. Returns $true if the venv is 3.12
# afterwards, $false otherwise (the caller falls back to CPU).
function Ensure-VenvPython312 {
    if (Test-VenvPythonVersion "3\.12") { return $true }
    Write-Host " [*] AMD ROCm តម្រូវឲ្យប្រើ Python 3.12 - កំពុងទាញយក/ដំឡើង Python 3.12..." -ForegroundColor Cyan
    $installerPath = Join-Path $env:TEMP "python_installer.exe"
    try {
        Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe" -OutFile $installerPath -UseBasicParsing
    } catch {
        Write-Host "[ព្រមាន] ការទាញយក Python 3.12 បានបរាជ័យ។" -ForegroundColor Yellow
        return $false
    }
    $installAllUsers = if ($isElevated) { "1" } else { "0" }
    $proc = Start-Process -FilePath $installerPath -ArgumentList @("/quiet", "InstallAllUsers=$installAllUsers", "PrependPath=1", "Include_pip=1", "Include_launcher=1", "Include_test=0") -Wait -PassThru
    if ($proc.ExitCode -ne 0) {
        Write-Host "[ព្រមាន] ការដំឡើង Python 3.12 បានបរាជ័យ (exit $($proc.ExitCode))។" -ForegroundColor Yellow
        return $false
    }
    Refresh-Path
    $py312exe = $null
    $p = Get-Command python -ErrorAction SilentlyContinue
    if ($p) {
        $pv = (& python --version 2>&1 | Select-Object -First 1)
        if ($pv -match "3\.12") { $py312exe = (& python -c "import sys; print(sys.executable)").Trim() }
    }
    if (-not $py312exe) {
        $pyL = Get-Command py -ErrorAction SilentlyContinue
        if ($pyL) {
            $py312v = (& py -3.12 --version 2>&1 | Select-Object -First 1)
            if ($py312v -match "3\.12") { $py312exe = (& py -3.12 -c "import sys; print(sys.executable)").Trim() }
        }
    }
    if (-not $py312exe) {
        Write-Host "[ព្រមាន] មិនអាចកំណត់ទីតាំង Python 3.12 បានទេ។" -ForegroundColor Yellow
        return $false
    }
    if (Test-Path -LiteralPath $venvDir) {
        try { Remove-Item -LiteralPath $venvDir -Recurse -Force -ErrorAction Stop } catch {
            Write-Host "[ព្រមាន] មិនអាចលុប .venv ចាស់ដើម្បីបង្កើតឡើងវិញជាមួយ Python 3.12 បានទេ។" -ForegroundColor Yellow
            return $false
        }
    }
    & $py312exe -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ព្រមាន] ការបង្កើត .venv ជាមួយ Python 3.12 បានបរាជ័យ។" -ForegroundColor Yellow
        return $false
    }
    Write-Host "[OK] .venv ត្រូវបានបង្កើតឡើងវិញជាមួយ Python 3.12 ដោយជោគជ័យ។" -ForegroundColor Green
    & $venvPython -m pip install --upgrade pip
    return $true
}

Write-Host ""
$torchOk = $false
$torchTried = @()
$cpuIndex = "https://download.pytorch.org/whl/cpu"

if ($gpuBrand -ne "cpu") {
    # If the venv already holds a CPU/plain torch build (e.g. from an
    # earlier run that fell back to CPU), pip would consider the pinned
    # torch "already satisfied" and never upgrade to a GPU wheel —
    # silently keeping the machine on CPU forever. Force a clean
    # reinstall so re-running SETUP.bat actually repairs it.
    $curTorch = (& $venvPython -c "import torch; print(torch.__version__)" 2>$null)
    if ($curTorch -and $curTorch -notmatch "\+(cu|rocm|xpu)") {
        Write-Host "[ចំណាំ] បានរកឃើញ PyTorch $curTorch (CPU build) - កំពុងដកចេញ ហើយដំឡើង build សម្រាប់ GPU ឡើងវិញ..." -ForegroundColor Yellow
        & $venvPython -m pip uninstall torch torchvision torchaudio -y 2>$null
    }
}

if ($gpuBrand -eq "amd_rocm") {
    # ── AMD ROCm (Windows): pip-installed ROCm SDK + AMD torch wheels ──
    # AMD publishes Windows torch wheels ONLY on repo.radeon.com (the
    # download.pytorch.org ROCm tiers have no Windows wheels). Per AMD's
    # docs the ROCm SDK wheels must be installed first; torch/torchvision/
    # torchaudio then install from direct URLs. Requires Python 3.12 and
    # an AMD Adrenalin 26.2.2+ driver. Total download ~2.2 GB.
    $rocBase = "https://repo.radeon.com/rocm/windows/rocm-rel-7.2.1"
    if (Ensure-VenvPython312) {
        Write-Host ""
        Write-InstallProgress 40 "[5/8] កំពុងដំឡើង ROCm SDK + PyTorch (AMD)..." "Downloading AMD ROCm SDK (~1.4 GB) + torch wheels (~2.2 GB total)..."
        Write-Host "      អាចចំណាយពេលច្រើននាទី (download ធំ)..."
        $torchTried += "rocm7.2.1"
        $sdkOk = Invoke-PipRetry @("install", "--no-cache-dir", "$rocBase/rocm_sdk_core-7.2.1-py3-none-win_amd64.whl", "$rocBase/rocm_sdk_devel-7.2.1-py3-none-win_amd64.whl", "$rocBase/rocm_sdk_libraries_custom-7.2.1-py3-none-win_amd64.whl", "$rocBase/rocm-7.2.1.tar.gz") 3
        if ($sdkOk) {
            if (Invoke-PipRetry @("install", "--no-cache-dir", "$rocBase/torch-2.9.1%2Brocm7.2.1-cp312-cp312-win_amd64.whl", "$rocBase/torchaudio-2.9.1%2Brocm7.2.1-cp312-cp312-win_amd64.whl", "$rocBase/torchvision-0.24.1%2Brocm7.2.1-cp312-cp312-win_amd64.whl") 3) {
                Write-Host ""
                Write-InstallProgress 62 "[5b/8] កំពុងផ្ទៀងផ្ទាត់ GPU kernel (rocm7.2.1)..." "Executing GPU smoke test kernel..."
                # ROCm torch exposes the CUDA API surface, so device 'cuda' is correct here.
                if (Test-TorchKernelReal -Device cuda) {
                    $torchOk = $true
                    $cudaVersion = "rocm7.2.1"
                    $torchIndex = $rocBase
                    Write-Host "[OK] GPU kernel test ជោគជ័យ (rocm7.2.1) — PyTorch នឹងប្រើ AMD GPU របស់អ្នកបាន។" -ForegroundColor Green
                } else {
                    Write-Host "[ព្រមាន] wheel rocm7.2.1 ដំឡើងបាន ប៉ុន្តែ GPU kernel test បរាជ័យ។ តម្រូវឲ្យមាន AMD Adrenalin driver 26.2.2+ ។" -ForegroundColor Yellow
                }
            } else {
                Write-Host "[ព្រមាន] ការដំឡើង AMD torch wheels បានបរាជ័យ។" -ForegroundColor Yellow
            }
        } else {
            Write-Host "[ព្រមាន] ការដំឡើង ROCm SDK wheels បានបរាជ័យ។" -ForegroundColor Yellow
        }
    } else {
        Write-Host "[ព្រមាន] AMD ROCm លើ Windows តម្រូវឲ្យប្រើ Python 3.12 - មិនអាចដំឡើង GPU build បានទេ កំពុងប្រើ CPU ជំនួសវិញ។" -ForegroundColor Yellow
    }
} elseif ($gpuBrand -eq "intel_xpu") {
    # ── Intel XPU ──────────────────────────────────────────────────
    Write-Host ""
    # XPU wheels need Python >= 3.10; if the venv is older, upgrade to 3.12.
    if (-not (Test-VenvPythonVersion "3\.1\d")) {
        Write-Host "[ចំណាំ] Intel XPU ត្រូវការ Python 3.10+ - កំពុងដំឡើង Python 3.12..." -ForegroundColor Yellow
        $null = Ensure-VenvPython312
    }
    Write-InstallProgress 40 "[5/8] កំពុងដំឡើង PyTorch (Intel XPU)..." "Downloading PyTorch XPU wheels (~2-3 GB)..."
    Write-Host "      អាចចំណាយពេលច្រើននាទី (torch មានទំហំប្រហែល ២-៣ GB)..."
    $torchTried += "xpu"
    # Pin exact versions: the XPU release index had a known outage
    # (pytorch/pytorch#185608) where intel-cmplr-lib-rt==2025.3.2 went
    # missing and pip silently fell back to an old torch 2.9.1 build.
    if (Invoke-PipRetry @("install", "torch==2.11.0", "torchvision==0.26.0", "torchaudio==2.11.0", "--index-url", "https://download.pytorch.org/whl/xpu", "--timeout", "120") 3) {
        Write-Host ""
        Write-InstallProgress 62 "[5b/8] កំពុងផ្ទៀងផ្ទាត់ GPU kernel (xpu)..." "Executing GPU smoke test kernel..."
        if (Test-TorchKernelReal -Device xpu) {
            $torchOk = $true
            $cudaVersion = "xpu"
            $torchIndex = "https://download.pytorch.org/whl/xpu"
            Write-Host "[OK] GPU kernel test ជោគជ័យ (xpu) — PyTorch នឹងប្រើ Intel GPU របស់អ្នកបាន។" -ForegroundColor Green
        } else {
            Write-Host "[ព្រមាន] wheel xpu ដំឡើងបាន ប៉ុន្តែ GPU kernel test បរាជ័យ។ តម្រូវឲ្យមាន Intel GPU driver ចុងក្រោយ។" -ForegroundColor Yellow
            & $venvPython -m pip uninstall torch torchvision torchaudio -y 2>$null
        }
    } else {
        Write-Host "[ព្រមាន] wheel xpu មិនអាចដំឡើងបានទេ។" -ForegroundColor Yellow
    }
} elseif ($cudaVersion -ne "cpu") {
    # ── NVIDIA: ordered tier list with automatic fallback ─────────
    foreach ($tier in $cudaCandidates) {
        $tierIndex = "https://download.pytorch.org/whl/$tier"
        $torchTried += $tier
        Write-Host ""
        Write-InstallProgress 40 "[5/8] កំពុងដំឡើង PyTorch ($tier)..." "Downloading PyTorch wheels for $tier (~2-3 GB)..."
        Write-Host "      អាចចំណាយពេលច្រើននាទី (torch មានទំហំប្រហែល ២-៣ GB)..."

        if (Invoke-PipRetry @("install", "torch<2.12", "torchvision", "torchaudio", "--index-url", $tierIndex, "--timeout", "120") 3) {
            # Step 5b: real-kernel smoke test on this tier
            Write-Host ""
            Write-InstallProgress 62 "[5b/8] កំពុងផ្ទៀងផ្ទាត់ GPU kernel ($tier)..." "Executing GPU smoke test kernel..."
            if (Test-TorchKernelReal -Device cuda) {
                $torchOk = $true
                $cudaVersion = $tier
                $torchIndex = $tierIndex
                Write-Host "[OK] GPU kernel test ជោគជ័យ ($tier) — PyTorch នឹងប្រើ GPU របស់អ្នកបាន។" -ForegroundColor Green
                break
            }
            Write-Host "[ព្រមាន] wheel $tier ដំឡើងបាន ប៉ុន្តែ GPU kernel test បរាជ័យ (Compute Capability: $computeCap)។ កំពុងព្យាយាម tier បន្ទាប់..." -ForegroundColor Yellow
            & $venvPython -m pip uninstall torch torchvision torchaudio -y 2>$null
        } else {
            Write-Host "[ព្រមាន] tier $tier មិនអាចដំឡើងបានទេ។ កំពុងព្យាយាម tier បន្ទាប់..." -ForegroundColor Yellow
        }
    }
}

# ── STEP 5c: CPU fallback (no GPU detected, or every GPU tier failed) ──
if (-not $torchOk) {
    Write-Host ""
    Write-InstallProgress 40 "[5/8] កំពុងដំឡើង PyTorch (CPU-only)..." "Downloading PyTorch CPU wheels..."
    if (Invoke-PipRetry @("install", "torch<2.12", "torchvision", "torchaudio", "--index-url", $cpuIndex, "--timeout", "120") 3) {
        $torchOk = $true
        $cudaVersion = "cpu"
        $torchIndex = $cpuIndex
        if ($gpuBrand -ne "cpu") {
            Write-Host "[ព្រមាន] មិនអាចប្រើ GPU បានទេ (tier បានសាកល្បង: $($torchTried -join ', ')) - កំពុងប្រើ CPU PyTorch ជំនួសវិញ។" -ForegroundColor Yellow
        } else {
            Write-Host "[OK] PyTorch (CPU-only) ត្រូវបានដំឡើង។" -ForegroundColor Green
        }
    }
}

if (-not $torchOk) {
    Write-Host "[កំហុស] ការដំឡើង PyTorch បានបរាជ័យទាំង GPU និង CPU wheel។ សូមពិនិត្យការតភ្ជាប់អ៊ីនធឺណិត ហើយដំណើរការ SETUP.bat ម្តងទៀត។" -ForegroundColor Red
    Set-InstallStatus 1
    Pause-Exit
    exit 1
}

Write-Host "[OK] PyTorch ត្រូវបានដំឡើង ($cudaVersion) ។" -ForegroundColor Green
Write-InstallProgress 60 "[5/8] PyTorch ត្រូវបានដំឡើង" "PyTorch ($cudaVersion) installed successfully"

# ── STEP 6: Notice about llama-cpp-python (GGUF backend) ──────────
Write-Host ""
Write-Host "[6/8] ចំណាំអំពីការគាំទ្រម៉ូដែល GGUF (llama-cpp-python)..."
Write-Host ""
Write-Host " ------------------------------------------------------------------" -ForegroundColor Cyan
Write-Host "  ការដំឡើងនេះមិនរួមបញ្ចូល llama-cpp-python ទេ (ត្រូវការ" -ForegroundColor Cyan
Write-Host "  សម្រាប់ដំណើរការម៉ូដែល GGUF ក្នុងដំណើរការដូចគ្នា)។" -ForegroundColor Cyan
Write-Host "" -ForegroundColor Cyan
Write-Host "  ប្រសិនបើអ្នកចង់ប្រើម៉ូដែល GGUF (.gguf) អ្នកអាច៖" -ForegroundColor Cyan
Write-Host "    1. ប្រើ backend 'llama-server (external process)' — គ្រាន់តែ" -ForegroundColor Cyan
Write-Host "       ទាញយក llama-server.exe ពី llama.cpp releases ហើយ" -ForegroundColor Cyan
Write-Host "       កំណត់ផ្លូវរបស់វានៅក្នុង UI របស់កម្មវិធី (⚙️ LLM Backend)។" -ForegroundColor Cyan
Write-Host "       មិនតម្រូវឱ្យដំឡើង Python package អ្វីទាំងអស់។" -ForegroundColor Cyan
Write-Host "" -ForegroundColor Cyan
Write-Host "    2. ដំឡើង llama-cpp-python ដោយខ្លួនឯងក្រោយពេលនេះ៖" -ForegroundColor Cyan
Write-Host "         pip install llama-cpp-python" -ForegroundColor Cyan
Write-Host " ------------------------------------------------------------------" -ForegroundColor Cyan
Write-Host ""
Write-Host "[ចំណាំ] llama-cpp-python មិនត្រូវបានដំឡើងទេ។ ម៉ូដែល GGUF អាចប្រើ" -ForegroundColor Yellow
Write-Host "        បានតាមរយៈ backend 'llama-server (external process)' —" -ForegroundColor Yellow
Write-Host "        កំណត់ផ្លូវ llama-server.exe នៅផ្នែកខាងលើនៃ UI របស់កម្មវិធី។" -ForegroundColor Yellow
Write-Host "        (សម្រាប់ Speech-to-Text តាមរយៈ whisper.cpp សូមទាញយកដោយឡែក" -ForegroundColor Yellow
Write-Host "         នូវ whisper-server.exe ពី https://github.com/ggerganov/whisper.cpp/releases)" -ForegroundColor Yellow

$llamaCppInstalled = $false
$llamaCppMode = "skipped"

# ── STEP 6: Install project requirements ────────────────────────────
Write-Host ""
Write-InstallProgress 70 "[6/8] កំពុងដំឡើង dependencies របស់គម្រោង..." "Installing requirements.txt packages..."
Write-Host "      អាចចំណាយពេលច្រើននាទី..."

Write-Host " កំពុងដំឡើង packages ទាំងអស់ពី requirements.txt..."
$coreOk = Invoke-PipRetry @("install", "--prefer-binary", "--timeout", "120", "-r", (Join-Path $root "requirements.txt")) 3

Write-Host ""
$hasPoppler = (Get-Command pdfinfo -ErrorAction SilentlyContinue) -or (Get-Command pdftoppm -ErrorAction SilentlyContinue) -or (Test-Path -LiteralPath (Join-Path $root "poppler"))
if (-not $hasPoppler) {
    Write-InstallProgress 78 "[6/8] កំពុងពិនិត្យ/ដំឡើង Poppler..." "Downloading PDF rendering engine..."
    Write-Host "[*] កំពុងពិនិត្យ/ដំឡើង Poppler (សម្រាប់ការបម្លែង PDF->រូបភាព)..." -ForegroundColor Yellow
    $popplerZip = Join-Path $root "poppler.zip"
    $popplerDir = Join-Path $root "poppler"
    try {
        Write-Host "    [+] កំពុងទាញយក Poppler binaries សម្រាប់ Windows..." -ForegroundColor Cyan
        $popplerUrl = "https://github.com/oschwartz10612/poppler-windows/releases/download/v24.08.0-0/Release-24.08.0-0.zip"
        Invoke-WebRequest -Uri $popplerUrl -OutFile $popplerZip -UseBasicParsing
        Write-Host "    [+] កំពុងពន្លាត Poppler ទៅកាន់ ./poppler..." -ForegroundColor Cyan
        Expand-Archive -Path $popplerZip -DestinationPath $popplerDir -Force
        Remove-Item -Path $popplerZip -Force -ErrorAction SilentlyContinue
        Write-Host "[OK] Poppler ត្រូវបានដំឡើងដោយស្វ័យប្រវត្តិទៅកាន់ ./poppler" -ForegroundColor Green
    } catch {
        if (Get-Command scoop -ErrorAction SilentlyContinue) {
            try { & scoop install poppler } catch {}
        } elseif (Get-Command choco -ErrorAction SilentlyContinue) {
            try { & choco install poppler -y } catch {}
        } elseif (Get-Command winget -ErrorAction SilentlyContinue) {
            try { & winget install --id=Software-Network.Poppler -e --accept-source-agreements --accept-package-agreements } catch {}
        }
    }
} else {
    Write-Host "[OK] Poppler ត្រូវបានដំឡើងរួចរាល់ហើយ។" -ForegroundColor Green
}
Write-Host ""

if (-not $coreOk) {
    Write-Host ""
    Write-Host "[កំហុស] ការដំឡើង dependencies បានបរាជ័យ។" -ForegroundColor Red
    Write-Host "        សាកល្បងដំណើរការដោយដៃ: pip install -r requirements.txt" -ForegroundColor Red
    Write-Host "        (ការបរាជ័យដោយសារបណ្តាញ អាចជោគជ័យពេលរត់ម្តងទៀត)" -ForegroundColor Yellow
    Set-InstallStatus 1
    Pause-Exit
    exit 1
}
Write-Host "[OK] Dependencies ត្រូវបានដំឡើង។" -ForegroundColor Green
Write-InstallProgress 82 "[6/8] Dependencies ត្រូវបានដំឡើង" "Core dependencies ready"

# ── STEP 7: Install Playwright (Deep Research's optional browser tools) ──
# Used by deep_research_agent.py / playwright_search_tool.py when the
# "Use Playwright (Headless Browser) Tools" checkbox is enabled on the
# 🔬 Deep Research tab. This is a SEPARATE, TWO-PART install:
#   1. `pip install playwright` — the Python package/API bindings.
#   2. `playwright install chromium` — the actual browser binary, which
#      pip does NOT download on its own.
# Skipping part 2 is exactly what used to cause a confusing failure: the
# checkbox stays present and clickable in the UI, the app builds the
# agent's Playwright tools without error, and only the FIRST actual
# search/visit-page call fails deep into a run (burning a full agent
# step and real wall-clock time) with "ImportError: ... needs the
# `playwright` package and its browser binaries". Running both install
# steps here, with a real smoke test that launches an actual headless
# browser (not just checking the import), catches that gap at setup
# time instead of mid-research-run. This feature is optional — Deep
# Research's default (non-Playwright) search tools already work without
# it — so any failure here is a warning, not a fatal setup error.
Write-Host ""
Write-InstallProgress 84 "[7/8] កំពុងដំឡើង Playwright package..." "Installing playwright package..."

$playwrightInstalled = $false

& $venvPython -m pip install "playwright>=1.40.0" --quiet
if ($LASTEXITCODE -eq 0) {
    Write-InstallProgress 87 "[7/8] កំពុងទាញយក Chromium browser..." "Downloading Chromium engine for Deep Research (~150-300 MB)..."
    Write-Host " កំពុងទាញយក Chromium browser binary (playwright install chromium)..."
    Write-Host "      អាចចំណាយពេលច្រើននាទី (ទាញយកប្រហែល ១៥០-៣០០ MB)..."
    & $venvPython -m playwright install chromium --with-deps *> $null
    if ($LASTEXITCODE -ne 0) {
        # --with-deps needs elevated/root privileges on some systems to
        # install OS-level libraries; retry without it — the browser
        # binary itself still installs fine without --with-deps on most
        # Windows machines, which already ship the needed system libs.
        & $venvPython -m playwright install chromium
    }

    if ($LASTEXITCODE -eq 0) {
        Write-InstallProgress 90 "[7/8] កំពុងផ្ទៀងផ្ទាត់ Chromium..." "Testing headless browser launch..."
        Write-Host " កំពុងផ្ទៀងផ្ទាត់ដោយបើក Chromium ពិតប្រាកដ (headless smoke test)..."
        $pwCode = "from playwright.sync_api import sync_playwright`nwith sync_playwright() as p:`n    b = p.chromium.launch(headless=True)`n    b.close()`nprint('OK')"
        $pwOk = $false
        $pwRes = Invoke-CapturedProcess -FileName $venvPython -Arguments "-c `"$pwCode`"" -TimeoutSec 60
        if (-not $pwRes.TimedOut -and $pwRes.ExitCode -eq 0) { $pwOk = $true }

        if ($pwOk) {
            Write-Host "[OK] Playwright + Chromium ត្រូវបានដំឡើង និងផ្ទៀងផ្ទាត់ដោយជោគជ័យ។" -ForegroundColor Green
            $playwrightInstalled = $true
        } else {
            Write-Host "[ព្រមាន] Chromium ត្រូវបានទាញយក ប៉ុន្តែការសាកល្បងបើក browser ពិតប្រាកដបានបរាជ័យ។" -ForegroundColor Yellow
            Write-Host "         ប្រអប់ 'Use Playwright (Headless Browser) Tools' នៅផ្ទាំង ស្រាវជ្រាវស៊ីជម្រៅ អាចនឹងមិនដំណើរការទេ។" -ForegroundColor Yellow
        }
    } else {
        Write-Host "[ព្រមាន] ការទាញយក Chromium browser binary បានបរាជ័យ។" -ForegroundColor Yellow
        Write-Host "         សូមសាកល្បងដោយដៃពេលក្រោយ: python -m playwright install chromium" -ForegroundColor Yellow
    }
} else {
    Write-Host "[ព្រមាន] ការដំឡើង playwright package បានបរាជ័យ។" -ForegroundColor Yellow
}

if (-not $playwrightInstalled) {
    Write-Host " ចំណាំ: នេះជាមុខងារជម្រើសសម្រាប់ផ្ទាំង 🔬 ស្រាវជ្រាវស៊ីជម្រៅ តែប៉ុណ្ណោះ — កម្មវិធីនៅតែដំណើរការធម្មតា" -ForegroundColor Yellow
    Write-Host " ដោយប្រើឧបករណ៍ស្វែងរកលំនាំដើម (DuckDuckGo) ។ កុំធីក 'Use Playwright (Headless Browser) Tools'" -ForegroundColor Yellow
    Write-Host " នៅលើផ្ទាំងនោះ ប្រសិនបើអ្នកមិនបានដំណើរការជំហាននេះដោយជោគជ័យទេ។" -ForegroundColor Yellow
}

# ── STEP 8: Comprehensive smoke test ──────────────────────────────────
Write-Host ""
Write-InstallProgress 94 "[8/8] កំពុងសាកល្បងប្រព័ន្ធ (smoke test)..." "Testing core AI & document modules..."
Write-Host ""

$importOk = $true
$testGroups = @(
    @{label="Core";        pkgs=@("torch", "chromadb", "gradio")}
    @{label="LLM/Embed";   pkgs=@("transformers", "sentence_transformers")}
    @{label="Documents";   pkgs=@("fitz", "docx", "pandas")}
    @{label="Audio/Vision"; pkgs=@("PIL", "soundfile", "librosa")}
    @{label="Network";     pkgs=@("ddgs", "requests")}
)

foreach ($g in $testGroups) {
    $groupOk = $true
    $failedPkgs = @()
    foreach ($p in $g.pkgs) {
        & $venvPython -c "import $p; print('OK')" 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            $groupOk = $false
            $importOk = $false
            $failedPkgs += $p
        }
    }
    $icon = if ($groupOk) { "[OK]" } else { "[ព្រមាន]" }
    $color = if ($groupOk) { "Green" } else { "Yellow" }
    if ($groupOk) {
        Write-Host " $icon $($g.label)" -ForegroundColor $color
    } else {
        Write-Host " $icon $($g.label) — បរាជ័យ: $($failedPkgs -join ', ')" -ForegroundColor $color
    }
}

# Optional packages — warn only, not a failure
Write-Host ""
$optionalPkgs = @("playwright", "bitsandbytes", "byaldi")
foreach ($p in $optionalPkgs) {
    & $venvPython -c "import $p; print('OK')" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host " [ចំណាំ] $p មិនទាន់ដំឡើងទេ (មុខងារជម្រើស)" -ForegroundColor Cyan
    } else {
        Write-Host " [OK] $p" -ForegroundColor Green
    }
}

Write-Host ""
if ($importOk) {
    Write-Host "[OK] ការសាកល្បងបានជោគជ័យ — dependencies ទាំងអស់ដំណើរការត្រឹមត្រូវ។" -ForegroundColor Green
Write-InstallProgress 98 "[8/8] ការសាកល្បងបានជោគជ័យ" "All system modules verified successfully"
} else {
    Write-Host "[ព្រមាន] កញ្ចប់មួយចំនួនបរាជ័យ — សូមពិនិត្យលទ្ធផលខាងលើ។" -ForegroundColor Yellow
    Write-Host "        សាកល្បងដំណើរការ: pip install -r requirements.txt" -ForegroundColor Yellow
}

Write-Host "[ចំណាំ] llama-cpp-python (GGUF, in-process): មិនត្រូវបានដំឡើងទេ។ ម៉ូដែល GGUF" -ForegroundColor Cyan
Write-Host "        នៅតែអាចប្រើបាន តាមរយៈ backend 'llama-server (external process)' — កំណត់ផ្លូវ" -ForegroundColor Cyan
Write-Host "        llama-server.exe នៅផ្នែកខាងលើនៃ UI របស់កម្មវិធី។" -ForegroundColor Cyan
Write-Host "        ឬដំឡើង llama-cpp-python ដោយខ្លួនឯង៖ pip install llama-cpp-python" -ForegroundColor Cyan
Write-Host "        (សម្រាប់ Speech-to-Text តាមរយៈ whisper.cpp សូមទាញយកដោយឡែក" -ForegroundColor Cyan
Write-Host "         នូវ whisper-server.exe ពី https://github.com/ggerganov/whisper.cpp/releases)" -ForegroundColor Cyan

if ($playwrightInstalled) {
    Write-Host "[OK] Playwright (Deep Research browser tools): ត្រូវបានដំឡើង និងផ្ទៀងផ្ទាត់។" -ForegroundColor Green
} else {
    Write-Host "[ព្រមាន] Playwright (Deep Research browser tools): មិនអាចប្រើបានទេ - ប្រអប់ 'Use Playwright' នៅតែបង្ហាញ ប៉ុន្តែសូមកុំធីកវា។" -ForegroundColor Yellow
}

# PyTorch's final, VERIFIED status — reflects the real-kernel smoke test
# in STEP 5b above, not just whether `pip install` exit-coded 0. If the
# GPU wheel failed the real test, $cudaVersion was already reset to
# "cpu" there, so this always reflects what will ACTUALLY run at app
# launch, not an optimistic guess based on driver version alone.
if ($cudaVersion -eq "cpu") {
    Write-Host "[ចំណាំ] PyTorch: កំពុងប្រើ CPU (មិនប្រើ GPU) ។ កម្មវិធីនឹងបង្ហាញព័ត៌មានលម្អិតនៅក្នុង UI ប្រសិនបើ GPU មួយត្រូវបានរកឃើញ ប៉ុន្តែមិនត្រូវបានគាំទ្រ។" -ForegroundColor Yellow
} else {
    Write-Host "[OK] PyTorch: បានផ្ទៀងផ្ទាត់ថា GPU ដំណើរការជាមួយ wheel '$cudaVersion' ។" -ForegroundColor Green
}

# ── Done ───────────────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " ការដំឡើងបានបញ្ចប់!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host " ជំហានបន្ទាប់:"
Write-Host "   ១. ចាប់ផ្តើមកម្មវិធី:        ចុចពីរដងលើ  RUN.bat"
Write-Host "   ២. កំណត់រចនាសម្ព័ន្ធ Model Settings (⚙️) ក្នុង UI: provider, ម៉ូដែលតាមផ្ទាំង"
Write-Host "      — ជម្រើស: ទាញយក whisper-server.exe ពី whisper.cpp/releases សម្រាប់ STT server"
Write-Host "   ៣. បើកផ្ទាំង `"Knowledge Base`" ដើម្បីបង្ហោះ និងបញ្ចូលឯកសាររបស់អ្នក។"
Write-Host ""
Write-Host " កម្មវិធីនឹងបើកនៅ:  http://localhost:7861"
Write-Host ""
Set-InstallStatus 0
Write-InstallProgress 100 "ការដំឡើងបានបញ្ចប់!" "Setup complete! LocalAiLab Assistant is ready."
Pause-Exit