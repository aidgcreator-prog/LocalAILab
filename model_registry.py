"""
model_registry.py — Central registry of model choices (LLM / VLM / STT /
visual retriever) shown in the UI dropdowns, plus shared path/size
constants, and the "rescan GGUF folder" action that rebuilds MODEL_OPTIONS
at runtime.
"""

import os
import re
from typing import Optional

import gradio as gr

import llama_backend
import user_config
import whisper_cpp_backend
from hardware import HardwareManager
from i18n import LANGUAGES

# ──────────────────────────────────────────────────────────────────
# Provider sentinels — each model type can run via one of three
# backends.  Persisted per‑tab so every chat tab can pick its own.
# ──────────────────────────────────────────────────────────────────
PROVIDER_LOCAL_HF = "__provider_local_hf__"
PROVIDER_SERVER    = "__provider_server__"
PROVIDER_HF_API    = "__provider_hf_api__"
PROVIDER_LITELLM   = "__provider_litellm__"

# Label -> sentinel — shared UI labels that use the sentinel when
# the model is configured through the shared HF fields below.
HF_API_ENTRY_LABEL = "🌐 Hugging Face Inference API (remote)"
HF_INFERENCE_API_SENTINEL = "__hf_inference_api__"

LITELLM_ENTRY_LABEL = "🔗 LiteLLM (OpenAI/Anthropic/Groq/…)"
LITELLM_SENTINEL = "__litellm__"

LLM_PROVIDER_OPTIONS = {
    "🧩 Local HuggingFace":         PROVIDER_LOCAL_HF,
    "🖥️ llama.cpp server":          PROVIDER_SERVER,
    "🌐 HF Inference API":          PROVIDER_HF_API,
    "🔗 LiteLLM (OpenAI/Anthropic/…)": PROVIDER_LITELLM,
}
VLM_PROVIDER_OPTIONS = {
    "🧩 Local HuggingFace":         PROVIDER_LOCAL_HF,
    "🖥️ llama.cpp server":          PROVIDER_SERVER,
    "🌐 HF Inference API":          PROVIDER_HF_API,
}
STT_PROVIDER_OPTIONS = {
    "🧩 Local HuggingFace":         PROVIDER_LOCAL_HF,
    "🖥️ whisper.cpp server":        PROVIDER_SERVER,
    "🌐 HF Inference API":          PROVIDER_HF_API,
}
EMBED_PROVIDER_OPTIONS = {
    "🧩 Local HuggingFace":         PROVIDER_LOCAL_HF,
    "🖥️ llama.cpp server":          PROVIDER_SERVER,
    "🌐 HF Inference API":          PROVIDER_HF_API,
}

# Per-tab provider persistence keys.
_PROVIDER_KEYS = {
    "gen":   "provider_gen",
    "rag":   "provider_rag",
    "data":  "provider_data",
    "dr":    "provider_dr",
    "vlm":   "provider_vlm",
    "stt":   "provider_stt",
    "embed": "provider_embed",
}
_DEFAULT_PROVIDER = PROVIDER_LOCAL_HF


def get_saved_provider(tab_key: str) -> str:
    """Persisted provider sentinel for a tab, falling back to local HF."""
    config_key = _PROVIDER_KEYS.get(tab_key)
    if config_key is None:
        return _DEFAULT_PROVIDER
    return str(user_config.USER_CONFIG.get(config_key, _DEFAULT_PROVIDER))


def set_saved_provider(tab_key: str, sentinel: str) -> None:
    config_key = _PROVIDER_KEYS.get(tab_key)
    if config_key:
        user_config.save_user_config({config_key: sentinel})


def get_provider_label(provider_map: dict, sentinel: str) -> str:
    """Reverse‑lookup the dropdown label for a provider sentinel."""
    for label, val in provider_map.items():
        if val == sentinel:
            return label
    return next(iter(provider_map))


# ──────────────────────────────────────────────────────────────────
# Model‑list filtering — each provider shows a different set of
# model choices in the dropdown.
# ──────────────────────────────────────────────────────────────────
def get_model_options_for_provider(provider: str, model_type: str) -> dict:
    """Return the label→model_id dict that should appear in the dropdown
    for *model_type* ('llm' / 'vlm' / 'stt' / 'embed') when the user has
    chosen *provider*."""
    if provider == PROVIDER_HF_API:
        return {HF_API_ENTRY_LABEL: HF_INFERENCE_API_SENTINEL}

    if provider == PROVIDER_LITELLM:
        return {LITELLM_ENTRY_LABEL: LITELLM_SENTINEL}

    if provider == PROVIDER_SERVER:
        if model_type == "llm":
            out = {}
            for k, v in llama_backend.discover_gguf_models().items():
                out[k] = v
            return out
        elif model_type == "vlm":
            out = {}
            for k, (mpath, _) in llama_backend.discover_gguf_vlm_models().items():
                out[k] = mpath
            return out
        elif model_type == "stt":
            return dict(whisper_cpp_backend.discover_whisper_models())
        elif model_type == "embed":
            out = {}
            for k, v in llama_backend.discover_gguf_models().items():
                out[k] = v
            return out
        return {}

    # PROVIDER_LOCAL_HF — only HF‑hub entries (no .gguf)
    if model_type == "llm":
        return dict(BASE_MODEL_OPTIONS)
    elif model_type == "vlm":
        return dict(BASE_VLM_OPTIONS)
    elif model_type == "stt":
        return dict(STT_OPTIONS)
    elif model_type == "embed":
        return dict(EMBED_OPTIONS)
    return {}


def get_model_label_for_id(options: dict, model_id: str, fallback: str) -> str:
    """Reverse‑lookup a model dropdown label from its value."""
    for label, val in options.items():
        if val == model_id:
            return label
    return fallback

# ──────────────────────────────────────────────────────────────────
# Shared constants
# ──────────────────────────────────────────────────────────────────
# Embedding model — dynamic default based on detected hardware tier,
# mirroring the "Embedding Model" column of README.md's "Model combos by
# hardware tier" table exactly:
#   CPU-only / 8GB / 16GB VRAM -> BGE-M3     (small, works everywhere)
#   24GB VRAM                  -> Qwen3-Embedding-4B
#   48GB+ VRAM                 -> Jina Embeddings v4
# Unknown hardware (detection failed) falls back to BGE-M3 — the safest
# default, since guessing a larger embedding model on unknown hardware
# risks an OOM on the very first index/query call.
#
# This only changes the DEFAULT — like context_window (see
# get_saved_context_window() below), a value the user explicitly saved
# to user_config.json always wins over the hardware-detected default, so
# switching hardware tiers never silently overrides a deliberate choice.
# ──────────────────────────────────────────────────────────────────
EMBED_OPTIONS = {
    "BGE-M3 (~2 GB RAM | multilingual, recommended default)": "BAAI/bge-m3",
    "Qwen3-Embedding-4B (~8 GB RAM | 24GB+ VRAM tier)":        "Qwen/Qwen3-Embedding-4B",
    "Jina Embeddings v4 (~qwen3-based | 48GB+ VRAM tier)":     "jinaai/jina-embeddings-v4",
}

_EMBED_MODEL_BY_TIER = {
    HardwareManager.TIER_48GB_VRAM: "jinaai/jina-embeddings-v4",
    HardwareManager.TIER_24GB_VRAM: "Qwen/Qwen3-Embedding-4B",
    HardwareManager.TIER_16GB_VRAM: "BAAI/bge-m3",
    HardwareManager.TIER_8GB_VRAM:  "BAAI/bge-m3",
    HardwareManager.TIER_CPU_ONLY:  "BAAI/bge-m3",
    HardwareManager.TIER_UNKNOWN:   "BAAI/bge-m3",
}


def get_recommended_embed_model() -> str:
    """The embedding model README.md's hardware-tier table recommends for
    THIS machine, based on live-detected VRAM/RAM (see
    hardware.HardwareManager.detect_hardware_tier()). Falls back to
    BGE-M3 if the tier can't be determined."""
    tier = HardwareManager.detect_hardware_tier()
    return _EMBED_MODEL_BY_TIER.get(tier, "BAAI/bge-m3")


def get_default_embed_model() -> str:
    """The embedding model actually used unless the user has a saved
    override in user_config.json — a persisted choice always wins (same
    pattern as get_saved_context_window()), so re-detecting hardware on
    every restart never silently reverts an explicit user pick."""
    saved = user_config.USER_CONFIG.get("embed_model")
    if saved:
        return saved
    return get_recommended_embed_model()


def set_embed_model(model_id: str) -> None:
    """Persist an explicit embedding-model choice — mirrors
    llama_backend.set_model_dir() / set_context_window()'s persistence
    pattern. NOTE: changing this only takes effect on the next embedding
    model load (models.get_embed_model() caches the loaded model); if one
    is already loaded, the caller is responsible for resetting
    models._embed_model, since an embedding model can't be hot-swapped
    mid-session without also fully re-indexing every stored vector in
    ChromaDB (embeddings from different models aren't comparable)."""
    user_config.save_user_config({"embed_model": model_id})


def get_default_embed_label() -> str:
    """Reverse-lookup the dropdown label matching the currently active
    embedding model id (persisted override, or the hardware-tier
    recommendation if nothing was ever saved) — mirrors
    get_saved_context_window_label()'s pattern. Used to initialize the
    UI's "🧩 Embedding Model" dropdown to the right value on load."""
    current = get_default_embed_model()
    for label, model_id in EMBED_OPTIONS.items():
        if model_id == current:
            return label
    return next(iter(EMBED_OPTIONS.keys()))


# Best-effort vector dimensions for each EMBED_OPTIONS entry — used only
# to make the UI's switch-embedding-model warning more concrete (telling
# the user the actual before/after dimensions instead of just "they might
# differ"). NOT used to block or validate anything: if a future model's
# real dimension differs from what's listed here, knowledge_base.py's
# actual runtime check (peeking at a real stored vector, and catching
# ChromaDB's own dimension-mismatch error) is always the source of truth,
# not this table.
EMBED_MODEL_DIMENSIONS = {
    "BAAI/bge-m3": 1024,
    "Qwen/Qwen3-Embedding-4B": 2560,
    "jinaai/jina-embeddings-v4": 2048,  # verify against the model card if this ever looks off
}

DEFAULT_EMBED_MODEL = get_default_embed_model()
CHROMA_PERSIST_DIR  = "./chroma_db"
VISUAL_INDEX_DIR    = "./visual_index"
CHUNK_SIZE          = 1024
CHUNK_OVERLAP       = 128
TOP_K               = 4
# NOTE: this budget covers BOTH the model's internal <think>...</think>
# reasoning AND its actual answer — they share the same generation call
# (see models._call_llm() / llama_backend.LlamaServerModel.generate()).
# 512 was fine for small non-reasoning models, but "thinking"-tuned
# models (e.g. Qwen3.x, Qwen3.6-35B-A3B) can burn the entire budget just
# reasoning about a longer/multi-part prompt, leaving nothing left for
# the answer itself — format_llm_response() in chat.py then has an empty
# or unclosed <think> section and the chat bubble looks blank even
# though generation "succeeded".
#
# Raised again from 2048 -> 4096: 2048 was still getting cut off mid-
# generation on longer agentic outputs — observed concretely on Deep
# Research's report-writing step, where a CodeAgent step ran out of
# budget in the middle of writing a Python triple-quoted report string
# and got cut off before the closing `"""`, which then failed to parse
# with "SyntaxError: unterminated triple-quoted string literal" — a
# genuine truncation, not a real code mistake by the model. Data
# Analysis's EDA reports and Deep Research's multi-section Markdown
# reports are the longest single generations in this app and are the
# most likely to need this room. If responses still feel truncated on a
# heavy reasoning model or a long report, raise this further (it does
# cost more time/VRAM per turn — the GGUF KV-cache size is governed
# separately by CONTEXT_WINDOW_OPTIONS below, not by this value).
MAX_NEW_TOKENS      = 4096

# ──────────────────────────────────────────────────────────────────
# Max New Tokens — now user-configurable from the UI (⚙️ Model Settings),
# instead of only the hardcoded MAX_NEW_TOKENS constant above (kept as
# the fallback default). Persisted the same way as CONTEXT_WINDOW_OPTIONS
# below, so the choice survives an app restart. See models.get_llm() /
# models._call_llm() for where this is actually applied — every backend
# (in-process llama.cpp, llama-server, and HuggingFace/transformers) reads
# get_saved_max_new_tokens() rather than the bare constant now.
#
# Why this matters in practice: this budget is SHARED between a model's
# internal <think>...</think> reasoning and its actual answer/code (see
# MAX_NEW_TOKENS's own docstring above) — a heavy "thinking"-tuned model
# (e.g. Qwen3.6-35B-A3B) can burn the entire budget reasoning and never
# emit an actual answer or tool call, which shows up in agentic tabs as
# a step that parses to an EMPTY code block ("Executing parsed code:"
# with nothing between the separators, `Out: None`) — a wasted step, not
# a tool-access failure. Raising this (or turning reasoning off via
# REASONING_DISABLE_TAG below) is the direct fix.
# ──────────────────────────────────────────────────────────────────
MAX_NEW_TOKENS_OPTIONS = {
    "1024  (fast, short answers)":                             1024,
    "2048":                                                    2048,
    "4096  (default)":                                         4096,
    "8192  (long reasoning / reports)":                        8192,
    "16384 (very long reasoning models, e.g. Qwen3.6-35B-A3B)": 16384,
}
DEFAULT_MAX_NEW_TOKENS_LABEL = "4096  (default)"
DEFAULT_MAX_NEW_TOKENS = MAX_NEW_TOKENS_OPTIONS[DEFAULT_MAX_NEW_TOKENS_LABEL]


def get_saved_max_new_tokens() -> int:
    """Read the persisted max-new-tokens budget, falling back to the
    4096 default if nothing was ever saved or the saved value is corrupt
    — same "safe default wins" pattern as get_saved_context_window()."""
    try:
        n = int(user_config.USER_CONFIG.get("max_new_tokens", DEFAULT_MAX_NEW_TOKENS))
        return n if n > 0 else DEFAULT_MAX_NEW_TOKENS
    except (TypeError, ValueError):
        return DEFAULT_MAX_NEW_TOKENS


def get_saved_max_new_tokens_label() -> str:
    """Reverse-lookup the dropdown label matching the persisted budget,
    for initializing the UI dropdown's value to whatever was saved last
    time — mirrors get_saved_context_window_label()."""
    saved = get_saved_max_new_tokens()
    for label, value in MAX_NEW_TOKENS_OPTIONS.items():
        if value == saved:
            return label
    return DEFAULT_MAX_NEW_TOKENS_LABEL


def set_max_new_tokens(n: int) -> None:
    """Persist the chosen max-new-tokens budget so it survives an app
    restart — mirrors set_context_window()'s persistence pattern."""
    user_config.save_user_config({"max_new_tokens": int(n)})


# ──────────────────────────────────────────────────────────────────
# Quantization (bitsandbytes) — user-configurable from the UI (🗜️
# Quantization dropdown in General Chat's Generation Settings).
#
# Lets any HuggingFace model load in 4-bit/8-bit via bitsandbytes,
# trading a little quality for roughly a quarter (4-bit) or half
# (8-bit) of the full-precision memory footprint. This is how the
# Gemma 4 hardware-tier table in README.md fits models like
# Gemma-4-26B-A4B-it on a 24GB card, or Gemma-4-E2B-it on a modest
# CPU machine — see get_recommended_quantization() below for the
# per-tier default.
#
# NOTE: bitsandbytes 4-bit/8-bit works most reliably on CUDA GPUs.
# On CPU/MPS models.get_llm() attempts it but falls back to the
# unquantized load (with a warning) rather than crashing. Models
# whose id contains "qat" (e.g. the Mobile QAT checkpoint) ship
# pre-quantized and are never re-quantized by this control.
# ──────────────────────────────────────────────────────────────────
QUANTIZATION_OPTIONS = {
    "None (full precision — default)": "none",
    "8-bit (bitsandbytes — ~half the memory)": "8bit",
    "4-bit NF4 (bitsandbytes — ~quarter the memory)": "4bit",
}
DEFAULT_QUANTIZATION_LABEL = "None (full precision — default)"
DEFAULT_QUANTIZATION = QUANTIZATION_OPTIONS[DEFAULT_QUANTIZATION_LABEL]


def get_recommended_quantization() -> str:
    """The quantization mode README.md's hardware-tier table recommends
    for THIS machine, matching the "Recommended Model / Quantization"
    ladder:
       CPU only / <8GB   -> E2B 4-bit      1.5-3 GB
       8-12GB GPU        -> E4B 4-bit      3-5 GB
       16GB GPU          -> 26B-A4B 4-bit  8-14 GB
       24GB GPU          -> 26B-A4B 8-bit  14-28 GB  (the sweet spot)
       24GB+ (max qual)  -> 31B 4-bit      18-20 GB  (absolute best)
    The top (48GB+) tier is treated as the "24GB GPU (max quality)" pick —
    the max VRAM the recommendation ladder targets is 24GB, which is the
    realistic ceiling. A saved user override via set_quantization() always
    wins (see get_effective_quantization())."""
    tier = HardwareManager.detect_hardware_tier()
    return {
        HardwareManager.TIER_48GB_VRAM: "4bit",
        HardwareManager.TIER_24GB_VRAM: "8bit",
        HardwareManager.TIER_16GB_VRAM: "4bit",
        HardwareManager.TIER_8GB_VRAM:  "4bit",
        HardwareManager.TIER_CPU_ONLY:  "4bit",
        HardwareManager.TIER_UNKNOWN:   "4bit",
    }.get(tier, "none")


def get_saved_quantization() -> str:
    """The explicitly-persisted quantization mode, or 'none' if the user
    never touched the control (used by the UI to show the current state)."""
    saved = str(user_config.USER_CONFIG.get("quantization_mode", "none"))
    return saved if saved in QUANTIZATION_OPTIONS.values() else "none"


def get_effective_quantization() -> str:
    """The quantization mode actually used when loading models: a saved
    user override wins, otherwise the hardware-tier recommendation."""
    saved = get_saved_quantization()
    if saved != "none":
        return saved
    return get_recommended_quantization()


def get_effective_quantization_label() -> str:
    """Reverse-lookup the dropdown label matching the effective
    quantization mode, for initializing the UI dropdown's value."""
    effective = get_effective_quantization()
    for label, value in QUANTIZATION_OPTIONS.items():
        if value == effective:
            return label
    return DEFAULT_QUANTIZATION_LABEL


def set_quantization(mode: str) -> None:
    """Persist the chosen quantization mode so it survives an app
    restart — mirrors set_context_window()'s persistence pattern."""
    mode = mode if mode in QUANTIZATION_OPTIONS.values() else "none"
    user_config.save_user_config({"quantization_mode": mode})


# ──────────────────────────────────────────────────────────────────
# Reasoning ("thinking") on/off toggle — user-configurable from the UI.
#
# Qwen3/Qwen3.5/Qwen3.6's own chat template looks for the literal
# substring "/no_think" (or "/think") anywhere in the LAST user turn and
# toggles its <think>...</think> reasoning block accordingly — this is
# the model family's own documented mechanism, not something this app
# invents. Prepending it to every prompt when the user has reasoning
# turned off is a direct, low-risk way to stop a heavy thinking-tuned
# model from spending its entire MAX_NEW_TOKENS budget on internal
# reasoning and never reaching a real answer/tool call (see
# MAX_NEW_TOKENS_OPTIONS's docstring above for the failure mode this
# fixes). On non-Qwen3 models this is simply inert extra text most
# templates ignore — harmless either way.
# ──────────────────────────────────────────────────────────────────
REASONING_DISABLE_TAG = "/no_think"


def get_saved_reasoning_enabled() -> bool:
    """Whether model reasoning is currently enabled (default: True — no
    behaviour change unless the user explicitly turns it off)."""
    return bool(user_config.USER_CONFIG.get("reasoning_enabled", True))


def set_reasoning_enabled(enabled: bool) -> None:
    """Persist the reasoning on/off choice so it survives an app restart
    — mirrors set_context_window()'s persistence pattern."""
    user_config.save_user_config({"reasoning_enabled": bool(enabled)})


def apply_reasoning_toggle(text: str) -> str:
    """Prepend REASONING_DISABLE_TAG to `text` when the user has disabled
    reasoning via the UI checkbox; a no-op passthrough otherwise. Callers
    (chat.py / data_analysis.py) apply this to every prompt/task string
    right before it reaches the model, on every tab (direct and agentic).
    """
    if get_saved_reasoning_enabled():
        return text
    return f"{REASONING_DISABLE_TAG}\n{text}"


DATA_ANALYSIS_DIR   = "./data_analysis"
DATA_UPLOAD_DIR      = f"{DATA_ANALYSIS_DIR}/uploads"
DATA_OUTPUT_DIR      = f"{DATA_ANALYSIS_DIR}/outputs"
DATA_AGENT_MAX_STEPS = 20

# ──────────────────────────────────────────────────────────────────
# Context window (n_ctx) — how many tokens of prompt+history+generation
# the LLM can hold at once. Mainly meaningful for the GGUF/llama.cpp
# backend (llama_backend.LlamaCppModel), where it's a fixed size set at
# load time — HF/transformers models size their own context from the
# checkpoint's trained max_position_embeddings and aren't affected by
# this setting.
#
# Bumping this fixes errors like:
#   "Requested tokens (16461) exceed context window of 16384"
# which happens once an agentic conversation's accumulated prompt +
# memory + tool-call history grows past whatever n_ctx the model was
# loaded with (16384 tokens, previously hardcoded in models.py). A
# larger window uses more VRAM/RAM (roughly linearly with n_ctx), so
# this is exposed as a user choice rather than just maxed out by default.
#
# Persisted the same way as llama_backend's GGUF folder (see
# user_config.py) so the choice survives an app restart.
# ──────────────────────────────────────────────────────────────────
CONTEXT_WINDOW_OPTIONS = {
    "4K   (4,096 tokens — lowest memory)":            4096,
    "8K   (8,192 tokens)":                            8192,
    "16K  (16,384 tokens — default)":                 16384,
    "32K  (32,768 tokens)":                           32768,
    "64K  (65,536 tokens — needs more VRAM/RAM)":     65536,
    "128K (131,072 tokens — needs a lot of VRAM/RAM)": 131072,
}
DEFAULT_CONTEXT_WINDOW_LABEL = "16K  (16,384 tokens — default)"
DEFAULT_CONTEXT_WINDOW = CONTEXT_WINDOW_OPTIONS[DEFAULT_CONTEXT_WINDOW_LABEL]


def get_saved_context_window() -> int:
    """Read the persisted context window (n_ctx), falling back to the
    default if nothing was ever saved (fresh install) or the saved value
    is corrupt/not one of our known sizes anymore."""
    try:
        n = int(user_config.USER_CONFIG.get("context_window", DEFAULT_CONTEXT_WINDOW))
        return n if n > 0 else DEFAULT_CONTEXT_WINDOW
    except (TypeError, ValueError):
        return DEFAULT_CONTEXT_WINDOW


def get_saved_context_window_label() -> str:
    """Reverse-lookup the dropdown label matching the persisted n_ctx, for
    initializing the UI dropdown's value to whatever was saved last time."""
    saved = get_saved_context_window()
    for label, value in CONTEXT_WINDOW_OPTIONS.items():
        if value == saved:
            return label
    return DEFAULT_CONTEXT_WINDOW_LABEL


def set_context_window(n_ctx: int) -> None:
    """Persist the chosen context window so it survives an app restart —
    mirrors llama_backend.set_model_dir()'s persistence pattern."""
    user_config.save_user_config({"context_window": int(n_ctx)})


# ──────────────────────────────────────────────────────────────────
# LLM backend mode for GGUF models — how a selected .gguf file is
# actually RUN, independent of which .gguf file/folder it comes from:
#
#   "inprocess" — llama-cpp-python, loaded directly inside this Python
#                 process (llama_backend.LlamaCppModel). The original,
#                 default behaviour.
#   "server"    — spawns/reuses an external `llama-server` executable
#                 as a subprocess and talks to it over its OpenAI-
#                 compatible HTTP API instead
#                 (llama_backend.get_or_start_llama_server() /
#                 LlamaServerModel). Needs a llama-server(.exe) binary
#                 configured — see llama_backend.LLAMA_SERVER_EXE_PATH /
#                 set_llama_server_exe_path().
#
# Only meaningful for .gguf models — HuggingFace/transformers models
# always run in-process regardless of this setting. Persisted the same
# way as the context window above, so the choice survives an app
# restart; models.get_llm() reads this to decide which backend class to
# build for a given GGUF model_id.
# ──────────────────────────────────────────────────────────────────
LLM_BACKEND_MODE_OPTIONS = {
    "🧩 llama-cpp-python (in-process — default)": "inprocess",
    "🖥️ llama-server (external process, OpenAI-compatible API)": "server",
}
DEFAULT_LLM_BACKEND_LABEL = "🧩 llama-cpp-python (in-process — default)"


def get_saved_llm_backend_mode() -> str:
    """Read the persisted GGUF backend mode ('inprocess' or 'server'),
    falling back to 'inprocess' if nothing was ever saved or the saved
    value isn't recognized — same "safe default wins" pattern as
    get_saved_context_window()."""
    saved = str(user_config.USER_CONFIG.get("llm_backend_mode", "inprocess"))
    return saved if saved in LLM_BACKEND_MODE_OPTIONS.values() else "inprocess"


def get_saved_llm_backend_label() -> str:
    """Reverse-lookup the dropdown label matching the persisted backend
    mode, for initializing the UI dropdown's value to whatever was saved
    last time — mirrors get_saved_context_window_label()."""
    saved = get_saved_llm_backend_mode()
    for label, mode in LLM_BACKEND_MODE_OPTIONS.items():
        if mode == saved:
            return label
    return DEFAULT_LLM_BACKEND_LABEL


def set_llm_backend_mode(mode: str) -> None:
    """Persist the chosen GGUF backend mode so it survives an app restart
    — mirrors set_context_window()'s persistence pattern. Callers (see
    ui.py) are responsible for resetting any cached agents/LLM instance
    and stopping a running llama-server process afterward, since a
    backend switch can't be hot-applied to an already-loaded model the
    way most other settings can."""
    mode = mode if mode in LLM_BACKEND_MODE_OPTIONS.values() else "inprocess"
    user_config.save_user_config({"llm_backend_mode": mode})


# ──────────────────────────────────────────────────────────────────
# llama-server (external process) backend — PER-REQUEST HTTP timeout.
#
# LlamaServerModel.generate() (llama_backend.py) posts to llama-server's
# /v1/chat/completions endpoint with a fixed request timeout. Previously
# this was hardcoded at 300s in LlamaServerModel's own default and never
# overridden by models.get_llm() — which is fine for small/fast models,
# but a large local GGUF model (e.g. a 30B+ MoE checkpoint) combined with
# a long accumulated agentic prompt (Deep Research's manager+sub-agent
# history, MAX_NEW_TOKENS=4096) can easily need more than 300s for a
# single generation. When that happens, LlamaServerModel.generate()
# doesn't crash — it catches the timeout and returns a fake assistant
# ChatMessage containing a "⚠️ llama-server request failed... Read timed
# out" warning (see that method's docstring/comment) — which smolagents'
# CodeAgent then tries to regex-parse as a ```python code block, fails,
# and reports a confusing "Error in code parsing" instead of the real
# "this just needs more time" issue.
#
# Exposed as a persisted user setting (same pattern as
# get_saved_context_window() above) instead of just raising the
# hardcoded default, since the right value genuinely depends on the
# user's model size/hardware — a small model on a fast GPU doesn't need
# 20 minutes per request, but a large CPU-bound MoE model might.
# ──────────────────────────────────────────────────────────────────
LLAMA_SERVER_TIMEOUT_OPTIONS = {
    "60s   (fast small models)":                       60,
    "120s":                                             120,
    "300s  (default)":                                  300,
    "600s  (10 min — large/CPU-bound models)":          600,
    "1200s (20 min — very large MoE models on CPU)":    1200,
    "1800s (30 min — maximum patience)":                1800,
}
DEFAULT_LLAMA_SERVER_TIMEOUT_LABEL = "300s  (default)"
DEFAULT_LLAMA_SERVER_TIMEOUT = LLAMA_SERVER_TIMEOUT_OPTIONS[DEFAULT_LLAMA_SERVER_TIMEOUT_LABEL]


def get_saved_llm_server_timeout() -> int:
    """Read the persisted llama-server per-request HTTP timeout (seconds),
    falling back to the 300s default if nothing was ever saved or the
    saved value is corrupt — same "safe default wins" pattern as
    get_saved_context_window()."""
    try:
        n = int(user_config.USER_CONFIG.get("llama_server_timeout", DEFAULT_LLAMA_SERVER_TIMEOUT))
        return n if n > 0 else DEFAULT_LLAMA_SERVER_TIMEOUT
    except (TypeError, ValueError):
        return DEFAULT_LLAMA_SERVER_TIMEOUT


def get_saved_llm_server_timeout_label() -> str:
    """Reverse-lookup the dropdown label matching the persisted timeout,
    for initializing the UI dropdown's value to whatever was saved last
    time — mirrors get_saved_context_window_label()."""
    saved = get_saved_llm_server_timeout()
    for label, value in LLAMA_SERVER_TIMEOUT_OPTIONS.items():
        if value == saved:
            return label
    return DEFAULT_LLAMA_SERVER_TIMEOUT_LABEL


def set_llm_server_timeout(seconds: int) -> None:
    """Persist the chosen llama-server per-request timeout so it survives
    an app restart — mirrors set_context_window()'s persistence pattern.
    Takes effect the next time a request is made (LlamaServerModel is
    lightweight to reconstruct — no subprocess restart needed, unlike a
    context-window or backend-mode change, since this only affects the
    Python-side `requests.post(..., timeout=...)` call, not llama-server
    itself)."""
    user_config.save_user_config({"llama_server_timeout": int(seconds)})


# ──────────────────────────────────────────────────────────────────
# Agentic CodeAgent step budget — scaled down for larger/slower local
# models. A broken step-parsing loop (e.g. a model that writes plain
# prose instead of a ```python fenced block) costs roughly the same
# wall-clock time PER STEP regardless of model size, but a 14B+ GGUF
# model can take 30-250+ seconds per step where a small HF model takes
# a few seconds — so the same default max_steps that's a harmless safety
# net on a small model turns into a 4-20+ minute stall on a large one
# before the agent finally gives up. See general_agent.py / rag_agent.py
# for where this is applied.
# ──────────────────────────────────────────────────────────────────
_PARAM_SIZE_RE = re.compile(r'(\d+(?:\.\d+)?)\s*[bB](?![a-zA-Z])')


def estimate_model_param_billions(model_id: str) -> Optional[float]:
    """Best-effort parse of a model's parameter count (in billions) from
    its id/filename, e.g.:
      'Qwen3.6-14B-A3B-FableVibes-Q8_0.gguf'      -> 14.0
      'qwen3-coder-30b-a3b-compacted-19b-256k...' -> 30.0 (first match wins)
      'Qwen/Qwen3-0.6B'                           -> 0.6
    Returns None if no confident '<number>B' pattern is found (e.g. an
    unusually-named checkpoint) — callers should treat that as "unknown
    size", not "small", since guessing wrong in the small direction would
    silently remove the safety margin this exists to add.
    """
    if not model_id:
        return None
    m = _PARAM_SIZE_RE.search(str(model_id))
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def get_max_steps_for_model(model_id: str, default_max_steps: int) -> int:
    """Scale an agentic CodeAgent's max_steps down for models estimated to
    be 10B+ parameters, so a broken parsing/tool-calling loop on a large,
    slow local GGUF model fails fast instead of grinding through the full
    default step budget (each failed step can take a minute or more on
    these models — see the module docstring above). Leaves
    `default_max_steps` untouched if the model's size can't be confidently
    parsed from its id/filename, since an unrecognized name is more often
    a normal HuggingFace repo id (usually small/fast) than a huge unnamed
    checkpoint, and it's safer to keep the normal budget than cut off a
    model that turns out to be small.
    """
    size_b = estimate_model_param_billions(model_id)
    if size_b is None:
        return default_max_steps
    if size_b >= 20:
        return min(default_max_steps, 4)
    if size_b >= 10:
        return min(default_max_steps, 5)
    return default_max_steps

QWEN3_IDS    = {"Qwen/Qwen3-0.6B", "Qwen/Qwen3-1.7B", "Qwen/Qwen3-4B",
                "Qwen/Qwen3-8B", "Qwen/Qwen3-14B", "Qwen/Qwen3-32B"}
# Qwen3.6 (April 2026) — hybrid linear-/full-attention MoE ("qwen3_5_moe")
# and dense architectures, superseding Qwen3.5. Only ships in 27B (dense)
# and 35B-A3B (MoE, ~3B active params/token) sizes — there is no small
# (<20B) Qwen3.6 checkpoint, so BASE_MODEL_OPTIONS below still uses plain
# Qwen3 for the 0.6B/1.7B/4B/8B/14B tiers, and only swaps in Qwen3.6 at
# the top end (replacing the older Qwen3-32B).
QWEN36_IDS   = {"Qwen/Qwen3.6-27B", "Qwen/Qwen3.6-35B-A3B"}
ALL_QWEN_IDS = QWEN3_IDS | QWEN36_IDS
QWEN_VL_IDS  = {"Qwen/Qwen2.5-VL-3B-Instruct", "Qwen/Qwen2.5-VL-7B-Instruct"}
SMOL_VLM_IDS = {"HuggingFaceTB/SmolVLM-256M-Instruct", "HuggingFaceTB/SmolVLM-500M-Instruct",
                "HuggingFaceTB/SmolVLM2-2.2B-Instruct"}
ORNITH_IDS = {
    "deepreinforce-ai/Ornith-1.0-9B",
}
# Gemma 4 (all sizes) needs transformers >= 5.10.1 — see
# models._MIN_TRANSFORMERS_VERSION["gemma4"] for the guard that checks
# this before load. Every entry in BASE_MODEL_OPTIONS is a Gemma 4 model
# (the app's base LLM family), so this guard applies to the whole default
# lineup — google/gemma-4-E2B-it (the app's default LLM), E4B, the Mobile
# QAT edge checkpoint, and the 12B/26B-A4B/31B ladder.
GEMMA4_IDS = {
    "google/gemma-4-E2B-it",
    "google/gemma-4-E4B-it",
    "google/gemma-4-e4b-it-qat-mobile-transformers",
    "google/gemma-4-12B-it",
    "google/gemma-4-26B-A4B-it",
    "google/gemma-4-31B-it",
    # QAT safetensors variants — same architecture, QAT-optimized weights
    "google/gemma-4-12B-it-qat-q4_0-unquantized",
    "google/gemma-4-26B-A4B-it-qat-q4_0-unquantized",
    "google/gemma-4-31B-it-qat-q4_0-unquantized",
    # Pre-quantized GPTQ/AWQ variants — same base architecture, different weight format
    "Vishva007/gemma-4-12B-it-W4A16-AutoRound-GPTQ",
    "Vishva007/gemma-4-12B-it-W4A16-AutoRound-AWQ",
    "mattbucci/gemma-4-26B-AWQ",
}

# Pre-quantized model IDs — these ship in GPTQ/AWQ format and must NOT be
# re-quantized by bitsandbytes. Detected by checking if the model id contains
# 'gptq' or 'awq' (case-insensitive).
GPTQ_AWQ_IDS = {
    "Vishva007/gemma-4-12B-it-W4A16-AutoRound-GPTQ",
    "Vishva007/gemma-4-12B-it-W4A16-AutoRound-AWQ",
    "mattbucci/gemma-4-26B-AWQ",
}

# ──────────────────────────────────────────────────────────────────
# Hugging Face Inference API — persisted settings.  The sentinel
# constant HF_INFERENCE_API_SENTINEL is defined near the top of this
# file alongside the other provider constants.
# ──────────────────────────────────────────────────────────────────
def get_saved_hf_token() -> str:
    val = str(user_config.USER_CONFIG.get("hf_token", "")).strip()
    if val and val != "hf_abc123":
        return val
    return os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACEHUB_API_TOKEN", "")


def set_hf_token(token: str) -> None:
    user_config.save_user_config({"hf_token": token})


def get_saved_hf_model_id() -> str:
    saved = str(user_config.USER_CONFIG.get("hf_model_id", "")).strip()
    return saved if saved else "google/gemma-4-26B-A4B-it"


def set_hf_model_id(model_id: str) -> None:
    user_config.save_user_config({"hf_model_id": model_id})


def get_saved_hf_provider() -> str:
    return str(user_config.USER_CONFIG.get("hf_provider", ""))


def set_hf_provider(provider: str) -> None:
    user_config.save_user_config({"hf_provider": provider})


# ──────────────────────────────────────────────────────────────────
# LiteLLM — persisted settings (model id, API key, API base).
# ──────────────────────────────────────────────────────────────────
def get_saved_litellm_model_id() -> str:
    return str(user_config.USER_CONFIG.get("litellm_model_id", ""))


def set_litellm_model_id(model_id: str) -> None:
    user_config.save_user_config({"litellm_model_id": model_id})


def get_saved_litellm_api_key() -> str:
    return str(user_config.USER_CONFIG.get("litellm_api_key", ""))


def set_litellm_api_key(key: str) -> None:
    user_config.save_user_config({"litellm_api_key": key})


def get_saved_litellm_api_base() -> str:
    return str(user_config.USER_CONFIG.get("litellm_api_base", ""))


def set_litellm_api_base(base: str) -> None:
    user_config.save_user_config({"litellm_api_base": base})


# ──────────────────────────────────────────────────────────────────
# LLM (HuggingFace + GGUF) options
# ──────────────────────────────────────────────────────────────────
BASE_MODEL_OPTIONS = {
    # Gemma 4 — the app's base LLM family. Needs transformers>=5.10.1 (see
    # models._MIN_TRANSFORMERS_VERSION["gemma4"] and GEMMA4_IDS above);
    # loading with an older transformers raises a clear upgrade error
    # instead of a cryptic AutoModel crash. Natively multimodal/encoder-
    # free — loads here via the plain text-LLM path (smolagents'
    # TransformersModel, which resolves Gemma 4 through
    # AutoModelForImageTextToText), which works for inference/generation,
    # though the vision/audio towers ride along unused; use the 🎨 Vision
    # LLM dropdown instead if you specifically want Gemma 4's image
    # understanding.
    # Sizes below show: download size (BF16) → VRAM at recommended quantization.
    "🔵 Gemma-4-E2B    (11 GB download → 3 GB VRAM @4-bit | CPU/<8GB tier)": "google/gemma-4-E2B-it",
    "🟢 Gemma-4-E4B    (18 GB download → 5 GB VRAM @4-bit | 8-12GB tier)": "google/gemma-4-E4B-it",
    "🧠 Gemma-4-E4B Mobile QAT (4 GB download | CPU/edge tier)": "google/gemma-4-e4b-it-qat-mobile-transformers",
    "🟠 Gemma-4-12B    (27 GB download | manual pick)": "google/gemma-4-12B-it",
    "🟠 Gemma-4-12B QAT (24 GB download | QAT-optimized, 11% smaller)": "google/gemma-4-12B-it-qat-q4_0-unquantized",
    "🔴 Gemma-4-26B-A4B (58 GB download → 14 GB VRAM @4-bit | 16-24GB tier)": "google/gemma-4-26B-A4B-it",
    "🔴 Gemma-4-26B-A4B QAT (52 GB download | QAT-optimized MoE)": "google/gemma-4-26B-A4B-it-qat-q4_0-unquantized",
    "🔴 Gemma-4-31B    (70 GB download → 18 GB VRAM @4-bit | 24GB+ max quality)": "google/gemma-4-31B-it",
    "🔴 Gemma-4-31B QAT (63 GB download | QAT-optimized, 10% smaller)": "google/gemma-4-31B-it-qat-q4_0-unquantized",
    # Pre-quantized Gemma 4 — GPTQ/AWQ checkpoints that skip the BF16 download
    # entirely. These load ~3x faster than BF16+bnb-quantize for the same result.
    # Requires auto-gptq or autoawq package respectively (auto-installed by
    # transformers on first load if not present).
    "🟠 Gemma-4-12B GPTQ (7 GB download | 4-bit pre-quantized)": "Vishva007/gemma-4-12B-it-W4A16-AutoRound-GPTQ",
    "🟠 Gemma-4-12B AWQ  (7 GB download | 4-bit pre-quantized)": "Vishva007/gemma-4-12B-it-W4A16-AutoRound-AWQ",
    "🔴 Gemma-4-26B AWQ  (14 GB download | 4-bit pre-quantized MoE)": "mattbucci/gemma-4-26B-AWQ",
    # Hugging Face Inference API — remote, no local weights needed. Picked via
    # the same model dropdown; models.get_llm() detects the sentinel and builds
    # smolagents.InferenceClientModel instead of loading locally. Requires a
    # HF API token and model ID configured in the Model Settings accordion.
    HF_API_ENTRY_LABEL: HF_INFERENCE_API_SENTINEL,
    # LiteLLM — remote via OpenAI/Anthropic/Groq etc. Picked via the same
    # model dropdown; models.get_llm() detects the sentinel and builds
    # smolagents.LiteLLMModel instead of loading locally. Requires a model
    # ID and API key configured in the Model Settings accordion.
    LITELLM_ENTRY_LABEL: LITELLM_SENTINEL,
}

# MODEL_OPTIONS starts as a copy of the base HuggingFace models. Any local
# .gguf models found under llama_backend.LLAMA_CPP_MODEL_DIR are merged in
# on top of it so they appear in the same dropdowns. The folder is
# user-configurable — via the LLAMA_CPP_MODEL_DIR environment variable at
# startup, or live from the "📁 GGUF Model Folder" box in the UI (see
# rescan_gguf_models() below). Kept as a single dict object that is mutated
# in place (never reassigned) so every module that imported it sees updates.
MODEL_OPTIONS = dict(BASE_MODEL_OPTIONS)
MODEL_OPTIONS.update(llama_backend.discover_gguf_models())

# ──────────────────────────────────────────────────────────────────
# LLM default selection — dynamic per detected hardware tier, following
# README.md's Gemma 4 "Recommended Model / Quantization" ladder:
#   CPU-only / <8GB      -> Gemma-4-E2B (4-bit or Mobile QAT)  1.5-3 GB
#   8-12GB GPU           -> Gemma-4-E4B (4-bit)                3-5 GB
#   16GB GPU             -> Gemma-4-26B-A4B (MoE, 4-bit)       8-14 GB
#   24GB GPU             -> Gemma-4-26B-A4B (MoE, 8-bit)       14-28 GB
#   24GB+ (max quality)  -> Gemma-4-31B (Dense, 4-bit)         18-20 GB
# The max VRAM the ladder targets is 24GB (realistic ceiling) — the
# 48GB+ hardware tier is treated as the "24GB max quality" pick.
# The ladder's quantization column is mirrored by
# get_recommended_quantization(). A saved user override
# (default_llm_label in user_config.json, set via set_default_llm())
# always wins, same persisted-choice pattern as DEFAULT_VLM_LABEL.
# ──────────────────────────────────────────────────────────────────
_LLM_LABEL_BY_TIER = {
    HardwareManager.TIER_CPU_ONLY:  "google/gemma-4-E2B-it",
    HardwareManager.TIER_8GB_VRAM:  "google/gemma-4-E4B-it",
    HardwareManager.TIER_16GB_VRAM: "google/gemma-4-26B-A4B-it",
    HardwareManager.TIER_24GB_VRAM: "google/gemma-4-26B-A4B-it",
    HardwareManager.TIER_48GB_VRAM: "google/gemma-4-31B-it",
    HardwareManager.TIER_UNKNOWN:   "google/gemma-4-E2B-it",
}

# Absolute fallback — the smallest Gemma 4, guaranteed present in every
# install regardless of the detected tier.
_LLM_FALLBACK_MODEL_ID = "google/gemma-4-E2B-it"
_LLM_FALLBACK_LABEL = "🔵 Gemma-4-E2B    (11 GB download → 3 GB VRAM @4-bit | CPU/<8GB tier)"


def _label_for_model_id(model_id: str, options: dict) -> Optional[str]:
    """Reverse-lookup a dropdown label for a model id, or None."""
    for label, val in options.items():
        if val == model_id:
            return label
    return None


def get_recommended_llm_label() -> str:
    """The LLM label README.md's hardware-tier table recommends for THIS
    machine. Falls back to the smallest Gemma 4 (E2B) if the tier can't
    be determined or its model id isn't in the dropdown."""
    tier = HardwareManager.detect_hardware_tier()
    model_id = _LLM_LABEL_BY_TIER.get(tier, _LLM_FALLBACK_MODEL_ID)
    return _label_for_model_id(model_id, MODEL_OPTIONS) or _LLM_FALLBACK_LABEL


def get_default_llm_label() -> str:
    """The LLM label actually selected by default in the UI, unless the
    user has a saved override in user_config.json — mirrors
    get_default_vlm_label()'s persisted-choice-wins pattern."""
    saved = user_config.USER_CONFIG.get("default_llm_label")
    if saved and saved in MODEL_OPTIONS:
        return saved
    return get_recommended_llm_label()


def set_default_llm(label: str) -> None:
    """Persist an explicit default-LLM choice — same pattern as
    set_default_vlm()."""
    user_config.save_user_config({"default_llm_label": label})

# DEFAULT_LLM_LABEL — the label selected by default in the model dropdowns.
# Resolved dynamically via get_default_llm_label() so a saved user override
# (default_llm_label in user_config.json) wins, else the hardware-tier
# recommendation (see _LLM_LABEL_BY_TIER / get_recommended_llm_label()
# below). Unlike the old static default, this lets a capable machine
# default to a Gemma 4 size that actually fits it instead of always the
# smallest.
DEFAULT_LLM_LABEL = get_default_llm_label()
DEFAULT_LLM_MODEL = MODEL_OPTIONS[DEFAULT_LLM_LABEL]


def rescan_gguf_models(folder_path: Optional[str], lang_key: str = "kh"):
    """Set (or change) the GGUF model folder at runtime and rebuild
    MODEL_OPTIONS (text LLMs) and VLM_OPTIONS (vision-model pairs),
    without needing to edit code or restart the app.

    Returns (status_message, text_dropdown_update x3, vlm_dropdown_update)
    so every model dropdown in the UI (General/RAG/Data-Analysis LLM
    pickers, plus the Vision LLM picker) refreshes with the newly
    discovered .gguf models immediately.
    """
    l = LANGUAGES.get(lang_key, LANGUAGES["kh"])
    folder_path = (folder_path or "").strip()

    # Persists to user_config.json and updates llama_backend.LLAMA_CPP_MODEL_DIR
    llama_backend.set_model_dir(folder_path)
    whisper_cpp_backend.set_whisper_model_dir(folder_path)

    MODEL_OPTIONS.clear()
    MODEL_OPTIONS.update(BASE_MODEL_OPTIONS)

    if not folder_path:
        msg = l["gguf_scan_disabled"]
    else:
        found = llama_backend.discover_gguf_models(folder_path)
        MODEL_OPTIONS.update(found)
        vlm_found_count = len(llama_backend.discover_gguf_vlm_models(folder_path))
        if found or vlm_found_count:
            msg = l["gguf_scan_found"].format(n=len(found), dir=folder_path)
            if vlm_found_count:
                msg += f" (+ {vlm_found_count} vision model pair(s) found for the 🎨 Vision LLM dropdown)"
        else:
            msg = l["gguf_scan_empty"].format(dir=folder_path)
        if not llama_backend.LLAMA_CPP_AVAILABLE:
            msg += (" ⚠️ llama-cpp-python not installed — in-process loading unavailable."
                    " Use '⚙️ LLM Backend' > 'llama-server (external process)' to run GGUF models without it.")

    # Vision GGUF pairs (main model + mmproj) are scanned/rebuilt
    # independently of the plain text-model branch above —
    # _rebuild_gguf_vlm_options() already no-ops safely on an
    # empty/invalid folder or a missing llama-cpp-python install.
    _rebuild_gguf_vlm_options(folder_path)

    choices = list(MODEL_OPTIONS.keys())
    default_value = DEFAULT_LLM_LABEL if DEFAULT_LLM_LABEL in choices else (choices[0] if choices else None)
    dd_update = gr.update(choices=choices, value=default_value)

    vlm_choices = list(VLM_OPTIONS.keys())
    vlm_default = DEFAULT_VLM_LABEL if DEFAULT_VLM_LABEL in vlm_choices else (vlm_choices[0] if vlm_choices else None)
    vlm_dd_update = gr.update(choices=vlm_choices, value=vlm_default)

    return msg, dd_update, dd_update, dd_update, vlm_dd_update


# ──────────────────────────────────────────────────────────────────
# Vision LLM (VLM) options
# ──────────────────────────────────────────────────────────────────
BASE_VLM_OPTIONS = {
    "🔵 SmolVLM-256M  (0.5 GB download | tiny)":  "HuggingFaceTB/SmolVLM-256M-Instruct",
    "🔵 SmolVLM-500M  (1 GB download | recommended)": "HuggingFaceTB/SmolVLM-500M-Instruct",
    "🟢 Qwen2.5-VL-3B (6 GB download → 3 GB VRAM @4-bit | 8GB tier)": "Qwen/Qwen2.5-VL-3B-Instruct",
    "🟠 Qwen2.5-VL-7B (15 GB download → 8 GB VRAM @4-bit | 16GB+ tier)": "Qwen/Qwen2.5-VL-7B-Instruct",
    # Gemma 4 supplement — every Gemma 4 base model is multimodal, so each
    # one doubles as a Vision Chat model (loaded via the "gemma4" VLM arch).
    # Sizes match the LLM dropdown since the checkpoints are shared.
    "🧠 Gemma-4-E4B Mobile QAT (4 GB download | edge)": "google/gemma-4-e4b-it-qat-mobile-transformers",
    "🔵 Gemma-4-E2B   (11 GB download → 3 GB VRAM @4-bit | CPU/<8GB tier)": "google/gemma-4-E2B-it",
    "🟢 Gemma-4-E4B   (18 GB download → 5 GB VRAM @4-bit | 8-12GB tier)": "google/gemma-4-E4B-it",
    HF_API_ENTRY_LABEL: HF_INFERENCE_API_SENTINEL,
}

# VLM_OPTIONS starts as a copy of the base HuggingFace VLMs. Any local
# GGUF vision-model pairs (main .gguf + matching mmproj .gguf) found
# under llama_backend.LLAMA_CPP_MODEL_DIR are merged in on top of it —
# same pattern as MODEL_OPTIONS for text LLMs — so they appear in the
# same "🎨 Vision LLM" dropdown. Kept as a single dict object that is
# mutated in place (never reassigned) so every module that imported it
# sees updates.
VLM_OPTIONS = dict(BASE_VLM_OPTIONS)

# Default VLM selection — dynamic per detected hardware tier, mirroring
# README.md's "Vision Model (HF/transformers)" column: Qwen2.5-VL-7B-
# Instruct is the recommended pick from the 16GB-VRAM tier upward, since
# every GGUF vision option in that table needs a llama_backend.py
# chat-handler update this app doesn't have yet (see the README's
# "Compatibility note"). Below that tier, the existing small SmolVLM-500M
# stays the default — a 7B VLM would be a poor default on modest/CPU-only
# hardware. A saved user override (see set_default_vlm()) always wins,
# same persisted-choice pattern as DEFAULT_EMBED_MODEL above.
_VLM_LABEL_BY_TIER = {
    HardwareManager.TIER_48GB_VRAM: "🟠 Qwen2.5-VL-7B (15 GB download → 8 GB VRAM @4-bit | 16GB+ tier)",
    HardwareManager.TIER_24GB_VRAM: "🟠 Qwen2.5-VL-7B (15 GB download → 8 GB VRAM @4-bit | 16GB+ tier)",
    HardwareManager.TIER_16GB_VRAM: "🟠 Qwen2.5-VL-7B (15 GB download → 8 GB VRAM @4-bit | 16GB+ tier)",
    HardwareManager.TIER_8GB_VRAM:  "🔵 SmolVLM-500M  (1 GB download | recommended)",
    HardwareManager.TIER_CPU_ONLY:  "🔵 SmolVLM-500M  (1 GB download | recommended)",
    HardwareManager.TIER_UNKNOWN:   "🔵 SmolVLM-500M  (1 GB download | recommended)",
}


def get_recommended_vlm_label() -> str:
    """The Vision LLM label README.md's hardware-tier table recommends
    for THIS machine. Falls back to the small SmolVLM-500M default if the
    tier can't be determined."""
    tier = HardwareManager.detect_hardware_tier()
    return _VLM_LABEL_BY_TIER.get(tier, "🔵 SmolVLM-500M  (~1 GB RAM | recommended)")


def get_default_vlm_label() -> str:
    """The VLM label actually selected by default in the UI, unless the
    user has a saved override in user_config.json — mirrors
    get_default_embed_model()'s persisted-choice-wins pattern."""
    saved = user_config.USER_CONFIG.get("default_vlm_label")
    if saved and saved in VLM_OPTIONS:
        return saved
    return get_recommended_vlm_label()


def set_default_vlm(label: str) -> None:
    """Persist an explicit default-VLM choice — same pattern as
    set_embed_model()."""
    user_config.save_user_config({"default_vlm_label": label})


DEFAULT_VLM_LABEL = get_default_vlm_label()
DEFAULT_VLM_MODEL = VLM_OPTIONS[DEFAULT_VLM_LABEL]

# Maps a GGUF vision model's main .gguf path -> its paired mmproj (vision
# projector) .gguf path (see llama_backend.discover_gguf_vlm_models()).
# models.get_vlm() looks this up by model_id, since llama.cpp needs BOTH
# files' paths to actually load a GGUF vision model — unlike text-only
# GGUF models, which need just the one file.
GGUF_VLM_MMPROJ_MAP = {}

# Maps a GGUF vision model's main .gguf path -> {label: mmproj_path} for
# all compatible mmproj files in the same folder. Populated by
# _rebuild_gguf_vlm_options(). Used by the mmproj dropdown in Vision Chat.
VLM_MMPROJ_CANDIDATES_MAP: dict[str, dict[str, str]] = {}


def get_mmproj_choices_for_vlm(model_path: str) -> dict[str, str]:
    """Return {label: mmproj_path} for the mmproj dropdown in Vision Chat.
    If explicit candidates exist for this model path, return those.
    Otherwise fall back to scanning the model's folder."""
    cached = VLM_MMPROJ_CANDIDATES_MAP.get(model_path)
    if cached:
        return cached
    fresh = llama_backend.get_mmproj_candidates_for_model(model_path)
    if fresh:
        VLM_MMPROJ_CANDIDATES_MAP[model_path] = fresh
    return fresh


def _rebuild_gguf_vlm_options(folder: Optional[str] = None):
    """(Re)populate VLM_OPTIONS with discovered GGUF vision-model pairs
    from `folder` (or the current LLAMA_CPP_MODEL_DIR) and refresh
    GGUF_VLM_MMPROJ_MAP and VLM_MMPROJ_CANDIDATES_MAP to match.
    Mutates all dicts in place (never reassigns), same pattern as
    MODEL_OPTIONS's text-LLM rescan."""
    VLM_OPTIONS.clear()
    VLM_OPTIONS.update(BASE_VLM_OPTIONS)
    GGUF_VLM_MMPROJ_MAP.clear()
    VLM_MMPROJ_CANDIDATES_MAP.clear()
    for label, (model_path, mmproj_path) in llama_backend.discover_gguf_vlm_models(folder).items():
        VLM_OPTIONS[label] = model_path
        GGUF_VLM_MMPROJ_MAP[model_path] = mmproj_path
        candidates = llama_backend.get_mmproj_candidates_for_model(model_path)
        if candidates:
            VLM_MMPROJ_CANDIDATES_MAP[model_path] = candidates


_rebuild_gguf_vlm_options()

# ──────────────────────────────────────────────────────────────────
# Visual retriever (ColPali-style, for visual PDF RAG) options
# ──────────────────────────────────────────────────────────────────
VISUAL_RETRIEVER_OPTIONS = {
    "vidore/colsmolvlm-v0.1  (~2 GB | recommended)": "vidore/colsmolvlm-v0.1",
    "vidore/colqwen2-v1.0    (~8 GB | higher accuracy)": "vidore/colqwen2-v1.0",
}
DEFAULT_VISUAL_RETRIEVER = "vidore/colsmolvlm-v0.1"

# ──────────────────────────────────────────────────────────────────
# Speech-to-Text (Whisper) options
# ──────────────────────────────────────────────────────────────────
STT_OPTIONS = {
    "🟢 Whisper-tiny    (~1 GB RAM | fastest)":   "openai/whisper-tiny",
    "🟡 Whisper-base    (~1 GB RAM)":              "openai/whisper-base",
    "🟡 Whisper-small   (~2 GB RAM | recommended)": "openai/whisper-small",
    "🔵 Whisper-large-v3 (~10 GB RAM | best accuracy, multilingual incl. Khmer)": "openai/whisper-large-v3",
    "🇰🇭 Whisper-small — ខ្មែរ (~1 GB RAM | Khmer-tuned)": "seanghay/whisper-small-khmer-v2",
    "🇰🇭 Whisper-large-v3-turbo — ខ្មែរ (~6 GB RAM | best for Khmer)": "metythorn/whisper-large-v3-turbo-mixed-20eps-clean-text-197k",
}
DEFAULT_STT_LABEL = "🇰🇭 Whisper-small — ខ្មែរ (~1 GB RAM | Khmer-tuned)"
DEFAULT_STT_MODEL = STT_OPTIONS[DEFAULT_STT_LABEL]
