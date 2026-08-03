"""
branding.py — LocalAiLab branding (logo, app name/version) and the
bilingual ℹ️ About tab content.
"""

import base64
from pathlib import Path

_LOGO_PATH = Path(__file__).parent / "image" / "logo.jpg"


def _load_logo_b64() -> str:
    try:
        data = _LOGO_PATH.read_bytes()
        return base64.b64encode(data).decode("utf-8")
    except Exception:
        return ""


DEVELOPER_LOGO_B64 = _load_logo_b64()
DEVELOPER_NAME = "LocalAiLab"
APP_NAME_EN = "Multipurpose AI Assistant"
APP_NAME_KH = "ជំនួយការ AI ពហុមុខងារ"
APP_VERSION = "0.0.3-beta"


# ──────────────────────────────────────────────────────────────────
# About tab — always shown bilingually (Khmer first, English below),
# independent of the language dropdown. Kept as static strings so it
# stays accurate to the current tab order / feature set at a glance.
# ──────────────────────────────────────────────────────────────────
def about_content_kh(device: str, version: str) -> str:
    return f"""
### 🔖 {APP_NAME_KH} — កំណែ {version}

ជំនួយការ AI ពហុមុខងារ ដែលដំណើរការនៅលើកុំព្យូទ័ររបស់អ្នកផ្ទាល់ ពហុភាសា (ខ្មែរ/អង់គ្លេស) និងពហុម៉ូដាល — សន្ទនាទូទៅ វិភាគឯកសារតាមរយៈ RAG យល់ដឹងរូបភាព
បំលែងសំឡេងទៅជាអក្សរ វិភាគទិន្នន័យ CSV/Excel ដោយ AI Agent និងគ្រប់គ្រងមូលដ្ឋានចំណេះដឹង — ដំណើរការទាំងស្រុងនៅលើកុំព្យូទ័ររបស់អ្នក
ដោយប្រើម៉ូដែល HuggingFace (transformers) ឬម៉ូដែលមូលដ្ឋាន GGUF តាមរយៈ llama.cpp។ បង្កើតដោយ LocalAiLab។

---

### 🆕 អ្វីដែលថ្មីក្នុងកំណែ {version}

- **📄 បញ្ជីម៉ូដែល `hf_models.csv` ខាងក្រៅ**៖ បញ្ជីម៉ូដែល HuggingFace ទាំងអស់ត្រូវបានរៀបចំក្នុងឯកសារ CSV ងាយស្រួលកែប្រែ (`hf_models.csv`) ដោយមិនបាច់កែប្រែកូដ Python។ រៀបចំជាពិសេសសម្រាប់ម៉ូដែល **Google**, **Unsloth**, និង **LMStudio** (ជាមួយនឹងម៉ូដែលតូចបំផុត `google/gemma-4-E2B-it-qat-mobile-transformers` ជាលំនាំដើម)។
- **⚡ ToolCallingAgent ជាលំនាំដើម**៖ ផ្ទាំងសន្ទនាទូទៅ (General Chat) ផ្ទាំង RAG Chat និងផ្ទាំងស្រាវជ្រាវស៊ីជម្រៅ (Deep Research) ប្រើ `ToolCallingAgent` ជាលំនាំដើម ដើមបីជៀសវាងកំហុស parsing កូដ Python លើ local models។ ផ្ទាំងវិភាគទិន្នន័យ (Data Analysis) នៅតែប្រើ `CodeAgent` សម្រាប់ប្រតិបត្តិការកូដ Python លើ pandas/matplotlib។
- **🧠 ឧបករណ៍វិភាគ Smart Parser ឆ្លាតវៃ**៖ បន្ថែម `_smart_parse_code_blobs` និង `_smart_parse_json_blob` សម្រាប់ចាប់យក និងបំលែងចម្លើយអត្ថបទធម្មតា ឬទម្រង់ tool call បែប `call:web_search{query:...}` របស់ Gemma-4 និង local LLM ផ្សេងទៀត ដោយគ្មានកំហុស retry loop ឡើយ។
- **🔑 ធ្វើសមកាលកម្ម HF Token & `.env`**៖ គាំទ្រការផ្ទុក `.env` ដោយស្វ័យប្រវត្តិ និងធ្វើសមកាលកម្មអថេរបរិស្ថាន `HF_TOKEN` ទៅកាន់ `os.environ` និង `.env` ដោយគ្មានសារព្រមានអត់ token ពី Hugging Face Hub ទៀតឡើយ។
- **🎨 សម្រួលទម្រង់ UI និងប្រព័ន្ធពណ៌**៖ បង្កើតទម្រង់ visually distinct សម្រាប់ **🧠 Reasoning (Amber Gold)**, **⚙️ 🛠️ Step Logs & Tool Calls (Tech Slate / Cyan)**, និង **✨ 💬 Final Answer (Emerald Green)** ព្រមទាំងបន្ថែម font fallbacks សកល (`Segoe UI Emoji`, `Apple Color Emoji`, `Noto Color Emoji`)។

---

## ផ្ទាំង

| ផ្ទាំង | ការពិពណ៌នា |
|---|---|
| 💬 ការសន្ទនាទូទៅ | ការសន្ទនាផ្ទាល់ជាមួយ LLM / ToolCallingAgent |
| 📚 ការសន្ទនា RAG | ទាញយកពីមូលដ្ឋានចំណេះដឹងជាមុន រួចឆ្លើយ |
| 🔬 ស្រាវជ្រាវស៊ីជម្រៅ | Agent គ្រប់គ្រង + agent ស្វែងរកតាមអ៊ីនធឺណិត — បំបែកសំណួរ រៀបចំផែនការឡើងវិញ ស្វែងរកជាបន្តបន្ទាប់ រួចសរសេររបាយការណ៍ Markdown ដែលមានប្រភពយោង |
| 🖼️ ការសន្ទនាចក្ខុវិស័យ | យល់ដឹងរូបភាព ជាមួយបរិបទអត្ថបទ |
| 🎙️ និយាយទៅជាអក្សរ | បំលែងសំឡេងជាអក្សរ ដោយប្រើ Whisper (រួមទាំងភាសាខ្មែរ) |
| 📊 វិភាគទិន្នន័យ | CodeAgent វិភាគ CSV/Excel បង្កើតក្រាហ្វិក និងរបាយការណ៍ |
| 📂 មូលដ្ឋានចំណេះដឹង | បង្ហោះ (PDF / TXT / MD / DOCX) និងគ្រប់គ្រងឯកសារ |

## ស្ថាបត្យកម្ម

| សមាសធាតុ | លម្អិត |
|---|---|
| LLM | ម៉ូដែល HuggingFace (Gemma-4 / Unsloth / LMStudio) **ឬ** ម៉ូដែល GGUF មូលដ្ឋានតាមរយៈ llama.cpp |
| Vision LLM | SmolVLM / Qwen2.5-VL |
| Speech-to-Text | Whisper (រួមទាំងម៉ូដែលខ្មែរ Whisper-small ខ្មែរ) |
| Embedding | BAAI/bge-m3 |
| Vector store | ChromaDB (`./chroma_db/`) |
| Visual Index | ColSmolVLM / ColQwen2 (`./visual_index/`) |
| ប្រភេទឯកសារដែលបញ្ចូលបាន | PDF, TXT, MD, DOCX |
| ប្រភេទភ្នាក់ងារ | `ToolCallingAgent` (General/RAG/Deep Research); `CodeAgent` (Data Analysis CSV/Excel) |
| UI | Gradio |

## ល្បឿនរំពឹងទុក ({device})

| កិច្ចការ | ពេលវេលា |
|---|---|
| បញ្ចូលឯកសារ | ១០–៦០ វិ |
| ឆ្លើយបែប General / RAG | ១–៣០ វិ |
| ឆ្លើយបែប Vision | ៣០ វិ – ២ នាទី |

> 💡 ម៉ូដែល GGUF (llama.cpp) ត្រូវបានស្កេនដោយស្វ័យប្រវត្តិពីថតដែលអ្នកកំណត់ (ប្រអប់ "📁 ថតម៉ូដែល GGUF" ខាងលើ ឬអថេរបរិស្ថាន `LLAMA_CPP_MODEL_DIR`) ហើយបង្ហាញនៅក្នុងបញ្ជីទម្លាក់ម៉ូដែលដូចគ្នានឹងម៉ូដែល HuggingFace។
"""


def about_content_en(device: str, version: str) -> str:
    return f"""
### 🔖 {APP_NAME_EN} — Version {version}

A local, bilingual (Khmer/English), multi-modal AI assistant — general chat, document RAG, vision chat, speech-to-text,
AI-driven CSV/Excel data analysis, and knowledge base management — running entirely on your own machine, using either
HuggingFace (transformers) models or local GGUF models via llama.cpp. Built by LocalAiLab.

---

### 🆕 What's New in Version {version}

- **📄 External `hf_models.csv` Registry**: HuggingFace model options are now stored in an external CSV file (`hf_models.csv`) for easy user editing without modifying Python source code. Tailored to **Google**, **Unsloth**, and **LMStudio** models (with `google/gemma-4-E2B-it-qat-mobile-transformers` as default).
- **⚡ Default `ToolCallingAgent` Architecture**: General Chat, RAG Chat, and Deep Research now default to `ToolCallingAgent` for structured tool calling without code execution errors. `CodeAgent` remains dedicated to Data Analysis (Python pandas & matplotlib data science).
- **🧠 Smart Parser Fallbacks**: Introduced `_smart_parse_code_blobs` and `_smart_parse_json_blob` to automatically handle plain text final answers and parse Gemma-4 `call:web_search{query:...}` tool calls with 0 error retries.
- **🔑 Automatic HF Token & `.env` Syncing**: Full `.env` file loading (`load_dotenv()`) and environment variable synchronization for `HF_TOKEN` across `os.environ` and `.env` for warning-free Hugging Face Hub downloads.
- **🎨 Enhanced Chat & Response UI Aesthetics**: High-contrast UI theme distinguishing **🧠 Reasoning Process (Amber Gold)**, **⚙️ 🛠️ Step Logs & Tool Calls (Tech Slate / Cyan)**, and **✨ 💬 Final Answers (Emerald Green)** with global cross-platform emoji font fallbacks (`Segoe UI Emoji`, `Apple Color Emoji`, `Noto Color Emoji`).

---

## Tabs

| Tab | Description |
|---|---|
| 💬 General Chat | Direct LLM conversation & web tools — ToolCallingAgent |
| 📚 RAG Chat | Retrieves from knowledge base first, then answers |
| 🔬 Deep Research | Manager agent + web-search sub-agent — breaks the question down, re-plans as it goes, and writes a structured Markdown report with sources |
| 🖼️ Vision Chat | Image understanding with optional text context |
| 🎙️ Speech to Text | Transcribe audio into text using Whisper (including Khmer tuning) |
| 📊 Data Analysis | CodeAgent analyzes CSV/Excel, builds charts and a report |
| 📂 Knowledge Base | Upload (PDF / TXT / MD / DOCX) & manage indexed documents |

## Architecture

| Component | Detail |
|---|---|
| LLM | HuggingFace models (Gemma-4 / Unsloth / LMStudio) **or** local GGUF models via llama.cpp |
| Vision LLM | SmolVLM / Qwen2.5-VL |
| Speech-to-Text | Whisper (including Khmer-tuned Whisper-small Khmer) |
| Embedding | BAAI/bge-m3 |
| Vector store | ChromaDB (`./chroma_db/`) |
| Visual Index | ColSmolVLM / ColQwen2 (`./visual_index/`) |
| Supported document types | PDF, TXT, MD, DOCX |
| Agent type | `ToolCallingAgent` (General/RAG/Deep Research); `CodeAgent` (Data Analysis CSV/Excel) |
| UI | Gradio |

## Expected speed ({device})

| Task | Time |
|---|---|
| Index a document | 10–60 s |
| General / RAG answer | 1–30 s |
| Vision answer | 30 s – 2 min |

> 💡 GGUF (llama.cpp) models are auto-discovered from whatever folder you configure (the "📁 GGUF Model Folder" box above, or the `LLAMA_CPP_MODEL_DIR` environment variable) and appear in the same model dropdown as the HuggingFace models.
"""
