# 🤖 Multipurpose AI Assistant — by LocalAiLab

🇰🇭 **[ខ្មែរ](#-ខ្មែរ)** | 🇬🇧 **[English](#-english)**

---

## 🇰🇭 ខ្មែរ

ជំនួយការ AI ពហុមុខងារ ដោយ **LocalAiLab** ដែលដំណើរការនៅលើម៉ាស៊ីនរបស់អ្នកផ្ទាល់ បានបង្កើតឡើងដោយប្រើ [smolagents](https://github.com/huggingface/smolagents)។ មានចំណុចប្រទាក់ Gradio ការសន្ទនាទូទៅ វិភាគឯកសារតាមរយៈ RAG (Retrieval-Augmented Generation) ជាមួយការផ្ទុកទិន្នន័យជាប់លាប់ដោយ ChromaDB សមត្ថភាពពហុម៉ូដាល (រូបភាព/VLM) ការបំលែងសំឡេងទៅជាអក្សរ និងការវិភាគទិន្នន័យ CSV/Excel ដោយ AI Agent។ ប្រព័ន្ធនេះរកឃើញ និងប្រើ GPU (CUDA ឬ AMD) ដោយស្វ័យប្រវត្តិប្រសិនបើមាន ឬប្រើ CPU ជំនួសវិញ។ ក្រៅពីម៉ូដែល HuggingFace/transformers ជាលំនាំដើម កម្មវិធីនេះក៏អាចប្រើម៉ូដែលមូលដ្ឋាន **GGUF តាមរយៈ llama.cpp** ផងដែរ។

> ⚠️ **វេទិកា៖ Windows តែប៉ុណ្ណោះ។** ស្គ្រីបដំឡើង/ដំណើរការទាំងអស់ (`SETUP.bat/.ps1`, `RUN.bat/.ps1`, `install.bat/.ps1`) សរសេរជា PowerShell/Batch ហើយត្រូវការតែលើ Windows ប៉ុណ្ណោះ។ កម្មវិធីនេះ **មិនត្រូវបានគាំទ្រ ឬសាកល្បងលើ macOS (Mac) ទេ** — `requirements.txt` រួមមាន `bitsandbytes` ដែលជាធម្មតាមិនមាន wheel សម្រាប់ Apple Silicon/Intel Mac ដូច្នេះការដំឡើងអាចនឹងបរាជ័យតាំងពីជំហានដំបូង។ សូមមើលផ្នែក "🍎 macOS" ខាងក្រោមសម្រាប់ព័ត៌មានលម្អិត។

ចំណុចប្រទាក់អាចប្តូរភាសាបានភ្លាមៗ (**ខ្មែរ** ⇄ **អង់គ្លេស**) នៅជ្រុងខាងលើស្តាំ។ ផ្ទាំង **ℹ️ អំពីកម្មវិធី** បង្ហាញព័ត៌មានទាំងពីរភាសាជានិច្ច (ខ្មែរខាងលើ អង់គ្លេសខាងក្រោម) ដោយមិនអាស្រ័យលើបញ្ជីទម្លាក់ភាសានោះទេ។

### 🆕 អ្វីដែលថ្មីក្នុងកំណែ 0.0.3 beta

- **📦 កម្មវិធីដំឡើង Setup Wizard (`LocalAiLab_Setup_v0.0.3.exe`)**៖ បង្កើតឡើងដោយ Inno Setup ដែលអនុញ្ញាតឱ្យអ្នកប្រើប្រាស់ជ្រើសរើសផ្លូវដំឡើង (ឧ. `E:\LocalAiLab`) បង្ហាញរបារកើនឡើង Progress Bar (0%–100%) ជាមួយព័ត៌មានលម្អិតបន្តផ្ទាល់ ( live status) ពេលដំឡើង `.venv` & PyTorch/dependencies មានប៊ូតុង **បោះបង់ (Cancel)** អាចចុចនិងបង្ខំបិទបាន និងបង្កើត shortcut លើ Desktop/Start Menu ដោយស្វ័យប្រវត្តិ
- **⚙️ Accordion "ការកំណត់ម៉ូដែល" ជាសកល**៖ ការកំណត់ provider/backend រួម (HF API token/model/provider, LiteLLM, ផ្លូវ `llama-server.exe`, ផ្លូវ `whisper-server.exe`, ថតម៉ូដែល GGUF) ត្រូវបានប្រមូលផ្តុំក្នុង accordion តែមួយនៅផ្នែកខាងលើកម្មវិធី។ ចំណែក **provider + model dropdown របស់ផ្ទាំងនីមួយៗ (និងប៊ូតុង Load/Unload)** នៅតែស្ថិតនៅក្នុងជ្រុងខាងស្តាំរបស់ផ្ទាំងនោះផ្ទាល់ (មិនមែនប្រមូលទៅក្នុង accordion កណ្តាលនោះទេ)។ ការកំណត់ Generation (វិន្ដូបរិបទ, Max New Tokens, ប្តូរបិទ/បើក Reasoning, "💥 ទំនេរ VRAM ទាំងអស់") សុទ្ធតែស្ថិតនៅផ្ទាំង 💬 ការសន្ទនាទូទៅ ប៉ុន្តែមានឥទ្ធិពលទៅលើកម្មវិធីទាំងមូល ព្រោះវារក្សាទុកជា setting សកល
- **🔗 LiteLLM provider**៖ ក្រៅពី HuggingFace API អ្នកអាចភ្ជាប់ទៅ OpenAI/Anthropic/Groq/… ណាមួយដែល LiteLLM គាំទ្រ តាមរយៈ Model ID + API Key + API Base ផ្ទាល់ខ្លួន (មានតែសម្រាប់ LLM tab ប៉ុណ្ណោះ មិនមែន VLM/STT/Embedding ទេ)
- **🖥️ whisper.cpp server backend** (`whisper_cpp_backend.py`)៖ STT អាចដំណើរការតាមរយៈ `whisper-server.exe` ដោយមានការគ្រប់គ្រង subprocess និង model discovery ដោយស្វ័យប្រវត្តិ
- **🖥️ Embedding server**៖ ម៉ូដែល GGUF embedding អាចដំណើរការតាមរយៈ llama.cpp `/v1/embeddings` (`EmbeddingServerModel`)
- **🌐 Hugging Face Inference API**៖ គ្រប់ប្រភេទម៉ូដែល (LLM, VLM, STT, Embedding) អាចប្រើម៉ូដែលពីចម្ងាយ (DeepInfra, Together, Replicate ៘) — មាន provider dropdown ផ្ទាល់ខ្លួនតាមផ្ទាំង
- **តម្រងម៉ូដែលតាម Provider**៖ ពេលប្តូរ provider ក្នុងផ្ទាំងណាមួយ បញ្ជីម៉ូដែលនឹងត្រងចេញតែម៉ូដែលដែលត្រូវគ្នាដោយស្វ័យប្រវត្តិ
- **រក្សាទុក Provider តាមផ្ទាំង**៖ ផ្ទាំងនីមួយៗនឹងចងចាំ provider និងម៉ូដែលដែលបានជ្រើសរើស សូម្បីតែបិទបើកកម្មវិធីឡើងវិញ (តាមរយៈ `user_config.json`)
- **🖥️ Backend GGUF ពីរបែប**៖ ជ្រើសរើសបានក្នុងគ្រប់ផ្ទាំង LLM/VLM/Embedding តាមរយៈ provider dropdown របស់ផ្ទាំងនោះ — **"🧩 Local HuggingFace"** ដំណើរការក្នុងដំណើរការតែមួយ (in-process, `llama-cpp-python`) ឬ **"🖥️ llama.cpp server"** ដែលហៅ `llama-server.exe` ខាងក្រៅ (កំណត់ផ្លូវវានៅ accordion "⚙️ ការកំណត់ម៉ូដែល" ផ្នែក Provider/Backend)
- **🔬 ផ្ទាំង Deep Research**៖ agent គ្រប់គ្រង + agent ស្វែងរកតាមអ៊ីនធឺណិតដាច់ដោយឡែក (`ToolCallingAgent`) បំបែកសំណួរជាសំណួររង រៀបចំផែនការឡើងវិញឥតឈប់ឈរ រួចសរសេររបាយការណ៍ Markdown
- **ស្វែងរកតាមអ៊ីនធឺណិតដោយឥតគិតថ្លៃ**៖ លំនាំដើមប្រើ `DuckDuckGoSearchTool` របស់ smolagents ខ្លួនឯង (តាមរយៈ `ddgs`) — មិនត្រូវការ API key ទេ។ ផ្ទាំង 🔬 ស្រាវជ្រាវស៊ីជម្រៅ ក៏មានប្រអប់ជម្រើស "Use Playwright (Headless Browser) Tools" ដែលបើកឧបករណ៍ browser ជាក់ស្តែងសម្រាប់ស្វែងរក/អាន PDF/extract links ដែលមានប្រយោជន៍លើទំព័រដែលត្រូវការ JavaScript
- **ម៉ូដែលថ្មី**៖ **Gemma 4** (E2B/12B/26B-A4B/31B) និង **Qwen3.6** (27B / 35B-A3B MoE)
- **🧠 ចងចាំការសន្ទនា (កំពុងសាកល្បង)**៖ ប្រអប់ថ្មីនៅគ្រប់ផ្ទាំង agentic
- **🧠 វិន្ដូបរិបទ**៖ ជ្រើសរើសពី 4K ដល់ 128K សម្រាប់ GGUF (នៅផ្ទាំង 💬 ការសន្ទនាទូទៅ — អនុវត្តជាសកល)
- **ការរកឃើញ GPU មិនត្រូវគ្នា**៖ ព្រមានក្នុង UI ជំនួសឱ្យការគាំងស្ងាត់ៗ
- **Data Analysis Agent**៖ ដំឡើង Python package ដោយខ្លួនឯង EDA ពេញលេញ **និងជម្រើសវិភាគតាមប្រភេទ (ការលក់, អតិថិជន, ហិរញ្ញវត្ថុ, ប្រាក់ខែ)** — ជ្រើសរើស workflow ដើម្បីបំពេញប្រអប់សំណួរដោយស្វ័យប្រវត្តិ
- **🔧 ជ្រើសរើស Embedding ឥតបញ្ហា**៖ ChromaDB បង្កើត collection ដាច់ដោយឡែកតាម dimension

### 📑 មាតិកា
- [ស្ថាបត្យកម្ម](#️-ស្ថាបត្យកម្ម)
- [ការចាប់ផ្តើមរហ័ស](#-ការចាប់ផ្តើមរហ័ស)
- [ចំណុចប្រទាក់អ្នកប្រើប្រាស់](#️-ចំណុចប្រទាក់អ្នកប្រើប្រាស់)
- [ការកំណត់ម៉ូដែល](#️-ការកំណត់ម៉ូដែល)
- [រចនាសម្ព័ន្ធឯកសារ](#-រចនាសម្ព័ន្ធឯកសារ)

---

### 🏗️ ស្ថាបត្យកម្ម

| សមាសធាតុ | លំនាំដើម |
|---|---|
| LLM | `Qwen/Qwen3-0.6B` (HuggingFace) **ឬ** `.gguf` តាមរយៈ llama.cpp **ឬ** ពីចម្ងាយតាមរយៈ Inference API |
| Vision LLM | `HuggingFaceTB/SmolVLM-500M-Instruct` (HuggingFace) **ឬ** GGUF តាមរយៈ llama.cpp **ឬ** ពីចម្ងាយតាមរយៈ Inference API |
| Speech-to-Text | `openai/whisper-small` (HuggingFace) **ឬ** whisper.cpp server **ឬ** ពីចម្ងាយតាមរយៈ Inference API |
| Embedding | `BAAI/bge-m3` (HuggingFace) **ឬ** GGUF តាមរយៈ llama.cpp server **ឬ** ពីចម្ងាយតាមរយៈ Inference API |
| Visual Retriever | `vidore/colsmolvlm-v0.1` |
| Vector store | ChromaDB (`./chroma_db/`) |
| Visual Index | `vidore/colsmolvlm-v0.1` (`./visual_index/`) |
| ប្រភេទឯកសារបញ្ចូល | PDF, TXT, MD, DOCX |
| ប្រភេទភ្នាក់ងារ | `CodeAgent` (General/RAG/Data Analysis); `ToolCallingAgent` (Deep Research search sub-agent) |
| UI | Gradio |

> **ចំណាំ**៖ `HardwareManager` រកឃើញផ្នែករឹងរបស់អ្នកដោយស្វ័យប្រវត្តិ (NVIDIA ឬ AMD) ហើយអាចជួយជួសជុលបរិយាកាសរបស់អ្នកតាមរយៈប៊ូតុង "Fix Environment" ក្នុងចំណុចប្រទាក់។ កូដមាន logic ដែលអាចរកឃើញ Apple Silicon (MPS) ដែរ ប៉ុន្តែនេះជា **Windows tool** ដែលមិនត្រូវបានសាកល្បង ឬគាំទ្រជាផ្លូវការលើ macOS ទេ (សូមមើលផ្នែក "🍎 macOS" ខាងក្រោម)។

---

### 🚀 ការចាប់ផ្តើមរហ័ស

#### ១. ដំឡើង Dependencies

```bash
# បង្កើត venv (មិនចាំបាច់ ប៉ុន្តែគួរធ្វើ)
python -m venv .venv && source .venv/bin/activate

# ដំឡើង dependencies ស្នូល (រូបភាព សំឡេង និងការដកស្រង់អត្ថបទ រួមទាំង python-docx)
pip install -r requirements.txt

# ដំឡើង PyTorch (រកឃើញ CUDA/MPS/AMD ដោយស្វ័យប្រវត្តិប្រសិនបើមាន)
pip install torch torchvision
```

#### 📦 ជម្រើស ១ — ដំឡើងតាមរយ: Windows Setup Wizard (ណែនាំសម្រាប់អ្នកប្រើប្រាស់)

ទាញយក និងដំណើរការ **`Output\LocalAiLab_Setup_v0.0.3.exe`**៖
- អនុញ្ញាតឱ្យអ្នកជ្រើសរើសផ្លូវដំឡើងដែលចង់បាន (ឧ. `E:\LocalAiLab`)
- ដំណើរការបង្កើត `.venv` និងដំឡើង PyTorch + AI dependencies ទាំងអស់ដោយស្វ័យប្រវត្តិ ជាមួយការបង្ហាញ progress bar (0%–100%)
- មានប៊ូតុង Cancel អាចចុចបោះបង់ការដំឡើងបានគ្រប់ពេល
- បង្កើត Shortcut លើ Desktop និង Start Menu ដោយស្វ័យប្រវត្តិ

#### 💻 ជម្រើស ២ — ដំឡើងតាមរយ: ស្គ្រីប បន្ទាត់តែមួយ

```powershell
iwr -useb https://raw.githubusercontent.com/aidgcreator-prog/LocalAILab/smolagent_modular/install.ps1 | iex
```

ពាក្យបញ្ជាតែមួយនេះ ដំឡើង Python + Git (បើគ្មាន) ទាញយក repo បង្កើត Python environment រកឃើញ GPU ដំឡើង PyTorch + dependencies ទាំងអស់ និងបង្កើត shortcut លើ Desktop។

បើម៉ាស៊ីនអ្នកមាន Python រួចហើយ គ្រាន់តែចុចពីរដងលើ **SETUP.bat** ដើម្បីធ្វើ GPU detection + dependency install ដោយស្វ័យប្រវត្តិ។

<details>
<summary><strong>ជម្រើស — ការគាំទ្រម៉ូដែល llama.cpp (GGUF)</strong></summary>

`llama-cpp-python` មិនត្រូវបានដំឡើងដោយស្វ័យប្រវត្តិទេ។ ដើម្បីប្រើម៉ូដែល GGUF (.gguf) អ្នកមានជម្រើសពីរ៖

**ជម្រើស A — Backend ខាងក្រៅ (ងាយស្រួលបំផុត)៖** ទាញយក `llama-server.exe` ពី [llama.cpp releases](https://github.com/ggerganov/llama.cpp/releases) ហើយកំណត់ផ្លូវរបស់វានៅ accordion "⚙️ ការកំណត់ម៉ូដែល" (ផ្នែក Provider/Backend) → "🖥️ llama-server.exe Path" នៅផ្នែកខាងលើកម្មវិធី។ បន្ទាប់មកនៅផ្ទាំងណាដែលចង់ប្រើ (💬/📚/📊/🔬) ជ្រើសរើស "🖥️ llama.cpp server" ក្នុងបញ្ជីទម្លាក់ Provider ផ្ទាល់របស់ផ្ទាំងនោះ។ មិនតម្រូវឱ្យដំឡើង Python package អ្វីទាំងអស់។

**ជម្រើស B — In-process (llama-cpp-python)៖** ដំឡើងដោយខ្លួនឯង៖

```powershell
pip install llama-cpp-python
```

សម្រាប់ GPU acceleration (CUDA):

```powershell
pip uninstall llama-cpp-python -y
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124 --force-reinstall --no-cache-dir
```

ប្តូរ `cu124` ទៅជាកំណែ CUDA ដែលត្រូវនឹង driver របស់អ្នក (`nvidia-smi` បង្ហាញវា)។ ប្រសិនបើ wheel គាំង ("Illegal Instruction") សូមសាងសង់ពី source ជំនួសវិញ៖

```powershell
$env:CMAKE_ARGS = "-DGGML_CUDA=on"
$env:FORCE_CMAKE = "1"
pip install llama-cpp-python --no-cache-dir --force-reinstall
```

**ថតម៉ូដែល GGUF**៖ ដាក់ឯកសារ `.gguf` ទៅក្នុងថតណាមួយ។ កំណត់ថតតាមរយៈអថេរបរិស្ថាន `LLAMA_CPP_MODEL_DIR` ឬវាយផ្លូវក្នុងប្រអប់ "📁 ថតម៉ូដែល GGUF" នៅក្នុង UI រួចចុច "🔍 ស្កេន"។

</details>

<details>
<summary><strong>🍎 macOS (Mac) — មិនត្រូវបានគាំទ្រ</strong></summary>

កម្មវិធីនេះ **មិនអាចដំណើរការលើ macOS បានទេ** ក្នុងស្ថានភាពបច្ចុប្បន្ន៖

- `SETUP.bat`/`SETUP.ps1`, `RUN.bat`/`RUN.ps1` និង `install.bat`/`install.ps1` សុទ្ធតែជាស្គ្រីប PowerShell/Batch ដែលមិនអាចដំណើរការនៅលើ Mac ទាល់តែសោះ — គ្មានវិធីចាប់ផ្តើមកម្មវិធីតាមរបៀបធម្មតាទេ។
- `requirements.txt` រួមមាន `bitsandbytes>=0.43.0` ដែលជាធម្មតាគ្មាន wheel ត្រឹមត្រូវសម្រាប់ Apple Silicon ឬ Intel Mac ទេ — `pip install -r requirements.txt` អាចនឹងបរាជ័យតាំងពីដើម។
- ការណែនាំបង្កើត `llama-cpp-python` ជាមួយ GPU (សូមមើលខាងលើ) ប្រើតែ `-DGGML_CUDA=on` (NVIDIA) ប៉ុណ្ណោះ — គ្មានការណែនាំ/សាកល្បងសម្រាប់ Metal (`-DGGML_METAL=on`) លើ Mac ទេ។
- ការបញ្ចូល PDF បែបចក្ខុវិស័យត្រូវការ Poppler ដែលការណែនាំដំឡើងក្នុង README នេះសរសេរសម្រាប់ Windows តែប៉ុណ្ណោះ។

ទោះបីជា `hardware.py` មាន logic រកឃើញ `torch.backends.mps` (Apple Silicon GPU) ក៏ដោយ វាមិនមានន័យថាកម្មវិធីទាំងមូលត្រូវបានសាកល្បង ឬគាំទ្រលើ macOS ទេ — មិនមានផ្លូវដំឡើងជាផ្លូវការ មិនមានការធានា និងគ្មានផែនការគាំទ្រ Mac ជាផ្លូវការទេនាពេលនេះ។

</details>

#### ២. បញ្ចូលឯកសាររបស់អ្នក

**តាមរយៈ CLI:**

```bash
python index_docs.py --pdf ./docs/my_paper.pdf        # PDF
python index_docs.py --txt ./docs/notes.md            # TXT/MD
python index_docs.py --docx ./docs/report.docx        # DOCX
python index_docs.py --dir ./docs                     # ថតទាំងមូល (auto-detect)
python index_docs.py --hf-dataset m-ric/huggingface_doc --text-col text --source-col source
python index_docs.py --stats                          # បង្ហាញស្ថិតិ
python index_docs.py --clear                          # សម្អាតទាំងអស់
```

**តាមរយៈចំណុចប្រទាក់ (UI):** ចាប់ផ្តើមកម្មវិធី ហើយប្រើផ្ទាំង **📂 មូលដ្ឋានចំណេះដឹង**។ អាចទម្លាក់ឯកសារ PDF, TXT, MD ឬ DOCX។

#### ៣. ដំណើរការកម្មវិធី

```bash
python app.py
```

ឬនៅលើ Windows ចុចពីរដងលើ **RUN.bat**។ បើកកម្មវិធីរុករកតាមអាសយដ្ឋាន [http://localhost:7861](http://localhost:7861) (ច្រកលំនាំដើម **7861** ជៀសវាងការប៉ះទង្គិចនឹង Gradio លំនាំដើម 7860 — ប្តូរបានតាមរយៈ `server_port` នៅក្នុង `app.py`)។

---

### 🖥️ ចំណុចប្រទាក់អ្នកប្រើប្រាស់

កម្មវិធីនេះមានផ្ទាំងសំខាន់ៗចំនួនប្រាំបី តាមលំដាប់ដូចខាងក្រោម៖

| # | ផ្ទាំង | ការពិពណ៌នា |
|---|---|---|
| 1 | 💬 **ការសន្ទនាទូទៅ** | ការសន្ទនាផ្ទាល់ជាមួយ LLM — មិនមានការទាញយកឯកសារ។ របៀប Agent (ស្រេចចិត្ត) អាចស្វែងរកតាមអ៊ីនធឺណិត |
| 2 | 🖼️ **ការសន្ទនាចក្ខុវិស័យ** | បង្ហោះរូបភាព ហើយសួរសំណួរ — គាំទ្រការទាញយកបរិបទចម្រុះ និង Visual RAG |
| 3 | 🎙️ **និយាយទៅជាអក្សរ** | ថត/បង្ហោះសំឡេង ហើយបំលែងទៅជាអក្សរដោយ Whisper (រកឃើញភាសាស្វ័យប្រវត្តិ ឬកំណត់ភាសាផ្ទាល់) |
| 4 | 📊 **វិភាគទិន្នន័យ** | បង្ហោះ CSV/Excel ឱ្យ AI Agent វិភាគ បង្កើតក្រាហ្វិក និងសរសេររបាយការណ៍ Markdown — មានជម្រើស workflow វិភាគតាមប្រភេទ (ការលក់, អតិថិជន, ហិរញ្ញវត្ថុ, ប្រាក់ខែ) |
| 5 | 📂 **មូលដ្ឋានចំណេះដឹង** | គ្រប់គ្រងឯកសារដែលបានបញ្ចូល (PDF/TXT/MD/DOCX) មើលតារាង និងសម្អាតការបញ្ចូល |
| 6 | 📚 **ការសន្ទនា RAG** | ទាញយកពីមូលដ្ឋានចំណេះដឹងជាមុន (ដោយផ្ទាល់ ឬដោយ Agent) មុននឹងឆ្លើយ |
| 7 | 🔬 **ស្រាវជ្រាវស៊ីជម្រៅ** | Agent គ្រប់គ្រង + agent ស្វែងរកតាមអ៊ីនធឺណិត បំបែកសំណួរជាសំណួររង រៀបចំផែនការឡើងវិញ រួចសរសេររបាយការណ៍ Markdown ដែលមានប្រភពយោង (ត្រូវការម៉ូដែលធំ)
| 8 | ℹ️ **អំពីកម្មវិធី** | ស្ថានភាពប្រព័ន្ធ ស្ថាបត្យកម្ម និងល្បឿនរំពឹងទុក — បង្ហាញជានិច្ចជាភាសាខ្មែរនិងអង់គ្លេសទាំងពីរ |

#### លក្ខណៈពិសេសសំខាន់ៗ
- **ចំណុចប្រទាក់ពីរភាសា**៖ ខ្មែរ/អង់គ្លេស ប្តូរបានភ្លាមៗតាមបញ្ជីទម្លាក់ភាសា
- **ម៉ូដែលច្រើនប្រភេទ Backend**៖ HuggingFace/transformers (in-process), local server (llama.cpp / whisper.cpp), ពីចម្ងាយតាមរយៈ Hugging Face Inference API, ឬ (សម្រាប់ LLM) LiteLLM (OpenAI/Anthropic/Groq/…) — ជ្រើសរើសដោយឡែកតាមផ្ទាំង
- **ការកំណត់ម៉ូដែល**៖ ការកំណត់ provider/backend រួម (HF API, LiteLLM, ផ្លូវ llama-server.exe/whisper-server.exe, ថត GGUF) ស្ថិតក្នុង accordion សកលមួយ; provider + model dropdown របស់ផ្ទាំងនីមួយៗ (៧ ផ្ទាំង) ស្ថិតនៅជ្រុងសាយប៊ែររបស់ផ្ទាំងនោះ; generation settings (context window, max tokens, reasoning) ស្ថិតនៅផ្ទាំង 💬 ការសន្ទនាទូទៅ ប៉ុន្តែអនុវត្តជាសកល
- **ចងចាំការសន្ទនា (កំពុងសាកល្បង)**៖ ប្រអប់ "🧠 ចងចាំការសន្ទនា" នៅគ្រប់ផ្ទាំង agentic — បើកដើម្បីឱ្យសំណួរបន្តអាចយោងលើអ្វីដែលបាននិយាយពីមុន។ ការចងចាំមាននៅតែក្នុងវគ្គដំណើរការបច្ចុប្បន្នប៉ុណ្ណោះ (មិនរក្សាទុកទៅថាសទេ) ហើយនឹងត្រូវកំណត់ចេញនៅពេលប្តូរម៉ូដែល ចុច "សម្អាត" ឬចាប់ផ្តើមកម្មវិធីឡើងវិញ
- **ការគាំទ្រឯកសារ DOCX**៖ ការបញ្ចូលឯកសារគាំទ្រ Word (.docx) រួមទាំងអត្ថបទក្នុងតារាង
- **ការជួសជុលបរិយាកាសដោយខ្លួនឯង**៖ ប៊ូតុង "Fix Environment" ដំឡើង PyTorch ត្រឹមត្រូវសម្រាប់ GPU របស់អ្នកដោយស្វ័យប្រវត្តិ
- **ភាពមើលឃើញនៃការគិត**៖ ស្លាក `<think>` របស់ម៉ូដែលបង្ហាញជាផ្នែកដែលអាចពង្រីក/បង្រួមបាន
- **ការជ្រើសរើស Visual Retriever**៖ ជ្រើសរើសរវាង `colsmolvlm` ឬ `colqwen2` ដោយផ្ទាល់ក្នុងចំណុចប្រទាក់

---

### ⚙️ ការកំណត់ម៉ូដែល

អ្នកអាចប្តូរម៉ូដែលនៅពេលដំណើរការ តាមរយៈបញ្ជីទម្លាក់ក្នុងចំណុចប្រទាក់។

<details open>
<summary><strong>Text LLMs</strong></summary>

| VRAM/RAM | ម៉ូដែលដែលណែនាំ |
|---|---|
| ~1.2 GB | `Qwen/Qwen3-0.6B` (លឿនបំផុត — លំនាំដើម) |
| ~3 GB | `Qwen/Qwen3-1.7B` |
| ~6 GB | `Qwen/Qwen2.5-Coder-3B-Instruct` (small coding/agent model) |
| ~7 GB | `Qwen/Qwen3-4B` |
| ~4 GB | `google/gemma-4-E2B-it` |
| ប្រែប្រួល | ម៉ូដែល `.gguf` ណាមួយនៅក្នុងថតដែលអ្នកកំណត់ (តាមរយៈ llama.cpp) |

</details>

<details open>
<summary><strong>Vision LLMs (VLM)</strong></summary>

| RAM | ម៉ូដែលដែលណែនាំ |
|---|---|
| ~0.5 GB | `HuggingFaceTB/SmolVLM-256M-Instruct` |
| ~1 GB | `HuggingFaceTB/SmolVLM-500M-Instruct` (ណែនាំ — លំនាំដើម) |
| ~6 GB | `Qwen/Qwen2.5-VL-3B-Instruct` |
| ប្រែប្រួល | គូម៉ូដែល GGUF (main + mmproj) នៅក្នុងថត llama.cpp របស់អ្នក |

</details>

<details open>
<summary><strong>Speech-to-Text (Whisper)</strong></summary>

| RAM | ម៉ូដែលដែលណែនាំ |
|---|---|
| ~1 GB | `openai/whisper-tiny` (លឿនបំផុត) |
| ~1 GB | `openai/whisper-base` |
| ~2 GB | `openai/whisper-small` (ណែនាំ — លំនាំដើម) |
| ~10 GB | `openai/whisper-large-v3` (ត្រឹមត្រូវបំផុត — ច្រើនភាសារួមទាំងខ្មែរ) |
| ~1 GB | `seanghay/whisper-small-khmer-v2` 🇰🇭 (កែសម្រួលសម្រាប់ខ្មែរ) |
| ~6 GB | `metythorn/whisper-large-v3-turbo-mixed-20eps-clean-text-197k` 🇰🇭 (ល្អបំផុតសម្រាប់ខ្មែរ) |

</details>

<details open>
<summary><strong>ជម្រើសម៉ូដែលតាមកម្រិតផ្នែករឹង (ជម្រើសកម្រិតខ្ពស់ជាង)</strong></summary>

តារាងខាងក្រោមផ្តល់ជូននូវសំណុំម៉ូដែល GGUF ដែលមានសមត្ថភាពខ្ពស់ជាងសម្រាប់អ្នកប្រើប្រាស់ដែលមានផ្នែករឹងខ្លាំង — ត្រូវទាញយក ហើយកំណត់ចេញពី "📁 ថតម៉ូដែល GGUF" ដូចម៉ូដែល `.gguf` ផ្សេងទៀត។

| ផ្នែករឹង | ម៉ូដែល Agent (សន្ទនា/Data Analysis) | ម៉ូដែល RAG | ម៉ូដែលចក្ខុវិស័យ (HF/transformers) | ម៉ូដែល Embedding |
|---|---|---|---|---|
| **CPU តែប៉ុណ្ណោះ (64–128 GB RAM)** | **Qwen3.6-35B-A3B (GGUF, MoE — ត្រូវការតែ ~3B active params/token ដូច្នេះលឿននៅលើ CPU)**<br>https://huggingface.co/ggml-org/Qwen3.6-35B-A3B-GGUF | **Gemma-4-12B-it (GGUF)**<br>https://huggingface.co/ggml-org/gemma-4-12B-it-GGUF | **Qwen2.5-VL-7B-Instruct (GGUF)**<br>https://huggingface.co/unsloth/Qwen2.5-VL-7B-Instruct-GGUF | **BGE-M3**<br>https://huggingface.co/BAAI/bge-m3 |
| **8 GB VRAM** | **Qwen3-8B (GGUF)**<br>https://huggingface.co/Qwen/Qwen3-8B-GGUF | **Gemma-4-12B-it (GGUF) — ⚠️ តឹងចង្អៀត សូមមើលចំណាំខាងក្រោម** (ដូចខាងលើ) | **Qwen2.5-VL-7B-Instruct (GGUF)** (ដូចខាងលើ) | **BGE-M3** (ដូចខាងលើ) |
| **16 GB VRAM** | **Qwen3-14B (GGUF)**<br>https://huggingface.co/MaziyarPanahi/Qwen3-14B-GGUF | **Gemma-4-12B-it (GGUF)** (ដូចខាងលើ) | **Qwen2.5-VL-7B-Instruct (GGUF)** (ដូចខាងលើ) | **BGE-M3** (ដូចខាងលើ) |
| **24 GB VRAM** | **Qwen3-32B (GGUF)**<br>https://huggingface.co/MaziyarPanahi/Qwen3-32B-GGUF | **Gemma-4-26B-A4B-it (GGUF)**<br>https://huggingface.co/unsloth/gemma-4-26B-A4B-it-GGUF | **Gemma-4-12B-it (GGUF)**<br>https://huggingface.co/ggml-org/gemma-4-12B-it-GGUF | **Qwen3-Embedding-4B**<br>https://huggingface.co/Qwen/Qwen3-Embedding-4B |
| **48 GB+ VRAM** | **Qwen3-32B (GGUF)** (ដូចខាងលើ) | **Gemma-4-31B-it (GGUF)**<br>https://huggingface.co/ggml-org/gemma-4-31B-it-GGUF | **Gemma-4-31B-it (GGUF)** (ដូចខាងលើ) | **Jina Embeddings v4**<br>https://huggingface.co/jinaai/jina-embeddings-v4 |

> ⚠️ **ចំណាំពិសេសអំពី 8 GB VRAM**៖ `Gemma-4-12B-it` នៅ Q4_K_M ត្រូវការទំហំ weight ត្រឹមតែ ~7.4 GB ដោយខ្លួនឯង — នេះស្ទើរតែមិនទុកទំហំសម្រាប់ KV cache ទេនៅលើកាត 8GB ជាពិសេសបើ Context Window (សូមមើលបញ្ជីទម្លាក់ "🧠 វិន្ដូបរិបទ" ក្នុង UI) ត្រូវបានកំណត់ធំជាង 8K។ ប្រសិនបើអ្នកជួប OOM លើកម្រិតនេះ សូមបន្ថយ Context Window ជាមុនសិន ឬប្តូរទៅ `Gemma-4-E4B-it` ដែលស្រាលជាង។
>
> **CPU តែប៉ុណ្ណោះ**៖ ចាប់តាំងពី Qwen3.6-35B-A3B ជាម៉ូដែល MoE (ត្រូវការតែ ~3B active parameters ក្នុងមួយ token ទោះបីជាទំហំសរុប 35B) វាដំណើរការបានលឿនគួរសមនៅលើ CPU ដែលមាន RAM 64–128GB — ខុសពីម៉ូដែល dense ដូចជា Qwen3-8B ដែលត្រូវការគណនាគ្រប់ parameter ទាំងអស់ជានិច្ច។

> ⚠️ **សំខាន់**៖ `Gemma-4-12B-it` / `Gemma-4-31B-it` ខ្លួនវាផ្ទាល់ជាម៉ូដែលចក្ខុវិស័យ (image-in, encoder-free) ដែរ ប៉ុន្តែកម្មវិធីនេះមិនទាន់ស្គាល់ chat-handler របស់វានៅឡើយទេ (`llama_backend.py` បច្ចុប្បន្នស្គាល់តែ LLaVA/MiniCPM-V/Moondream/nanoLLaVA) — ដូច្នេះការប្រើវាជា "🎨 Vision LLM" (GGUF) ក្នុងកម្មវិធីនេះ ត្រូវការកែកូដបន្ថែមសិន។ `Qwen2.5-VL-7B-Instruct` (HuggingFace/transformers) នៅតែជាជម្រើសសុវត្ថិភាពបំផុតដែលដំណើរការភ្លាមៗ។ ចំណែក `Qwen3-VL` (ជំនាន់ថ្មីជាង Qwen2.5-VL) ត្រូវបានគាំទ្រដោយ llama.cpp ចាប់តាំងពីចុងខែតុលា ២០២៥ តាមរយៈឧបករណ៍ `llama-mtmd-cli`/`llama-server` ថ្មី ប៉ុន្តែក៏ត្រូវការការកែសម្រួល `llama_backend.py` ដូចគ្នា មុននឹងអាចប្រើក្នុងកម្មវិធីនេះបាន។

</details>

---

### 📂 រចនាសម្ព័ន្ធឯកសារ

```
.
├── app.py            # ចំណុចចូលកម្មវិធី (launch) — ឡូជិកពិតត្រូវបានបំបែកទៅជាម៉ូឌុលខាងក្រោម
├── i18n.py           # ខ្សែអក្សរចំណុចប្រទាក់ (ខ្មែរ/អង់គ្លេស)
├── hardware.py       # ការរកឃើញ GPU/Device និងការជួសជុលបរិយាកាសដោយខ្លួនឯង
├── user_config.py    # ការកំណត់ដែលរក្សាទុក (ឧ. ថតម៉ូដែល GGUF, context window)
├── llama_backend.py        # backend ជម្រើស llama.cpp (ម៉ូដែល GGUF, text + vision)
├── whisper_cpp_backend.py  # backend ជម្រើស whisper.cpp (STT តាមរយៈ subprocess server)
├── branding.py             # ស្លាកសញ្ញា ឈ្មោះកម្មវិធី/កំណែ និងមាតិកាផ្ទាំង ℹ️ អំពីកម្មវិធី
├── model_registry.py # បញ្ជីជម្រើសម៉ូដែល (LLM/VLM/STT) និងការស្កេន GGUF ឡើងវិញ
├── models.py         # ការផ្ទុក/ដោះស្រាយ/ដំណើរការ LLM, VLM, STT
├── knowledge_base.py # ការបញ្ចូលឯកសារ (PDF/TXT/MD/DOCX), ChromaDB, Visual Index, ការទាញយក
├── agent_memory.py   # ការចងចាំចម្រុះវេនសម្រាប់ CodeAgent (RAM តែប៉ុណ្ណោះ — មិនរក្សាទុកទៅថាសទេ)
├── general_agent.py  # CodeAgent សម្រាប់ការសន្ទនាទូទៅបែប Agent (web search)
├── rag_agent.py      # CodeAgent សម្រាប់ RAG បែប Agent (retriever tool)
├── deep_research_agent.py # Agent គ្រប់គ្រង + ToolCallingAgent ស្វែងរកតាមអ៊ីនធឺណិត សម្រាប់ស្រាវជ្រាវស៊ីជម្រៅ
├── data_analysis.py  # CodeAgent សម្រាប់វិភាគ CSV/Excel
├── playwright_search_tool.py # Playwright + DuckDuckGo search tools (ជំនួស SerpAPI ដែលត្រូវចំណាយលុយ)
├── agent_streaming.py  # ការផ្សាយបន្តផ្ទាល់ ActionStep/PlanningStep សម្រាប់គ្រប់ផ្ទាំង agentic
├── chat.py           # Handler សន្ទនាសម្រាប់ផ្ទាំង General/RAG/Vision
├── ui.py             # ការសង់ចំណុចប្រទាក់ Gradio និងការភ្ជាប់ event ទាំងអស់
├── index_docs.py     # ស្គ្រីប CLI សម្រាប់បញ្ចូលឯកសារ
├── requirements.txt   # Dependencies របស់ Python (រួមទាំង python-docx)
├── SETUP.bat/.ps1    # កម្មវិធីដំឡើងលើ Windows (GPU detection, venv, deps)
├── RUN.bat/.ps1      # កម្មវិធីដំណើរការលើ Windows ដោយចុចតែម្តង
├── install.bat/.ps1  # កម្មវិធីដំឡើងតាមអ៊ីនធឺណិត (Python+Git+clone+setup+shortcut)
├── installer.iss     # ស្គ្រីប Inno Setup GUI Wizard (LocalAiLab_Setup_v0.0.3.exe)
├── BUILD_INSTALLER.bat # ស្គ្រីបសម្រាប់ compile installer.iss ទៅជា .exe
├── Output/           # ថតលទ្ធផល compile installer wizard (LocalAiLab_Setup_v0.0.3.exe)
├── README.md         # ឯកសារនេះ
├── chroma_db/        # បង្កើតដោយស្វ័យប្រវត្តិ; ការផ្ទុកទិន្នន័យជាប់លាប់របស់ ChromaDB
└── visual_index/     # បង្កើតដោយស្វ័យប្រវត្តិ; ការផ្ទុក Visual Index
```

---
---

## 🇬🇧 English

A local, multipurpose AI assistant built by **LocalAiLab** with [smolagents](https://github.com/huggingface/smolagents), featuring a Gradio UI, general chat, document RAG (Retrieval-Augmented Generation) with persistent ChromaDB storage, multi-modal capabilities (Vision/VLM), Speech-to-Text transcription, and AI-driven CSV/Excel data analysis. It automatically detects and uses your GPU (CUDA or AMD) if available, falling back to CPU otherwise. Besides the default HuggingFace/transformers models, the app can also run local **GGUF models via llama.cpp**.

> ⚠️ **Platform: Windows only.** Every install/launch script (`SETUP.bat/.ps1`, `RUN.bat/.ps1`, `install.bat/.ps1`) is PowerShell/Batch and only runs on Windows. This app is **not supported or tested on macOS (Mac)** — `requirements.txt` includes `bitsandbytes`, which typically has no working wheel for Apple Silicon or Intel Mac, so `pip install -r requirements.txt` can fail right at the start. See the "🍎 macOS" section below for details.

The UI is fully bilingual — switch between **Khmer** and **English** instantly using the language dropdown in the top-right corner. The **ℹ️ About** tab always shows both languages (Khmer above, English below), regardless of that dropdown.

### 🆕 What's New in Version 0.0.3 beta

- **📦 Windows GUI Setup Wizard (`LocalAiLab_Setup_v0.0.3.exe`)**: Built with Inno Setup. Allows users to choose any custom installation path (e.g. `E:\LocalAiLab`), shows a real-time progress bar (0%–100%) with live setup status during `.venv` creation & PyTorch/dependency installation, includes an active and enforceable **Cancel** button, and automatically creates Desktop & Start Menu shortcuts.
- **⚙️ Global "Model Settings" accordion**: shared provider/backend config (HF API token/model/provider, LiteLLM, `llama-server.exe` path, `whisper-server.exe` path, GGUF model folder) is collected into a single accordion near the top of the app. Each tab's own **provider dropdown + model dropdown + Load/Unload buttons** still live in that tab's own sidebar column (not moved into the central accordion). Generation settings (Context Window, Max New Tokens, the Reasoning toggle, "💥 Free All VRAM") live in the 💬 General Chat tab's sidebar, but apply app-wide since they're persisted global settings.
- **🔗 LiteLLM provider**: besides the HF Inference API, the LLM tab can now point at any OpenAI/Anthropic/Groq/etc. endpoint LiteLLM supports, via a Model ID + API Key + API Base you configure yourself (LLM only — not available for VLM/STT/Embedding).
- **🖥️ whisper.cpp server backend** (`whisper_cpp_backend.py`): STT can now run via a `whisper-server.exe` subprocess, with automatic model file discovery, port management, and settings persistence.
- **🖥️ Embedding server support**: GGUF embedding models can run via llama.cpp's `/v1/embeddings` endpoint (`EmbeddingServerModel`) — no separate local HuggingFace model needed for vector generation.
- **🌐 Hugging Face Inference API**: every model type (LLM, VLM, STT, Embedding) can now use remote models (e.g. `google/gemma-4-31B-it` via DeepInfra, Together, or Replicate) without loading anything locally — each with its own provider dropdown per tab.
- **Provider-aware model filtering**: changing the provider dropdown per tab automatically filters the companion model dropdown to show only compatible models.
- **Per-tab provider persistence**: each tab remembers its chosen provider and model across restarts via `user_config.json` keys (`provider_gen`, `provider_rag`, etc.).
- **🖥️ Dual GGUF backend**: selectable per tab via that tab's own provider dropdown — **"🧩 Local HuggingFace"** runs GGUF models in-process (`llama-cpp-python`), or **"🖥️ llama.cpp server"** talks to an external `llama-server.exe` (configure its path under the "⚙️ Model Settings" accordion's Provider/Backend section).
- **🔬 Deep Research overhaul**: the search sub-agent now uses `ToolCallingAgent` (instead of `CodeAgent`) for reliable structured tool calls, with `provide_run_summary=True` and `planning_interval=4` — matching the canonical `open_deep_research` pattern.
- **Free web search by default**: uses smolagents' own built-in `DuckDuckGoSearchTool` (via `ddgs`) — no paid API, no API key. Deep Research also offers an optional "Use Playwright (Headless Browser) Tools" checkbox for a real-browser search/read/PDF-extraction toolset, useful on JavaScript-heavy pages the default tools can't render.
- **New models**: added the **Gemma 4** family (E2B/12B/26B-A4B/31B, now Apache 2.0-licensed) and the **Qwen3.6** family (27B dense / 35B-A3B MoE) — both need a newer `transformers` release (see the Text LLMs table below).
- **🧠 Conversation Memory (Experimental)**: a new toggle on every agentic tab lets follow-up questions refer back to earlier turns (RAM-only, never persisted to disk).
- **🧠 Configurable Context Window**: pick anywhere from 4K to 128K tokens for GGUF models directly in the UI (General Chat tab's sidebar — applies globally).
- **GPU-incompatibility detection**: the UI now shows a clear warning if a detected GPU (e.g. an older Pascal/sm_6x card) isn't supported by the installed PyTorch build, instead of silently falling back to CPU with no explanation.
- **Data Analysis agent** can now install missing Python packages itself (`install_package` tool), runs a fuller EDA with multiple charts, **and offers guided analysis workflows (Sales, Customer, Financial, Payroll) via an Analysis Type selector** — pick a workflow to pre-fill the question box with step-by-step instructions.

### 📑 Table of Contents
- [Architecture](#️-architecture)
- [Quick Start](#-quick-start)
- [User Interface](#️-user-interface)
- [Model Settings](#️-model-settings)
- [File Structure](#-file-structure)

---

### 🏗️ Architecture

| Component | Default |
|---|---|
| LLM | `Qwen/Qwen3-0.6B` (HuggingFace) **or** `.gguf` via llama.cpp **or** remote via Inference API |
| Vision LLM | `HuggingFaceTB/SmolVLM-500M-Instruct` (HuggingFace) **or** GGUF via llama.cpp **or** remote via Inference API |
| Speech-to-Text | `openai/whisper-small` (HuggingFace) **or** whisper.cpp server **or** remote via Inference API |
| Embedding | `BAAI/bge-m3` (HuggingFace) **or** GGUF via llama.cpp server **or** remote via Inference API |
| Visual Retriever | `vidore/colsmolvlm-v0.1` |
| Vector store | ChromaDB (`./chroma_db/`) |
| Visual Index | `vidore/colsmolvlm-v0.1` (`./visual_index/`) |
| Supported document types | PDF, TXT, MD, DOCX |
| Agent type | `CodeAgent` (General/RAG/Data Analysis); `ToolCallingAgent` (Deep Research search sub-agent) |
| UI | Gradio |

> **Note**: `HardwareManager` automatically detects your hardware (NVIDIA or AMD) and can help fix your environment via the "Fix Environment" button in the UI. The code contains logic that can detect Apple Silicon (MPS) as well, but this is a **Windows tool** that is not tested or officially supported on macOS (see the "🍎 macOS" section below).

---

### 🚀 Quick Start

#### 1. Install dependencies

```bash
# Create a venv (optional but recommended)
python -m venv .venv && source .venv/bin/activate

# Install core dependencies (vision, audio, and text extraction, incl. python-docx)
pip install -r requirements.txt

# Install PyTorch (auto-detects CUDA/MPS/AMD if available)
pip install torch torchvision
```

#### 📦 Option 1 — Windows GUI Setup Wizard (Recommended for End Users)

Download and run **`Output\LocalAiLab_Setup_v0.0.3.exe`**:
- Lets you choose your preferred destination directory (e.g. `E:\LocalAiLab`).
- Automatically creates `.venv` and installs PyTorch + AI dependencies with a live progress bar (0%–100%).
- Provides a clickable and enforceable Cancel button.
- Automatically creates Desktop and Start Menu shortcuts.

#### 💻 Option 2 — One-liner Windows command (fresh machine)

```powershell
iwr -useb https://raw.githubusercontent.com/aidgcreator-prog/LocalAILab/smolagent_modular/install.ps1 | iex
```

This single command installs Python + Git (if missing), clones the repo, sets up the Python environment, detects your GPU, installs PyTorch + all dependencies, and creates a desktop shortcut — zero clicks required after the prompt.

On a machine that already has Python, just double-click **SETUP.bat** to do the GPU detection + dependency install automatically.

<details>
<summary><strong>Optional — llama.cpp (GGUF) model support</strong></summary>

`llama-cpp-python` is **not** installed by default. To use GGUF models (.gguf), you have two options:

**Option A — External backend (easiest):** Download `llama-server.exe` from [llama.cpp releases](https://github.com/ggerganov/llama.cpp/releases) and set its path under the "⚙️ Model Settings" accordion (Provider/Backend section) → "🖥️ llama-server.exe Path" near the top of the app. Then on whichever tab you want to use it (💬/📚/📊/🔬), pick "🖥️ llama.cpp server" from that tab's own Provider dropdown. No Python package install needed.

**Option B — In-process (llama-cpp-python):** Install it manually:

```powershell
pip install llama-cpp-python
```

For GPU acceleration (CUDA):

```powershell
pip uninstall llama-cpp-python -y
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124 --force-reinstall --no-cache-dir
```

Swap `cu124` for whatever CUDA tier matches your driver (`nvidia-smi` shows it top-right). If that wheel crashes with "Illegal Instruction", build from source instead:

```powershell
$env:CMAKE_ARGS = "-DGGML_CUDA=on"
$env:FORCE_CMAKE = "1"
pip install llama-cpp-python --no-cache-dir --force-reinstall
```

**GGUF model folder**: drop your `.gguf` files into any folder. Point the app at it by setting the `LLAMA_CPP_MODEL_DIR` environment variable before launching, or typing the folder path into the "📁 GGUF Model Folder" box in the UI and clicking "🔍 Scan".

</details>

<details>
<summary><strong>🍎 macOS (Mac) — Not Supported</strong></summary>

This app **does not run on macOS** in its current state:

- `SETUP.bat`/`SETUP.ps1`, `RUN.bat`/`RUN.ps1`, and `install.bat`/`install.ps1` are all PowerShell/Batch scripts that simply don't run on Mac — there's no normal way to launch the app.
- `requirements.txt` includes `bitsandbytes>=0.43.0`, which typically has no working wheel for Apple Silicon or Intel Mac — `pip install -r requirements.txt` can fail right away.
- The GPU build instructions for `llama-cpp-python` above only cover `-DGGML_CUDA=on` (NVIDIA) — there's no documented/tested Metal build (`-DGGML_METAL=on`) for Mac.
- Visual PDF indexing needs Poppler, and this README's install instructions for it are Windows-only.

`hardware.py` does contain logic that detects `torch.backends.mps` (Apple Silicon GPU), but that doesn't mean the app as a whole is tested or supported on macOS — there's no official install path, no guarantees, and no current plan for official Mac support.

</details>

#### 2. Index your documents

**Via CLI:**

```bash
python index_docs.py --pdf ./docs/my_paper.pdf        # Index a PDF
python index_docs.py --txt ./docs/notes.md            # Index a text/markdown file
python index_docs.py --docx ./docs/report.docx        # Index a Word document
python index_docs.py --dir ./docs                     # Index a folder (auto-detects types)
python index_docs.py --hf-dataset m-ric/huggingface_doc --text-col text --source-col source
python index_docs.py --stats                          # Show index statistics
python index_docs.py --clear                          # Clear the entire index
```

**Via UI:** Launch the app and use the **📂 Knowledge Base** tab. PDF, TXT, MD, and DOCX uploads are all supported.

#### 3. Launch the app

```bash
python app.py
```

Or on Windows, double-click **RUN.bat**. Open [http://localhost:7861](http://localhost:7861) in your browser (default port **7861**, to avoid conflicting with Gradio's usual 7860 — change via `server_port` in `app.py`).

---

### 🖥️ User Interface

The app is organized into eight main tabs, in this order:

| # | Tab | Description |
|---|---|---|
| 1 | 💬 **General Chat** | Direct LLM conversation — no retrieval. Optional Agentic Mode adds live web search |
| 2 | 🖼️ **Vision Chat** | Upload an image and ask questions — supports hybrid text context and Visual RAG |
| 3 | 🎙️ **Speech to Text** | Record or upload audio, transcribed via Whisper (auto-detect or forced language) |
| 4 | 📊 **Data Analysis** | Upload CSV/Excel; the AI agent explores it, builds charts, and writes a report. Pick a guided workflow (Sales, Customer, Financial, Payroll) or use the default EDA |
| 5 | 📂 **Knowledge Base** | Manage indexed documents (PDF/TXT/MD/DOCX), view the table, clear the index |
| 6 | 📚 **RAG Chat** | Retrieves from the knowledge base first (directly or agentically), then answers |
| 7 | 🔬 **Deep Research** | A manager agent + web-search sub-agent break the question into sub-questions, re-plan as they go, and write a structured Markdown report with sources (needs a capable model) |
| 8 | ℹ️ **About** | System status, architecture, and performance expectations — always bilingual |

#### Key Features
- **Bilingual UI**: full Khmer/English interface — switch instantly with the language dropdown
- **Multiple model backends**: HuggingFace/transformers (in-process), local server (llama.cpp / whisper.cpp), remote via Hugging Face Inference API (DeepInfra, Together, Replicate, etc.), or (LLM only) LiteLLM (OpenAI/Anthropic/Groq/…) — chosen independently per tab
- **Model settings**: shared provider/backend config (HF API, LiteLLM, llama-server.exe/whisper-server.exe paths, GGUF folder) lives in one global accordion; each tab's own provider + model dropdown (7 tabs) stays in that tab's sidebar; generation settings (context window, max tokens, reasoning) live in the 💬 General Chat tab but apply app-wide
- **Conversation Memory (Experimental)**: a "🧠 Conversation Memory" toggle on every agentic tab lets follow-up questions refer back to earlier turns. Memory only lives for the current running session (not saved to disk), and resets on a model switch, "Clear", or an app restart
- **DOCX support**: document indexing supports Word (.docx) files, including text inside tables
- **Environment Self-Fixing**: the "Fix Environment" button installs the correct PyTorch build for your GPU automatically
- **Reasoning Visibility**: model `<think>` tags render as a clean, collapsible UI element
- **Visual Retriever Selection**: choose between `colsmolvlm` or `colqwen2` directly in the UI

---

### ⚙️ Model Settings

You can change models at runtime via the UI's model selection dropdowns.

<details open>
<summary><strong>Text LLMs</strong></summary>

| VRAM/RAM | Recommended model |
|---|---|
| ~1.2 GB | `Qwen/Qwen3-0.6B` (fastest — default) |
| ~3 GB | `Qwen/Qwen3-1.7B` |
| ~6 GB | `Qwen/Qwen2.5-Coder-3B-Instruct` (small coding/agent model) |
| ~7 GB | `Qwen/Qwen3-4B` |
| ~4 GB | `google/gemma-4-E2B-it` |
| varies | Any `.gguf` model in your configured folder (via llama.cpp) |

</details>

<details open>
<summary><strong>Vision LLMs (VLM)</strong></summary>

| RAM | Recommended model |
|---|---|
| ~0.5 GB | `HuggingFaceTB/SmolVLM-256M-Instruct` |
| ~1 GB | `HuggingFaceTB/SmolVLM-500M-Instruct` (recommended — default) |
| ~6 GB | `Qwen/Qwen2.5-VL-3B-Instruct` |
| varies | GGUF vision-model pairs (main + mmproj) in your llama.cpp folder |

</details>

<details open>
<summary><strong>Speech-to-Text (Whisper)</strong></summary>

| RAM | Recommended model |
|---|---|
| ~1 GB | `openai/whisper-tiny` (fastest) |
| ~1 GB | `openai/whisper-base` |
| ~2 GB | `openai/whisper-small` (recommended — default) |
| ~10 GB | `openai/whisper-large-v3` (best accuracy, multilingual incl. Khmer) |
| ~1 GB | `seanghay/whisper-small-khmer-v2` 🇰🇭 (Khmer-tuned) |
| ~6 GB | `metythorn/whisper-large-v3-turbo-mixed-20eps-clean-text-197k` 🇰🇭 (best for Khmer) |

</details>

<details open>
<summary><strong>Model combos by hardware tier (higher-end options)</strong></summary>

For people with beefier hardware who want noticeably stronger local models than the defaults above, here's a tiered combo — all still `.gguf` files you drop into your configured GGUF folder like any other model.

| Hardware | Agent Model (Chat/Data Analysis) | RAG Model | Vision Model (HF/transformers) | Embedding Model |
|---|---|---|---|---|
| **CPU Only (64–128 GB RAM)** | **Qwen3.6-35B-A3B (GGUF, MoE — only ~3B active params/token, so it stays fast on CPU)**<br>https://huggingface.co/ggml-org/Qwen3.6-35B-A3B-GGUF | **Gemma-4-12B-it (GGUF)**<br>https://huggingface.co/ggml-org/gemma-4-12B-it-GGUF | **Qwen2.5-VL-7B-Instruct (GGUF)**<br>https://huggingface.co/unsloth/Qwen2.5-VL-7B-Instruct-GGUF | **BGE-M3**<br>https://huggingface.co/BAAI/bge-m3 |
| **8 GB VRAM** | **Qwen3-8B (GGUF)**<br>https://huggingface.co/Qwen/Qwen3-8B-GGUF | **Gemma-4-12B-it (GGUF) — ⚠️ tight fit, see note below** (same as above) | **Qwen2.5-VL-7B-Instruct (GGUF)** (same as above) | **BGE-M3** (same as above) |
| **16 GB VRAM** | **Qwen3-14B (GGUF)**<br>https://huggingface.co/MaziyarPanahi/Qwen3-14B-GGUF | **Gemma-4-12B-it (GGUF)** (same as above) | **Qwen2.5-VL-7B-Instruct (GGUF)** (same as above) | **BGE-M3** (same as above) |
| **24 GB VRAM** | **Qwen3-32B (GGUF)**<br>https://huggingface.co/MaziyarPanahi/Qwen3-32B-GGUF | **Gemma-4-26B-A4B-it (GGUF)**<br>https://huggingface.co/unsloth/gemma-4-26B-A4B-it-GGUF | **Gemma-4-12B-it (GGUF)**<br>https://huggingface.co/ggml-org/gemma-4-12B-it-GGUF | **Qwen3-Embedding-4B**<br>https://huggingface.co/Qwen/Qwen3-Embedding-4B |
| **48 GB+ VRAM** | **Qwen3-32B (GGUF)** (same as above) | **Gemma-4-31B-it (GGUF)**<br>https://huggingface.co/ggml-org/gemma-4-31B-it-GGUF | **Gemma-4-31B-it (GGUF)** (same as above) | **Jina Embeddings v4**<br>https://huggingface.co/jinaai/jina-embeddings-v4 |

> ⚠️ **8 GB VRAM note**: `Gemma-4-12B-it` at Q4_K_M is already ~7.4 GB of weights alone — that leaves very little headroom for KV cache on an 8 GB card, especially if the "🧠 Context Window" dropdown in the UI is set above 8K. If you hit an out-of-memory error at this tier, lower the context window first, or switch to the lighter `Gemma-4-E4B-it` instead.
>
> **CPU Only**: Qwen3.6-35B-A3B is a MoE model — only ~3B of its 35B total parameters are active per token — so it stays reasonably fast on a 64–128 GB RAM CPU-only rig, unlike a dense model like Qwen3-8B, which always computes every parameter.

> ⚠️ **Compatibility note**: `Gemma-4-12B-it` / `Gemma-4-31B-it` are themselves natively multimodal (encoder-free, take image input directly) — but this app's GGUF vision loader (`llama_backend.py`) only recognizes the LLaVA/MiniCPM-V/Moondream/nanoLLaVA chat-handler families right now, not Gemma 4's format. So using them as this app's "🎨 Vision LLM" (GGUF path) needs a small code update first — until then, `Qwen2.5-VL-7B-Instruct` via the HuggingFace/transformers backend is the option that works out of the box. Similarly, `Qwen3-VL` (a newer, likely stronger vision-language family than Qwen2.5-VL) gained llama.cpp support in late October 2025 via the newer `llama-mtmd-cli`/`llama-server` multimodal path, but also isn't wired up in this app's handler-detection list yet.

</details>

---

### 📂 File Structure

```
.
├── app.py             # Entry point (launch) — actual logic lives in the modules below
├── i18n.py            # Khmer/English UI strings
├── hardware.py        # GPU/device detection, environment self-fix
├── user_config.py     # Persisted settings (e.g. GGUF model folder, context window)
├── llama_backend.py      # Optional llama.cpp (GGUF) model backend (text + vision)
├── whisper_cpp_backend.py # Optional whisper.cpp server backend (STT via subprocess)
├── branding.py           # Logo, app name/version, ℹ️ About tab content
├── model_registry.py  # Model dropdown options (LLM/VLM/STT) + GGUF rescan
├── models.py          # LLM/VLM/STT loading, caching, unloading, inference
├── knowledge_base.py  # Document indexing (PDF/TXT/MD/DOCX), ChromaDB, visual index, retrieval
├── agent_memory.py    # Multi-turn memory helper for CodeAgents (in-RAM only — no disk persistence, see file docstring)
├── general_agent.py   # Agentic General Chat CodeAgent (web search tools)
├── rag_agent.py        # Agentic RAG CodeAgent (retriever tool)
├── deep_research_agent.py # Manager + ToolCallingAgent web-search sub-agent for Deep Research
├── data_analysis.py   # CodeAgent for CSV/Excel exploration
├── playwright_search_tool.py # Playwright + DuckDuckGo search tools (free SerpAPI replacement)
├── agent_streaming.py  # Live-streaming of every ActionStep/PlanningStep for all agentic tabs
├── chat.py            # Chat-turn handlers for General/RAG/Vision tabs
├── ui.py              # Gradio Blocks UI + all event wiring
├── index_docs.py      # CLI indexing script
├── requirements.txt   # Python dependencies (incl. python-docx)
├── SETUP.bat/.ps1     # Windows one-click installer (GPU detection, venv, deps)
├── RUN.bat/.ps1       # Windows one-click launcher
├── install.bat/.ps1   # Windows one-liner installer (Python+Git+clone+setup+shortcut)
├── installer.iss      # Inno Setup GUI Wizard script (LocalAiLab_Setup_v0.0.3.exe)
├── BUILD_INSTALLER.bat # Batch script to compile installer.iss into .exe
├── Output/            # Output folder for compiled setup wizard (LocalAiLab_Setup_v0.0.3.exe)
├── README.md          # This file
├── chroma_db/         # Auto-created; ChromaDB persistent storage
└── visual_index/      # Auto-created; visual index storage
```
