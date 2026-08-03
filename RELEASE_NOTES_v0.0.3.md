# 🤖 Multipurpose AI Assistant — Release Notes v0.0.3 beta

🇰🇭 **[ខ្មែរ](#-ខ្មែរ)** | 🇬🇧 **[English](#-english)**

---

## 🇰🇭 ខ្មែរ

# 🚀 កំណែប្រែ LocalAiLab Assistant v0.0.3 beta

យើងខ្ញុំសូមណែនាំ **LocalAiLab Assistant v0.0.3 beta** ដែលជាការធ្វើបច្ចុប្បន្នភាពដ៏ធំមួយ រួមមានកម្មវិធីដំឡើងស្វ័យប្រវត្តិ (Windows Setup Wizard) ការគ្រប់គ្រងម៉ូដែលកាន់តែទូលំទូលាយ និងផ្ទាំងស្រាវជ្រាវ Deep Research!

---

### 🆕 អ្វីដែលថ្មីក្នុងកំណែ 0.0.3 beta

#### 📦 1. កម្មវិធីដំឡើង Windows Setup Wizard (`LocalAiLab_Setup_v0.0.3.exe`)
- **ដំឡើងងាយស្រួល**៖ កម្មវិធីដំឡើងទំហំស្រាល (~10.8 MB) ជាមួយ Inno Setup UI ទំនើប។
- **ជ្រើសរើសទីតាំងដំឡើង**៖ អាចជ្រើសរើសផ្លូវដំឡើងតាមចិត្ត (ឧ. `D:\LocalAiLab`) ដោយមិនត្រូវការសិទ្ធិ Admin (`PrivilegesRequired=lowest`)។
- **របារកើនឡើង (Progress Bar)**៖ បង្ហាញព័ត៌មានលម្អិតបន្តផ្ទាល់ (0%–100%) ពេលរៀបចំ `.venv` និងដំឡើង PyTorch តាមផ្នែករឹង (GPU/CPU) របស់ម៉ាស៊ីនអ្នក។
- **ប៊ូតុង Cancel**៖ អាចចុចបោះបង់ការដំឡើងបានគ្រប់ពេល ដោយសុវត្ថិភាព។
- **Shortcut ស្វ័យប្រវត្តិ**៖ បង្កើត Shortcut នៅលើ Desktop និង Start Menu ដោយស្វ័យប្រវត្តិ។

#### ⚙️ 2. ការគ្រប់គ្រងម៉ូដែល និង Provider ថ្មី
- **Accordion "ការកំណត់ម៉ូដែល" ជាសកល**៖ រៀបចំ API Keys, Model Provider, ផ្លូវ `llama-server.exe`, `whisper-server.exe`, និងថត GGUF ក្នុងកន្លែងតែមួយ។
- **LiteLLM Provider**៖ ភ្ជាប់ទៅកាន់ OpenAI, Anthropic, Groq, ៘ តាមរយៈ API Base Custom សម្រាប់ LLM។
- **Hugging Face Inference API**៖ គាំទ្រម៉ូដែល remote សម្រាប់ LLM, VLM, STT, និង Embeddings។
- **តម្រង & រក្សាទុក Provider**៖ ផ្ទាំងនីមួយៗចងចាំ provider និងម៉ូដែលចុងក្រោយដោយស្វ័យប្រវត្តិ (`user_config.json`)។
- **GGUF Server / Local Backend**៖ គាំទ្រទាំង `llama-cpp-python` (In-process) និង `llama-server.exe` (External Process)។

#### 🔬 3. ផ្ទាំងស្រាវជ្រាវស៊ីជម្រៅ (Deep Research Agent)
- **Agent ពហុដំណាក់កាល**៖ បំបែកសំណួរធំៗជាសំណួររង ស្វែងរកតាមអ៊ីនធឺណិត រួចសរសេររបាយការណ៍ជា Markdown (`ToolCallingAgent`)។
- **DuckDuckGo & Playwright Browser Tools**៖ ស្វែងរកព័ត៌មានតាម Web ដោយឥតគិតថ្លៃ និងអាចបើក Headless Browser ដើម្បីអាន/ទាញយកទិន្នន័យពី Web/PDF ដែលត្រូវការ JavaScript។

#### 🤖 4. ការគាំទ្រម៉ូដែលថ្មី & Feature ផ្សេងៗ
- **Gemma 4 ជាម៉ូដែលមូលដ្ឋាន**៖ បញ្ជីម៉ូដែលមូលដ្ឋានឥឡូវជា **Gemma 4 តែមួយគ្រួសារ** — E2B, E4B, E4B Mobile QAT, 12B, 26B-A4B (MoE), និង 31B — ជាមួយការគាំទ្រ quantization 4-bit/8-bit និង Vision Chat (សូមមើលផ្នែកទី 5 ខាងក្រោម)។
- **Data Analysis Agent**៖ វិភាគ CSV/Excel ដោយស្វ័យប្រវត្តិ ជាមួយជម្រើស workflow តាមប្រភេទ (ការលក់, អតិថិជន, ហិរញ្ញវត្ថុ, ប្រាក់ខែ)។
- **ចងចាំការសន្ទនា (Conversation Memory)**៖ ប្រអប់ចងចាំបរិបទឆ្លង tab និងកំណត់ Context Window ពី 4K ដល់ 128K។

#### 🎯 5. Gemma 4 — ជាម៉ូដែលមូលដ្ឋានតែមួយគត់
- **Gemma 4 ទាំងស្រុង**៖ ម៉ូដែលមូលដ្ឋានឥឡូវជា Gemma 4 តែមួយគ្រួសារប៉ុណ្ណោះ (Qwen ដែលជាម៉ូដែលមូលដ្ឋានចាស់ត្រូវបានដកចេញ) ជាមួយទំហំ RAM ដែលបានកែត្រឹមត្រូវ៖ E2B (~10 GB), E4B (~16 GB), E4B Mobile QAT (~3 GB), 12B (~24 GB), 26B-A4B MoE (~53 GB, active ~4B), 31B (~65 GB)។
- **ជ្រើសរើសម៉ូដែលតាមផ្នែករឹងដោយស្វ័យប្រវត្តិ**៖ កម្មវិធីជ្រើសរើសម៉ូដែល *និង* កម្រិត quantization ដែលសមស្របបំផុតតាម GPU/RAM ដែលរកឃើញ (CPU → E2B 4-bit, 8–12 GB → E4B 4-bit, 16 GB → 26B-A4B 4-bit, 24 GB → 26B-A4B 8-bit, 48 GB+ → 31B 4-bit)។
- **📦 Model Quantization**៖ បញ្ជីទម្លាក់ថ្មីសម្រាប់ bitsandbytes 4-bit/8-bit (CUDA GPU តែប៉ុណ្ណោះ) ជួយសន្សំ RAM យ៉ាងច្រើនសម្រាប់ម៉ូដែលក្នុងស្រុក។
- **Gemma 4 Vision Chat**៖ ម៉ូដែល Gemma 4 ទាំងអស់ជាម៉ូដែលចក្ខុវិស័យ ដូច្នេះអាចប្រើក្នុងផ្ទាំង "🎨 Vision Chat" បានភ្លាមៗ ដោយមិនចាំបាច់ម៉ូដែល VLM ដាច់ដោយឡែក។
- **តម្រូវការ**៖ `transformers>=5.10.1` សម្រាប់ Gemma 4 (SETUP/កម្មវិធីដំឡើងនឹងដំឡើងឱ្យស្វ័យប្រវត្តិ)។

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

We are excited to announce **LocalAiLab Assistant v0.0.3 beta**! This major update introduces a single-file Windows Setup Wizard, comprehensive model provider management, and an autonomous Deep Research agent.

---

### 🆕 What's New in v0.0.3 beta

#### 📦 1. Windows Setup Wizard (`LocalAiLab_Setup_v0.0.3.exe`)
- **Streamlined Setup**: Lightweight installer (~10.8 MB) built with a modern Inno Setup wizard.
- **Custom Installation Folder**: Install anywhere (e.g., `D:\LocalAiLab`) without requiring administrator privileges (`PrivilegesRequired=lowest`).
- **Live Progress Reporting**: Real-time progress bar (0%–100%) tracking Python environment creation and hardware-optimized PyTorch/CUDA setup.
- **Graceful Cancellation**: Safe, single-click cancellation that cleans up background tasks cleanly.
- **Desktop & Start Menu Shortcuts**: Automatic creation of launch shortcuts upon installation.

#### ⚙️ 2. Enhanced Model Configuration & Provider System
- **Global Model Settings Accordion**: Consolidates API Keys, HuggingFace Inference tokens, LiteLLM parameters, `llama-server.exe` / `whisper-server.exe` paths, and GGUF directories into a central control panel.
- **LiteLLM Provider**: Seamlessly connect to OpenAI, Anthropic, Groq, and custom API endpoints.
- **Hugging Face Inference API**: Remote model execution across LLM, VLM, STT, and Embedding tabs.
- **Per-Tab Memory & Filtering**: Remembers selected models and providers per tab across application restarts via `user_config.json`.
- **Flexible GGUF Backend**: Choose between in-process (`llama-cpp-python`) or external process (`llama-server.exe`) for local execution.

#### 🔬 3. Autonomous Deep Research Agent
- **Multi-Step Search & Report**: Break down complex research prompts into sub-queries, search the web autonomously, and summarize findings into structured Markdown reports using `ToolCallingAgent`.
- **DuckDuckGo & Headless Browser Tools**: Free web search using `DuckDuckGoSearchTool` alongside optional Playwright browser automation for scraping JS-heavy sites and PDFs.

#### 🤖 4. New Models & Capabilities
- **Gemma 4 base models**: The base LLM list is now the **Gemma 4 family only** — E2B, E4B, E4B Mobile QAT, 12B, 26B-A4B (MoE), and 31B — with 4-bit/8-bit quantization and Vision Chat support (see section 5 below).
- **Data Analysis Workflows**: Automated CSV/Excel analysis with specialized workflow templates (Sales, Customer, Finance, Payroll).
- **Expanded Context & Memory**: Global context window selection (4K to 128K) and experimental cross-tab conversation memory.

#### 🎯 5. Gemma 4 — The Base Model Family
- **Gemma 4 only**: The base LLM list is now exclusively the Gemma 4 family (the former Qwen base models were removed), with corrected RAM footprints: E2B (~10 GB), E4B (~16 GB), E4B Mobile QAT (~3 GB), 12B (~24 GB), 26B-A4B MoE (~53 GB, ~4B active), 31B (~65 GB).
- **Automatic hardware-tier selection**: The app now picks the right model *and* quantization level for your detected hardware (CPU → E2B 4-bit, 8–12 GB → E4B 4-bit, 16 GB → 26B-A4B 4-bit, 24 GB → 26B-A4B 8-bit, 48 GB+ → 31B 4-bit).
- **📦 Model Quantization**: New dropdown for bitsandbytes 4-bit/8-bit loading (CUDA GPU only) — big RAM savings on local models.
- **Gemma 4 Vision Chat**: Every Gemma 4 model is natively multimodal, so they now work out of the box in the "🎨 Vision Chat" tab — no separate VLM needed.
- **Requirement**: `transformers>=5.10.1` for Gemma 4 (installed automatically by SETUP/the Setup Wizard).

---

### 📥 Quick Installation Guide

1. Download **`LocalAiLab_Setup_v0.0.3.exe`** from the **Assets** section of GitHub Releases.
2. Double-click the installer to launch the Setup Wizard.
3. Select your preferred installation directory and click **Install** — the setup process will automatically configure Python dependencies and detect your GPU/CPU hardware.
4. Launch the application via the **"LocalAiLab Assistant"** shortcut created on your Desktop!
