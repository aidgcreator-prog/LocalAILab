# 🤖 Multipurpose AI Assistant — Release Notes v0.0.3 beta

🇰🇭 **[ខ្មែរ](#-ខ្មែរ)** | 🇬🇧 **[English](#-english)**

---

## 🇰🇭 ខ្មែរ

# 🚀 កំណែប្រែ LocalAiLab Assistant v0.0.3 beta

យើងខ្ញុំសូមណែនាំ **LocalAiLab Assistant v0.0.3 beta** ដែលជាការធ្វើបច្ចុប្បន្នភាពដ៏ធំមួយ រួមមានកម្មវិធីដំឡើងស្វ័យប្រវត្តិ (Windows Setup Wizard) ការគ្រប់គ្រងម៉ូដែលតាមរយៈ CSV ការទាញយកម៉ូដែល Gemma 4, Unsloth, LMStudio ទាំងអស់ និងផ្ទាំងស្រាវជ្រាវ Deep Research!

---

### 🆕 អ្វីដែលថ្មីក្នុងកំណែ 0.0.3 beta

#### 📦 1. កម្មវិធីដំឡើង Windows Setup Wizard (`LocalAiLab_Setup_v0.0.3.exe`)
- **ដំឡើងងាយស្រួល**៖ កម្មវិធីដំឡើងទំហំស្រាល (~10.8 MB) ជាមួយ Inno Setup UI ទំនើប។
- **ជ្រើសរើសទីតាំងដំឡើង**៖ អាចជ្រើសរើសផ្លូវដំឡើងតាមចិត្ត (ឧ. `D:\LocalAiLab`) ដោយមិនត្រូវការសិទ្ធិ Admin (`PrivilegesRequired=lowest`)។
- **របារកើនឡើង (Progress Bar)**៖ បង្ហាញព័ត៌មានលម្អិតបន្តផ្ទាល់ (0%–100%) ពេលរៀបចំ `.venv` និងដំឡើង PyTorch តាមផ្នែករឹង (GPU/CPU) របស់ម៉ាស៊ីនអ្នក។
- **ប៊ូតុង Cancel**៖ អាចចុចបោះបង់ការដំឡើងបានគ្រប់ពេល ដោយសុវត្ថិភាព។
- **Shortcut ស្វ័យប្រវត្តិ**៖ បង្កើត Shortcut នៅលើ Desktop និង Start Menu ដោយស្វ័យប្រវត្តិ។

#### 📄 2. ការគ្រប់គ្រងម៉ូដែលតាមរយៈ CSV (`models.csv` / `hf_models.csv`)
- **ងាយស្រួលកែប្រែ**៖ បញ្ជីម៉ូដែលទាំងអស់ត្រូវបានផ្លាស់ប្តូរចេញពី Python code ទៅជាឯកសារ `models.csv` ធ្វើឱ្យអ្នកប្រើប្រាស់អាចបន្ថែម ឬកែប្រែម៉ូដែលក្នុង Excel ឬ Notepad បានយ៉ាងងាយ។
- **ទំហំទាញយកច្បាស់លាស់ពី Hugging Face API**៖ ទំហំទាញយកពិតប្រាកដត្រូវបានទាញយកដោយស្វ័យប្រវត្តិពី Hugging Face Hub API (ឧ. Gemma 4 E2B = 4.8 GB, E4B = 7.4 GB, 31B = 62 GB, Unsloth MLX 4-bit = 1.3–6.1 GB)។
- **អាប់ដេតភ្លាមៗ**៖ ចុច "Rescan GGUF Folder" ដើម្បី load ទិន្នន័យថ្មីពី CSV ដោយមិនបាច់បិទបើកកម្មវិធីឡើយ។

#### ⚙️ 3. ការគ្រប់គ្រង Provider ថ្មី & UI សាមញ្ញ
- **Accordion "ការកំណត់ម៉ូដែល" ជាសកល**៖ រៀបចំ API Keys, Model Provider, ផ្លូវ `llama-server.exe`, `whisper-server.exe`, និងថត GGUF ក្នុងកន្លែងតែមួយ។
- **LiteLLM & Hugging Face API**៖ ភ្ជាប់ទៅកាន់ OpenAI, Anthropic, Groq, ឬ Hugging Face Inference API ដោយរលូន។
- **UI ស្អាត និងលឿន**៖ សម្រួល UI ដោយដកបញ្ជីទម្លាក់ Model Quantization ចាស់ចេញ ដើម្បីឱ្យការជ្រើសរើសម៉ូដែល pre-quantized (Unsloth, MLX, Google QAT/CT) ធ្វើឡើងដោយផ្ទាល់ និងលឿនរហ័ស។

#### 🔬 4. ផ្ទាំងស្រាវជ្រាវស៊ីជម្រៅ (Deep Research Agent)
- **Agent ពហុដំណាក់កាល**៖ បំបែកសំណួរធំៗជាសំណួររង ស្វែងរកតាមអ៊ីនធឺណិត រួចសរសេររបាយការណ៍ជា Markdown (`ToolCallingAgent`)។
- **DuckDuckGo & Playwright Browser Tools**៖ ស្វែងរកព័ត៌មានតាម Web ដោយឥតគិតថ្លៃ និងអាចបើក Headless Browser ដើម្បីអាន/ទាញយកទិន្នន័យពី Web/PDF ដែលត្រូវការ JavaScript។

#### 🎯 5. ម៉ូដែល Gemma 4, Unsloth & LM Studio
- **ម៉ូដែល Google, Unsloth & LM Studio**៖ បញ្ជីម៉ូដែល Hugging Face រួមមានម៉ូដែលផ្លូវការពី Google (E2B, E4B, 12B, 26B-A4B, 31B, Mobile QAT, Mobile CT, W4A16 CT), Unsloth (BnB 4-bit, MLX 4-bit/3-bit), និង LM Studio Community (MLX 4-bit)។
- **Gemma 4 Vision Chat**៖ ម៉ូដែល Gemma 4 ទាំងអស់ជាម៉ូដែលចក្ខុវិស័យ ដូច្នេះអាចប្រើក្នុងផ្ទាំង "🎨 Vision Chat" បានភ្លាមៗ ដោយមិនចាំបាច់ម៉ូដែល VLM ដាច់ដោយឡែក។
- **តម្រូវការ**៖ `transformers>=5.10.1` សម្រាប់ Gemma 4 (ដំឡើងស្វ័យប្រវត្តិ)។

---

### 📥 របៀបដំឡើង (Quick Installation)

1. ទាញយក **`LocalAiLab_Setup_v0.0.3.exe`** ពីផ្នែក **Assets** នៃ GitHub Releases។
2. ចុចពីរដងលើ file executable ដើម្បីបើក Setup Wizard។
3. ជ្រើសរើសទីតាំងដំឡើង រួចចុច **Install** — កម្មវិធីនឹងរៀបចំ Python Virtual Environment និង GPU/CPU PyTorch ដោយស្វ័យប្រវត្តិ។
4. បន្ទាប់ពីដំឡើងរួចរាល់ ចុចលើ Shortcut **"LocalAiLab Assistant"** នៅលើ Desktop ដើម្បីចាប់ផ្តើមប្រើប្រាស់!

---
---

## 🇬🇧 English

# 🚀 LocalAiLab Assistant Release Notes v0.0.3 beta

We are excited to announce **LocalAiLab Assistant v0.0.3 beta**! This major update introduces CSV-based dynamic model management, exact download size tracking via Hugging Face API, a single-file Windows Setup Wizard, and an autonomous Deep Research agent.

---

### 🆕 What's New in v0.0.3 beta

#### 📦 1. Windows Setup Wizard (`LocalAiLab_Setup_v0.0.3.exe`)
- **Streamlined Setup**: Lightweight installer (~10.8 MB) built with a modern Inno Setup wizard.
- **Custom Installation Folder**: Install anywhere (e.g., `D:\LocalAiLab`) without requiring administrator privileges (`PrivilegesRequired=lowest`).
- **Live Progress Reporting**: Real-time progress bar (0%–100%) tracking Python environment creation and hardware-optimized PyTorch/CUDA setup.
- **Graceful Cancellation**: Safe, single-click cancellation that cleans up background tasks cleanly.
- **Desktop & Start Menu Shortcuts**: Automatic creation of launch shortcuts upon installation.

#### 📄 2. CSV-Driven Model Management (`models.csv` / `hf_models.csv`)
- **User-Editable Models File**: All Hugging Face model definitions are externalized to `models.csv`, allowing users to easily add, edit, or remove models using Excel or Notepad without touching code.
- **Verified Hugging Face Download Sizes**: Exact download sizes are fetched live from Hugging Face Hub API (e.g., Gemma 4 E2B = 4.8 GB, E4B = 7.4 GB, 31B = 62 GB, Unsloth MLX 4-bit = 1.3–6.1 GB).
- **Hot Reload**: Clicking "Rescan GGUF Folder" instantly reloads updated models from the CSV file at runtime.

#### ⚙️ 3. Enhanced Model Settings & Streamlined UI
- **Global Model Settings Accordion**: Consolidates API Keys, HuggingFace Inference tokens, LiteLLM parameters, `llama-server.exe` / `whisper-server.exe` paths, and GGUF directories into a central control panel.
- **LiteLLM & HF Inference API**: Connect seamlessly to OpenAI, Anthropic, Groq, or Hugging Face Inference API endpoints.
- **Clean UI**: Streamlined interface by removing unnecessary quantization controls in favor of pre-quantized model selections (Unsloth BnB 4-bit, MLX 4-bit/3-bit, Google QAT/CT).

#### 🔬 4. Autonomous Deep Research Agent
- **Multi-Step Search & Report**: Break down complex research prompts into sub-queries, search the web autonomously, and summarize findings into structured Markdown reports using `ToolCallingAgent`.
- **DuckDuckGo & Headless Browser Tools**: Free web search using `DuckDuckGoSearchTool` alongside optional Playwright browser automation for scraping JS-heavy sites and PDFs.

#### 🎯 5. Google Gemma 4, Unsloth & LM Studio Models
- **Curated Model Lineup**: Hugging Face dropdowns feature models exclusively from `google/` (E2B, E4B, 12B, 26B-A4B, 31B, Mobile QAT, Mobile CT, W4A16 CT), `unsloth/` (BnB 4-bit, MLX 4-bit/3-bit), and `lmstudio-community/` (MLX 4-bit).
- **Native Gemma 4 Vision Chat**: Every Gemma 4 model is natively multimodal and works out of the box in the "🎨 Vision Chat" tab.
- **Requirement**: `transformers>=5.10.1` for Gemma 4 (installed automatically).

---

### 📥 Quick Installation Guide

1. Download **`LocalAiLab_Setup_v0.0.3.exe`** from the **Assets** section of GitHub Releases.
2. Double-click the installer to launch the Setup Wizard.
3. Select your preferred installation directory and click **Install** — the setup process will automatically configure Python dependencies and detect your GPU/CPU hardware.
4. Launch the application via the **"LocalAiLab Assistant"** shortcut created on your Desktop!
