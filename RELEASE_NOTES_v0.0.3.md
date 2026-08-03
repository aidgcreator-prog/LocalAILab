# 🤖 Multipurpose AI Assistant — Release Notes v0.0.3 beta

🇰🇭 **[ខ្មែរ](#-ខ្មែរ)** | 🇬🇧 **[English](#-english)**

---

## 🇰🇭 ខ្មែរ

# 🚀 កំណែប្រែ LocalAiLab Assistant v0.0.3 beta

យើងខ្ញុំសូមណែនាំ **LocalAiLab Assistant v0.0.3 beta** ដែលជាការធ្វើបច្ចុប្បន្នភាពដ៏ធំមួយ! រួមមានកម្មវិធីដំឡើងស្វ័យប្រវត្តិ (Windows Setup Wizard), គ្រប់គ្រងម៉ូដែល HuggingFace តាមរយៈ CSV ខាងក្រៅ, ប្រើ `ToolCallingAgent` ជាលំនាំដើម, Smart Parsers ការពារកំហុស retry loops, ធ្វើសមកាលកម្ម HF Token ជាមួយ `.env`, និងការរៀបចំទម្រង់ UI និងប្រព័ន្ធពណ៌ visually distinct សម្រាប់ Reasoning, Tools, និង Final Answer!

---

### 🆕 អ្វីដែលថ្មីក្នុងកំណែ 0.0.3 beta

#### 📦 1. កម្មវិធីដំឡើង Windows Setup Wizard (`LocalAiLab_Setup_v0.0.3.exe`)
- **ដំឡើងងាយស្រួល**៖ កម្មវិធីដំឡើងទំហំស្រាល (~10.8 MB) ជាមួយ Inno Setup UI ទំនើប។
- **ជ្រើសរើសទីតាំងដំឡើង**៖ អាចជ្រើសរើសផ្លូវដំឡើងតាមចិត្ត (ឧ. `D:\LocalAiLab`) ដោយមិនត្រូវការសិទ្ធិ Admin (`PrivilegesRequired=lowest`)។
- **របារកើនឡើង (Progress Bar)**៖ បង្ហាញព័ត៌មានលម្អិតបន្តផ្ទាល់ (0%–100%) ពេលរៀបចំ `.venv` និងដំឡើង PyTorch តាមផ្នែករឹង (GPU/CPU) របស់ម៉ាស៊ីនអ្នក។
- **ប៊ូតុង Cancel**៖ អាចចុចបោះបង់ការដំឡើងបានគ្រប់ពេល ដោយសុវត្ថិភាព។
- **Shortcut ស្វ័យប្រវត្តិ**៖ បង្កើត Shortcut នៅលើ Desktop និង Start Menu ដោយស្វ័យប្រវត្តិ។

#### 📄 2. ការគ្រប់គ្រងម៉ូដែលតាមរយៈ CSV ខាងក្រៅ (`hf_models.csv`)
- **ងាយស្រួលកែប្រែ**៖ បញ្ជីម៉ូដែល HuggingFace ទាំងអស់ត្រូវបានរៀបចំក្នុង `hf_models.csv` សម្រាប់បន្ថែម/កែប្រែម៉ូដែល (Google, Unsloth, LMStudio) ជាមួយនឹងម៉ូដែលតូចបំផុត `google/gemma-4-E2B-it-qat-mobile-transformers` ជាលំនាំដើម។
- **ទំហំទាញយកច្បាស់លាស់ពី Hugging Face API**៖ ទំហំទាញយកពិតប្រាកដត្រូវបានទាញយកដោយស្វ័យប្រវត្តិពី Hugging Face Hub API។

#### ⚡ 3. ToolCallingAgent ជាលំនាំដើម & ស្ថាបត្យកម្ម Agent ថ្មី
- **កាត់បន្ថយកំហុស Python Code**៖ ផ្ទាំងសន្ទនាទូទៅ (General Chat) ផ្ទាំង RAG Chat និងផ្ទាំងស្រាវជ្រាវស៊ីជម្រៅ (Deep Research) ប្រើ `ToolCallingAgent` ជាលំនាំដើម ដើមបីជៀសវាងកំហុស parsing កូដ Python លើ local models។
- **CodeAgent សម្រាប់ Data Analysis**៖ ផ្ទាំងវិភាគទិន្នន័យ (Data Analysis) នៅតែប្រើ `CodeAgent` សម្រាប់ប្រតិបត្តិការកូដ Python លើ pandas/matplotlib។

#### 🧠 4. ឧបករណ៍វិភាគ Smart Parser ឆ្លាតវៃ (0 Error Retries)
- **កាត់បន្ថយកំហុស Regex/JSON**៖ បន្ថែម `_smart_parse_code_blobs` និង `_smart_parse_json_blob` សម្រាប់ចាប់យក និងបំលែងចម្លើយអត្ថបទធម្មតា ឬទម្រង់ tool call បែប `call:web_search{query:...}` របស់ Gemma-4 និង local LLM ផ្សេងទៀត ដោយគ្មានកំហុស retry loop ឡើយ។
- **បំលែងអត្ថបទធម្មតាទៅជា Final Answer**៖ ប្រសិនបើម៉ូដែលឆ្លើយជាអត្ថបទធម្មតាដោយគ្មាន JSON blob, Smart Parser បំលែងវាជា `final_answer` ដោយស្វ័យប្រវត្តិក្នុងរយៈពេល 1 វិនាទី។

#### 🔑 5. ធ្វើសមកាលកម្ម HF Token & `.env`
- **គ្មានសារព្រមាន token ទៀតឡើយ**៖ គាំទ្រការផ្ទុក `.env` ដោយស្វ័យប្រវត្តិ និងធ្វើសមកាលកម្មអថេរបរិស្ថាន `HF_TOKEN` ទៅកាន់ `os.environ` និង `.env` ដោយគ្មានសារព្រមានអត់ token ពី Hugging Face Hub ទៀតឡើយ។

#### 🎨 6. សម្រួលទម្រង់ UI និងប្រព័ន្ធពណ៌ Visual Distinction
- **ប្រព័ន្ធពណ៌ និង Container ថ្មី**៖
  - 🧠 **Reasoning Process** (Amber Gold details block ជាមួយ toggle hint)
  - ⚙️ 🛠️ **Step Logs & Tool Calls** (Tech Slate / Cyan cards ជាមួយ collapsible step logs)
  - ✨ 💬 **Final Answer** (Emerald Green cards ជាមួយ high-contrast markdown typography)
- **Emoji Fallback សកល**៖ បន្ថែម font fallbacks សកល (`Segoe UI Emoji`, `Apple Color Emoji`, `Noto Color Emoji`) សម្រាប់ Windows, Mac, Linux, និង Web Browsers។

---

## 🇬🇧 English

# 🚀 LocalAiLab Assistant Release Notes v0.0.3 beta

We are excited to announce **LocalAiLab Assistant v0.0.3 beta**! This major update introduces dynamic CSV model management, default `ToolCallingAgent` architecture, smart parser fallbacks for zero error retries, automatic HF Token and `.env` synchronization, a single-file Windows Setup Wizard, and distinct visual container styling for thinking, tools, and final answers.

---

### 🆕 What's New in v0.0.3 beta

#### 📦 1. Windows Setup Wizard (`LocalAiLab_Setup_v0.0.3.exe`)
- **Lightweight & Clean**: Built with Inno Setup. Allows users to choose any custom installation path (e.g. `E:\LocalAiLab`).
- **Real-Time Progress Bar**: Shows live status during `.venv` creation & PyTorch/dependency installation.
- **Cancel Button & Shortcuts**: Active cancel option and automatic Desktop & Start Menu shortcuts.

#### 📄 2. External `hf_models.csv` Model Registry
- **Zero-Code Model Configuration**: HuggingFace models are organized in an external CSV file (`hf_models.csv`) featuring **Google**, **Unsloth**, and **LMStudio** models, using `google/gemma-4-E2B-it-qat-mobile-transformers` as the default model.
- **Accurate Download Sizes**: Real download sizes pulled via Hugging Face Hub API.

#### ⚡ 3. Default `ToolCallingAgent` Architecture
- **No Python Code Parsing Errors**: General Chat, RAG Chat, and Deep Research default to `ToolCallingAgent` for structured tool calls without requiring models to write executable Python code blocks.
- **Dedicated Data Analysis CodeAgent**: `CodeAgent` remains strictly reserved for Data Analysis (`data_analysis.py`), where executing Python pandas and matplotlib code is required.

#### 🧠 4. Smart Parser Fallbacks (0 Error Retries)
- **Resilient Tool Call Parsing**: `_smart_parse_code_blobs` and `_smart_parse_json_blob` automatically handle Gemma-4 `call:web_search{query:...}` tool call formats and unquoted JSON keys without throwing JSON syntax errors.
- **Plain Text Answer Recovery**: If a model outputs plain text without a JSON blob, the smart parser automatically wraps it into a `final_answer` tool call in 1 second instead of failing into 300-second retry loops.

#### 🔑 5. HF Token & `.env` Synchronization
- **Warning-Free Hugging Face Downloads**: Automatically loads `.env` (`load_dotenv()`) and exports `HF_TOKEN` across `os.environ` (`HF_TOKEN`, `HUGGING_FACE_HUB_TOKEN`, `HUGGINGFACEHUB_API_TOKEN`) and `.env` whenever a token is saved in the UI.

#### 🎨 6. Enhanced UI & Visual Container Distinction
- **Distinct Visual Styling**:
  - 🧠 **Reasoning Process**: Warm Amber Gold collapsible monologue block.
  - ⚙️ 🛠️ **Step Logs & Tool Calls**: Tech Slate / Cyan cards with collapsible step logs and observation output containers.
  - ✨ 💬 **Final Answers**: High-contrast Emerald Green cards.
- **Global Cross-Platform Emoji Support**: Added `Segoe UI Emoji`, `Apple Color Emoji`, and `Noto Color Emoji` fallback font rules.
