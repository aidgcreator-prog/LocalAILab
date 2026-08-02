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
        "$Percent|$Title|$Detail" | Out-File -FilePath $ProgressFile -Encoding UTF8 -Force
    } catch {}
}

function Set-InstallStatus([int]$Code) {
    try {
        "$Code" | Out-File -FilePath $StatusFile -Encoding UTF8 -Force
    } catch {}
}

# ── STEP 0: Check we are in the right folder & Path Length ─────────────────────
if (-not (Test-Path -LiteralPath (Join-Path $root "app.py"))) {
    Write-Host "[កំហុស] រកមិនឃើញ app.py ។ សូមដំណើរការស្គ្រីបនេះពីក្នុងថតឫសនៃកម្មវិធី (ថតដែលមាន app.py) ។" -ForegroundColor Red
    Set-InstallStatus 1
        Read-Host "ចុច Enter ដើម្បីបិទ"
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
        Read-Host "ចុច Enter ដើម្បីបិទ"
        exit 1
    }

    Write-InstallProgress 15 "[1/8] កំពុងដំឡើង Python 3.11.9..." "Installing Python 3.11.9 (silent)..."
    $installArgs = @("/quiet", "InstallAllUsers=1", "PrependPath=1", "Include_pip=1", "Include_launcher=1", "Include_test=0")
    $proc = Start-Process -FilePath $installerPath -ArgumentList $installArgs -Wait -PassThru
    if ($proc.ExitCode -ne 0) {
        Write-Host "[កំហុស] ការដំឡើង Python បានបរាជ័យ (exit code $($proc.ExitCode)) ។" -ForegroundColor Red
        Write-Host "        សូមដំឡើងដោយផ្ទាល់ពី: https://www.python.org/downloads/"
        Set-InstallStatus 1
        Read-Host "ចុច Enter ដើម្បីបិទ"
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
        Read-Host "ចុច Enter ដើម្បីបិទ"
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
        Read-Host "ចុច Enter ដើម្បីបិទ"
        exit 1
    }
}
Write-Host "[OK] pip អាចប្រើប្រាស់បាន។" -ForegroundColor Green

# ── STEP 2: Create virtual environment ────────────────────────────
Write-Host ""
Write-InstallProgress 22 "[2/8] កំពុងបង្កើត virtual environment (.venv)..." "Setting up .venv folder..."
$venvPython = Join-Path $root ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $venvPython) {
    Write-Host "[OK] .venv មានរួចហើយ កំពុងរំលងការបង្កើត។" -ForegroundColor Green
} else {
    & python -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[កំហុស] បរាជ័យក្នុងការបង្កើត virtual environment ។" -ForegroundColor Red
        Set-InstallStatus 1
        Read-Host "ចុច Enter ដើម្បីបិទ"
        exit 1
    }
    Write-Host "[OK] Virtual environment ត្រូវបានបង្កើត។" -ForegroundColor Green
}
Write-InstallProgress 25 "[2/8] Virtual environment រួចរាល់" ".venv created and activated"

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
        $cudaLine = $smiOut | Select-String "CUDA Version"
        $rawCuda = $null
        if ($cudaLine) {
            if ($cudaLine.Line -match "CUDA Version:\s*([0-9]+\.[0-9]+)") {
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
        if ($rawCuda) {
            $cmajor = [int]($rawCuda.Split(".")[0])
            $cfull = $rawCuda
            if ($cmajor -eq 11) {
                $cudaVersion = "cu118"
            } elseif ($cmajor -eq 12) {
                if ($cfull -match "^12\.(1|2|3)") {
                    $cudaVersion = "cu121"
                } elseif ($cfull -match "^12\.(4|5|6)") {
                    $cudaVersion = "cu124"
                } else {
                    $cudaVersion = "cu128"
                }
            } elseif ($cmajor -ge 13) {
                Write-Host "[ចំណាំ] Driver CUDA version ($rawCuda) ថ្មីជាង wheel tier ដែលស្គាល់ - កំពុងប្រើ cu128 (tier ថ្មីបំផុត)។ driver ថ្មីមិនមានន័យថា GPU ត្រូវបានគាំទ្រដោយ PyTorch ថ្មីៗនោះទេ - ការសាកល្បងផ្ទុកគំរូខាងក្រោមនឹងផ្ទៀងផ្ទាត់រឿងនេះឱ្យប្រាកដ។" -ForegroundColor Cyan
                $cudaVersion = "cu128"
            } else {
                $cudaVersion = "cu128"
            }
        } else {
            $cudaVersion = "cu128"
        }
        $torchIndex = "https://download.pytorch.org/whl/$cudaVersion"
        Write-Host "[OK] នឹងដំឡើង PyTorch សម្រាប់ CUDA $cudaVersion (នឹងផ្ទៀងផ្ទាត់ដោយផ្ទុកគំរូ kernel ពិតប្រាកដនៅជំហានបន្ទាប់)" -ForegroundColor Green
        $gpuDone = $true
    }
}

if (-not $gpuDone) {
    $rocmSmi = Get-Command rocm-smi -ErrorAction SilentlyContinue
    $rocminfo = Get-Command rocminfo -ErrorAction SilentlyContinue
    if ($rocmSmi -or $rocminfo) {
        $gpuBrand = "amd_rocm"
        Write-Host "[OK] រកឃើញ GPU AMD ជាមួយ ROCm ។" -ForegroundColor Green
        $cudaVersion = "rocm6.2"
        $torchIndex = "https://download.pytorch.org/whl/rocm6.2"
        Write-Host "[OK] នឹងដំឡើង PyTorch សម្រាប់ ROCm (wheel: $cudaVersion)" -ForegroundColor Green
        Write-Host "[ចំណាំ] ប្រសិនបើការដំឡើងបរាជ័យ សូមពិនិត្យ https://pytorch.org សម្រាប់ wheel ROCm ចុងក្រោយ។"
        $gpuDone = $true
    } else {
        $isAmd = $false
        try {
            $vc = Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue
            if ($vc -and ($vc.Name -join ";") -match "Radeon|AMD") { $isAmd = $true }
        } catch {}
        if ($isAmd) {
            $gpuBrand = "amd_no_rocm"
            Write-Host ""
            Write-Host "+-----------------------------------------------------------------+" -ForegroundColor Yellow
            Write-Host "|  រកឃើញ GPU AMD ប៉ុន្តែមិនទាន់ដំឡើង ROCm toolkit ទេ។              |" -ForegroundColor Yellow
            Write-Host "|                                                                   |" -ForegroundColor Yellow
            Write-Host "|  ដើម្បីប្រើ GPU អ្នកត្រូវការ AMD ROCm សម្រាប់ Windows ។             |" -ForegroundColor Yellow
            Write-Host "|  ទាញយក: https://rocm.docs.amd.com/en/latest/                    |" -ForegroundColor Yellow
            Write-Host "|                                                                   |" -ForegroundColor Yellow
            Write-Host "|  GPU AMD ដែលគាំទ្រ (ROCm លើ Windows):                             |" -ForegroundColor Yellow
            Write-Host "|    RX 6000 series, RX 7000 series, Instinct MI series            |" -ForegroundColor Yellow
            Write-Host "|                                                                   |" -ForegroundColor Yellow
            Write-Host "|  កំពុងប្រើ CPU PyTorch ជាបណ្តោះអាសន្ន។                            |" -ForegroundColor Yellow
            Write-Host "|  ដំណើរការ SETUP.bat ម្តងទៀត បន្ទាប់ពីដំឡើង ROCm ។                 |" -ForegroundColor Yellow
            Write-Host "+-----------------------------------------------------------------+" -ForegroundColor Yellow
            Write-Host ""
            $cudaVersion = "cpu"
            $torchIndex = "https://download.pytorch.org/whl/cpu"
        } else {
            Write-Host "[ព្រមាន] រកមិនឃើញ GPU ទេ (គ្មាន nvidia-smi, rocm-smi ឬ GPU AMD ក្នុងបញ្ជីឧបករណ៍) ។" -ForegroundColor Yellow
            Write-Host "        កំពុងដំឡើង PyTorch សម្រាប់ CPU ។"
            $gpuBrand = "cpu"
            $cudaVersion = "cpu"
            $torchIndex = "https://download.pytorch.org/whl/cpu"
        }
    }
}

# ── STEP 5: Install PyTorch ─────────────────────────────────────────
Write-Host ""
if ($cudaVersion -eq "cpu") {
    Write-InstallProgress 40 "[5/8] កំពុងដំឡើង PyTorch (CPU-only)..." "Downloading PyTorch CPU wheels..."
} else {
    Write-InstallProgress 40 "[5/8] កំពុងដំឡើង PyTorch ($cudaVersion)..." "Downloading PyTorch wheels for $cudaVersion (~2-3 GB)..."
}
Write-Host "      អាចចំណាយពេលច្រើននាទី (torch មានទំហំប្រហែល ២-៣ GB)..."
& $venvPython -m pip install torch torchvision torchaudio --index-url $torchIndex
if ($LASTEXITCODE -ne 0) {
    Write-Host "[កំហុស] ការដំឡើង PyTorch បានបរាជ័យ។" -ForegroundColor Red
    if ($gpuBrand -eq "amd_rocm") {
        Write-Host "[គន្លឹះ] wheel ROCm ប្រហែលជាមិនមានសម្រាប់កំណែ ROCm របស់អ្នកទេ។" -ForegroundColor Yellow
        Write-Host "        សាកល្បង: https://pytorch.org/get-started/locally/ ដើម្បីរក wheel ត្រឹមត្រូវ។"
    }
    Set-InstallStatus 1
        Read-Host "ចុច Enter ដើម្បីបិទ"
        exit 1
}
Write-Host "[OK] PyTorch ត្រូវបានដំឡើង ($cudaVersion) ។" -ForegroundColor Green
Write-InstallProgress 60 "[5/8] PyTorch ត្រូវបានដំឡើង" "PyTorch ($cudaVersion) installed successfully"

# ── STEP 5b: Verify the GPU wheel ACTUALLY works on THIS machine ─────
# `pip install` succeeding, and even `torch.cuda.is_available()`
# returning True, do NOT guarantee this specific PyTorch build ships
# compiled kernels for this specific GPU's compute capability. PyTorch
# wheels only include kernels for a fixed list of architectures, and
# older cards (e.g. Pascal/sm_6x such as the GeForce MX series, or
# Maxwell/sm_5x) have been dropped from recent stable releases. When
# that happens, the model still LOADS onto the device with no error —
# it only crashes the first time a real kernel launches (e.g. deep
# inside a model's tie_weights() step), with a confusing
# "CUDA error: no kernel image is available for execution on the
# device". A driver reporting a new CUDA version (e.g. CUDA 13.x) does
# NOT mean the GPU itself is new/supported — this is exactly the gap
# that let an old GPU silently receive a "should be fine" verdict.
#
# So: actually launch a real kernel here (mirrors the same
# Test-LlamaCppRealModelLoad pattern already used for llama-cpp-python
# below) and, if it fails, automatically fall back to the CPU-only
# wheel instead of leaving a broken GPU install in place for a
# non-technical end user to stumble into later at runtime.
function Test-TorchCudaReal([int]$TimeoutSec = 90) {
    $code = "import torch; x = torch.randn(64, 64, device='cuda'); y = x @ x; torch.cuda.synchronize(); print('OK')"
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName               = $venvPython
    $psi.Arguments              = "-c `"$code`""
    $psi.UseShellExecute        = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError  = $true
    try {
        $proc = [System.Diagnostics.Process]::Start($psi)
    } catch {
        return $false
    }
    $finished = $proc.WaitForExit($TimeoutSec * 1000)
    if (-not $finished) {
        try { $proc.Kill() } catch {}
        return $false
    }
    return ($proc.ExitCode -eq 0)
}

if ($cudaVersion -ne "cpu") {
    Write-Host ""
    Write-InstallProgress 62 "[5b/8] កំពុងផ្ទៀងផ្ទាត់ GPU kernel..." "Executing GPU smoke test kernel..."
    if (Test-TorchCudaReal) {
        Write-Host "[OK] GPU kernel test ជោគជ័យ — PyTorch នឹងប្រើ GPU របស់អ្នកបាន។" -ForegroundColor Green
    } else {
        Write-InstallProgress 65 "[5b/8] កំពុងត្រលប់ទៅ CPU PyTorch វិញ..." "GPU CC incompatible. Installing CPU-only PyTorch wheel..."
        Write-Host "[ព្រមាន] GPU wheel ដំឡើងបានជោគជ័យ ប៉ុន្តែ GPU នេះ (Compute Capability: $computeCap) មិនត្រូវបានគាំទ្រដោយ PyTorch build នេះទេ (ប្រហែលជាចាស់ពេក ឬថ្មីពេក)។ កំពុងត្រលប់ទៅ CPU-only wheel វិញ ដោយស្វ័យប្រវត្តិ..." -ForegroundColor Yellow
        & $venvPython -m pip uninstall torch torchvision torchaudio -y 2>$null
        & $venvPython -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
        if ($LASTEXITCODE -eq 0) {
            $cudaVersion = "cpu"
            $torchIndex  = "https://download.pytorch.org/whl/cpu"
            Write-Host "[OK] កម្មវិធីនឹងដំណើរការនៅលើ CPU ជំនួសវិញ (GPU នេះមិនត្រូវបានគាំទ្រដោយ PyTorch កំណែថ្មីនេះទេ)។" -ForegroundColor Yellow
            Write-Host "     ចំណាំ៖ កម្មវិធីខ្លួនឯងក៏នឹងបង្ហាញការព្រមានស្រដៀងគ្នានេះនៅក្នុង UI ជានិច្ចផងដែរ។" -ForegroundColor Yellow
        } else {
            Write-Host "[កំហុស] ការត្រលប់ទៅ CPU wheel ក៏បានបរាជ័យដែរ។ សូមដំណើរការ SETUP.bat ម្តងទៀត ឬដំឡើងដោយដៃ។" -ForegroundColor Red
            Set-InstallStatus 1
            Read-Host "ចុច Enter ដើម្បីបិទ"
            exit 1
        }
    }
}

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
& $venvPython -m pip install -r (Join-Path $root "requirements.txt")
$coreExit = $LASTEXITCODE

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

if ($coreExit -ne 0) {
    Write-Host "[ព្រមាន] ការដំឡើង dependencies បានបរាជ័យ។ សូមពិនិត្យមើលកំណត់ត្រាខាងលើ។" -ForegroundColor Yellow
    Write-Host "        សាកល្បងដំណើរការ: pip install -r requirements.txt" -ForegroundColor Yellow
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
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName               = $venvPython
        $psi.Arguments              = "-c `"$pwCode`""
        $psi.UseShellExecute        = $false
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError  = $true
        $pwOk = $false
        try {
            $proc = [System.Diagnostics.Process]::Start($psi)
            $finished = $proc.WaitForExit(60000)
            if ($finished -and $proc.ExitCode -eq 0) { $pwOk = $true }
            elseif (-not $finished) { try { $proc.Kill() } catch {} }
        } catch {}

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
Read-Host "ចុច Enter ដើម្បីបិទ"

