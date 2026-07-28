"""
models.py — Lazy-loaded model backends: embedding model, ChromaDB handle,
text LLM (HuggingFace or GGUF via llama_backend), Vision LLM, and
Speech-to-Text pipeline. Each model type keeps its own module-level cache
and lock, following the lazy-load/lock pattern used throughout the app.
"""

import gc
import threading
import time
from typing import Optional

import torch

import llama_backend
import model_registry as mr
import whisper_cpp_backend
from hardware import DEVICE, TORCH_DTYPE
from i18n import LANGUAGES

_embed_model         = None
_embed_model_id      = None
_embed_lock          = threading.Lock()
_chroma_col          = None
_llm                 = None
_llm_model_id        = mr.DEFAULT_LLM_MODEL
# Context window (n_ctx) the currently-loaded LLM was built with — only
# meaningful for the GGUF/llama.cpp backend (see model_registry.py's
# CONTEXT_WINDOW_OPTIONS). None until a GGUF model has actually been
# loaded at least once; HF/transformers models leave this as None too,
# since n_ctx doesn't apply to them.
_llm_n_ctx           = None

# ──────────────────────────────────────────────────────────────────
# Some newer HuggingFace checkpoints ship architectures that only
# `transformers` releases from a certain version onward know how to
# build (as opposed to older custom-arch models that ship their own
# `trust_remote_code` modeling file and work on any transformers
# version). deepreinforce-ai/Ornith-1.0-9B is one of these: it's a
# Qwen3.5 hybrid linear-/full-attention ("qwen35") architecture that
# requires transformers >= 5.8.1 to even recognize the config class —
# on an older install this fails with a confusing
# "Unrecognized configuration class" / KeyError deep inside
# AutoModelForCausalLM.from_pretrained() instead of a clear message.
# Keyed by the model ids in model_registry.ORNITH_IDS so this stays a
# single source of truth if more Ornith-family models are added later.
# ──────────────────────────────────────────────────────────────────
_MIN_TRANSFORMERS_VERSION = {
    "ornith": "5.8.1",
    # Qwen3.6 (dense Qwen3.6-27B, MoE Qwen3.6-35B-A3B) uses the "qwen3_5"
    # architecture — confirmed via community reports that transformers
    # <5.2.0 doesn't recognize it (same "config class not found" failure
    # mode as Ornith above). Now wired into BASE_MODEL_OPTIONS (see
    # model_registry.QWEN36_IDS) — loading it with an older transformers
    # fails with a clear upgrade message rather than a cryptic AutoModel
    # crash.
    "qwen36": "5.2.0",
    # Gemma 4 (E2B/E4B/12B/26B-A4B/31B) introduced the "gemma4" model type
    # in transformers 5.5.0 — confirmed directly via huggingface/transformers
    # issue #45376 and multiple vLLM/llm-compressor compatibility reports.
    # Google's own docs recommend >=5.10.1. Below 5.5.0, AutoConfig can't
    # even parse the checkpoint's config.json (fails with a confusing
    # "'list' object has no attribute 'keys'" deep in tokenizer setup,
    # not a clear version message) — this guard replaces that with an
    # actionable error. Applies to google/gemma-4-E2B-it (the app's
    # existing default!) as much as any newly-registered Gemma 4 size.
    "gemma4": "5.10.1",
}

# Model-id-set -> (version-guard key, human-readable architecture note).
# Checked in order; first matching set wins. Table-driven so adding a new
# guarded family is one line here instead of another elif branch.
def _version_guard_families():
    return (
        (mr.ORNITH_IDS, "ornith", "Qwen3.5 hybrid linear-/full-attention architecture"),
        (mr.QWEN36_IDS, "qwen36", "Qwen3.6 (qwen3_5) architecture"),
        (mr.GEMMA4_IDS, "gemma4", "Gemma 4 (gemma4) multimodal architecture"),
    )


def _version_tuple(version_str: str) -> tuple:
    """Parse a dotted version string into a comparable tuple of ints,
    ignoring any non-numeric suffix (e.g. 'dev0', 'rc1') per component."""
    parts = []
    for p in str(version_str).split(".")[:3]:
        digits = "".join(ch for ch in p if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def _check_transformers_version_for(model_id: str) -> None:
    """Raise a clear, actionable RuntimeError if the installed
    `transformers` version is too old to load `model_id`, instead of
    letting a cryptic internal AutoModel error surface first."""
    min_version = None
    arch_note = None
    for id_set, guard_key, note in _version_guard_families():
        if model_id in id_set:
            min_version = _MIN_TRANSFORMERS_VERSION[guard_key]
            arch_note = note
            break
    if min_version is None:
        return
    import transformers as _tf
    installed = getattr(_tf, "__version__", "0")
    if _version_tuple(installed) < _version_tuple(min_version):
        raise RuntimeError(
            f"'{model_id}' needs transformers >= {min_version} — it's a "
            f"{arch_note} that older "
            f"transformers releases don't recognize. You have {installed} "
            f"installed.\n\n"
            f"Upgrade with:\n"
            f'  pip install --upgrade "transformers>={min_version}"\n\n'
            f"Then restart the app and try loading the model again."
        )
_vlm_model           = None
_vlm_processor       = None
_vlm_model_id        = None
_llm_lock            = threading.Lock()
_vlm_lock            = threading.Lock()
_stt_pipeline        = None
_stt_model_id        = None
_stt_lock            = threading.Lock()


def _release_model(obj):
    """Explicitly free memory held by a model before dropping the last
    Python reference to it.

    Just setting a global cache variable to None does NOT free GPU/CPU
    memory right away:
      - transformers/torch models: the CUDA caching allocator keeps the
        freed blocks around until torch.cuda.empty_cache() runs (and that
        can only reclaim memory from tensors that have already been
        garbage-collected).
      - llama.cpp (llama-cpp-python) models: the native context / KV-cache
        lives in a C++ object. Its Python wrapper's __del__ will eventually
        close it, but only once the GC actually runs the finalizer — which
        is not guaranteed to happen before the next model tries to load,
        causing an OOM when switching models back-to-back.

    Calling this before overwriting/loading a new model avoids the
    "previous model didn't offload, so the next one fails to load" issue.
    """
    if obj is None:
        return

    # llama-server (external process) backend: LlamaServerModel and
    # LlamaServerVLMModel have no in-process model/KV-cache to release —
    # the real memory lives in the separate llama-server subprocess.
    # "Releasing" this object means stopping that subprocess, not any of
    # the torch/llama.cpp cleanup below (which doesn't apply — there's no
    # `.llm`/`.model` attribute holding real weights in this Python process).
    if isinstance(obj, (llama_backend.LlamaServerModel, llama_backend.LlamaServerVLMModel)):
        llama_backend.stop_llama_server()
        del obj
        return

    try:
        # llama.cpp backend: LlamaCppModel wraps the native llama_cpp.Llama
        # instance as `.llm` — close it explicitly to free the KV-cache /
        # context right now instead of waiting on GC.
        inner = getattr(obj, "llm", None)
        if inner is not None and hasattr(inner, "close"):
            try:
                inner.close()
            except Exception:
                pass

        # transformers / smolagents TransformersModel: move the underlying
        # nn.Module off the GPU before dropping it so CUDA's allocator can
        # actually reclaim the memory once we empty_cache() below.
        model_attr = getattr(obj, "model", None)
        if model_attr is not None and hasattr(model_attr, "to"):
            try:
                model_attr.to("cpu")
            except Exception:
                pass
    except Exception:
        pass

    del obj
    gc.collect()
    try:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            torch.mps.empty_cache()
    except Exception:
        pass


def get_embed_model(model_id: Optional[str] = None):
    """Lazily build (or rebuild, if the model id changed) the shared
    embedding model instance.

    `model_id` lets the "🧩 Embedding Model" control on the Knowledge Base
    tab (see ui.py) switch models at runtime, the same way get_llm()/
    get_vlm() already do for their tabs. If not given, falls back to
    whatever embedding model was last loaded, or — on first call —
    model_registry.get_default_embed_model() (persisted override, or the
    hardware-tier recommendation).

    IMPORTANT: switching to a DIFFERENT embedding model does NOT re-embed
    anything already stored in ChromaDB. Vectors from two different
    embedding models are not comparable, and ChromaDB locks a collection
    to whatever dimension it was first created with — so switching after
    documents are already indexed will make retrieval fail with a
    dimension-mismatch error (see knowledge_base.retrieve_context()'s
    friendlier error for this) until you either switch back to the
    original embedding model, or clear the index and re-index everything
    with the new one. ui.py's embedding-model "Load" button warns about
    this before switching.
    """
    global _embed_model, _embed_model_id
    target = model_id or _embed_model_id or mr.DEFAULT_EMBED_MODEL

    if _embed_model is not None and target == _embed_model_id:
        return _embed_model

    with _embed_lock:
        if _embed_model is not None and target == _embed_model_id:
            return _embed_model

        if _embed_model is not None:
            print(f"[RAG] Unloading previous embedding model '{_embed_model_id}' before loading '{target}' …")
            _release_model(_embed_model)
            _embed_model = None

        # ── HF Inference API ──────────────────────────────────────
        if target == mr.HF_INFERENCE_API_SENTINEL:
            hf_model_id = mr.get_saved_hf_model_id()
            if not hf_model_id:
                raise ValueError(
                    "Hugging Face Inference API selected for Embedding, but no "
                    "model ID is configured."
                )
            _embed_model = InferenceApiEmbeddingModel(model_id=hf_model_id)
            _embed_model_id = target
            return _embed_model

        # ── llama.cpp server embeddings ──────────────────────────
        if str(target).lower().endswith(".gguf"):
            print(f"[RAG] Starting llama-server for embeddings with '{target}' …")
            base_url = llama_backend.get_or_start_llama_server(
                model_path=target,
                n_ctx=mr.get_saved_context_window(),
                n_gpu_layers=-1,  # external llama-server has its own GPU support
            )
            _embed_model = EmbeddingServerModel(
                model_path=target, base_url=base_url,
            )
            _embed_model_id = target
            return _embed_model

        # ── Local HuggingFace SentenceTransformer ────────────────
        print(f"[RAG] Loading embedding model '{target}' on {DEVICE.upper()} …")
        from sentence_transformers import SentenceTransformer
        try:
            _embed_model = SentenceTransformer(target, device=DEVICE, trust_remote_code=True)
        except TypeError:
            _embed_model = SentenceTransformer(target, device=DEVICE)
        _embed_model_id = target
        return _embed_model


def force_reload_embed_model(target_model_id: str):
    """Used by the Knowledge Base tab's "🧩 Embedding Model" Load button:
    fully release whatever embedding model is currently loaded (regardless
    of id) and load `target_model_id` fresh — mirrors force_reload_llm()/
    force_reload_vlm()/force_reload_stt()."""
    global _embed_model, _embed_model_id
    _release_model(_embed_model)
    _embed_model = None
    _embed_model_id = None
    return get_embed_model(target_model_id)


def unload_embed_model_fn(lang_key: str = "kh") -> str:
    """Explicit "force unload from VRAM" action for the embedding model —
    mirrors unload_llm_fn()/unload_vlm_fn()/unload_stt_fn()."""
    global _embed_model, _embed_model_id
    l = LANGUAGES.get(lang_key, LANGUAGES["kh"])
    if _embed_model is None:
        return l["btn_unload_none"]
    mid = _embed_model_id
    _release_model(_embed_model)
    _embed_model = None
    _embed_model_id = None
    return l["msg_unloaded"].format(model=mid)


def encode_texts(texts: list, normalize: bool = True):
    embed = get_embed_model()
    # InferenceApiEmbeddingModel and EmbeddingServerModel have their own
    # encode() with a different signature.
    if hasattr(embed, "encode") and hasattr(embed, "model_id"):
        return embed.encode(texts, normalize=normalize)
    vecs = embed.encode(texts, normalize_embeddings=normalize,
                        show_progress_bar=False)
    return vecs.tolist() if hasattr(vecs, "tolist") else vecs


def get_chroma_collection(name: str = "rag_docs"):
    # NOTE: deliberately no "[RAG] ChromaDB ready — N chunks indexed."
    # print here anymore. This function is called from ui.py's
    # demo.load(kb.get_index_stats, ...) right after the UI mounts (see
    # ui.py's comment on why that's deferred rather than eager), so the
    # line used to show up in the terminal on every single app startup —
    # it did NOT mean an LLM/embedding model was being preloaded, only
    # that the ChromaDB persistent client had opened. Removed as pure
    # console noise; the same info is already visible in the UI's status
    # bar (kb.get_index_stats()) without needing a terminal print.
    global _chroma_col

    # Use a dimension-aware collection name so that switching to a
    # different embedding model automatically gets its own ChromaDB
    # collection instead of reusing one built with a different vector
    # dimension (which causes the "Collection expecting embedding with
    # dimension of 1024, got 2560" error).
    # When no embedding model is loaded yet, fall back to the hardcoded
    # dimensions table in model_registry.py for the saved/active embed
    # model id.
    _dim_name = None
    if _embed_model is not None:
        mid = getattr(_embed_model, 'model_name', None) or getattr(_embed_model, 'name', None)
        _dim_name = mr.EMBED_MODEL_DIMENSIONS.get(mid)
        if _dim_name is None and hasattr(_embed_model, 'get_sentence_transformer_model'):
            try:
                cfg = _embed_model.get_sentence_transformer_model().config
                _dim_name = getattr(cfg, 'hidden_size', None) or getattr(cfg, 'projection_dim', None)
            except Exception:
                pass
    if _dim_name is None:
        _dim_name = mr.EMBED_MODEL_DIMENSIONS.get(_embed_model_id, None)
    if _dim_name is None:
        _dim_name = mr.EMBED_MODEL_DIMENSIONS.get(mr.DEFAULT_EMBED_MODEL, 1024)

    _dim_name = f"rag_docs_{_dim_name}d"

    if _chroma_col is not None:
        old_name = getattr(_chroma_col, 'name', None)
        if old_name is not None and old_name != _dim_name:
            try:
                import chromadb
                chromadb.PersistentClient(path=mr.CHROMA_PERSIST_DIR).delete_collection(old_name)
            except Exception:
                pass
            print(f"[RAG] Old ChromaDB collection '{old_name}' removed after embedding model switch.")
            _chroma_col = None

    if _chroma_col is None:
        import chromadb
        client = chromadb.PersistentClient(path=mr.CHROMA_PERSIST_DIR)
        _chroma_col = client.get_or_create_collection(
            name=_dim_name, metadata={"hnsw:space": "cosine"})
    return _chroma_col


def reset_chroma_collection():
    """Used by clear_index() in knowledge_base.py to drop and recreate the
    collection object after deleting it from disk."""
    global _chroma_col
    _chroma_col = None


def get_llm(model_id: Optional[str] = None, n_ctx: Optional[int] = None):
    """Lazily build (or rebuild, if the model id OR the requested context
    window changed) the shared LLM instance.

    `n_ctx` (context window, in tokens) only applies to the GGUF/llama.cpp
    backend — see model_registry.CONTEXT_WINDOW_OPTIONS. If not given
    explicitly, it falls back to whatever context window the currently
    loaded model was built with, or — if nothing has been loaded yet — the
    persisted default from model_registry.get_saved_context_window(). This
    means callers that don't care about context window (most of them) can
    keep calling get_llm(model_id) exactly as before, and it'll keep using
    whatever context window was last chosen (via the UI's global "Context
    Window" control) without having to thread it through every call site.

    NOTE: this function is only ever invoked on-demand — the first time a
    chat tab is actually used, a "Load" button is clicked, or an agentic
    tab builds its CodeAgent (see general_agent.py / rag_agent.py /
    data_analysis.py). Nothing in app.py or ui.py calls this at startup,
    so no LLM is loaded in advance; the app only pays the model-loading
    cost the first time it's actually needed.
    """
    global _llm, _llm_model_id, _llm_n_ctx
    target = model_id or _llm_model_id
    is_gguf = str(target).lower().endswith(".gguf")
    target_ctx = n_ctx if n_ctx is not None else (_llm_n_ctx or mr.get_saved_context_window())
    # A context-window change only matters (and only requires a reload) for
    # the GGUF backend — n_ctx is baked into llama.cpp's KV-cache at load
    # time and can't be changed on a live model. HF/transformers models
    # ignore n_ctx entirely, so changing it should never trigger a
    # needless reload of an already-loaded HF model.
    ctx_changed = is_gguf and target_ctx != _llm_n_ctx

    if _llm is not None and target == _llm_model_id and not ctx_changed:
        return _llm

    with _llm_lock:
        if _llm is not None and target == _llm_model_id and not ctx_changed:
            return _llm

        if _llm is not None:
            reason = (f"context window changed to {target_ctx} tokens"
                      if ctx_changed else f"loading '{target}'")
            print(f"[RAG] Unloading previous LLM '{_llm_model_id}' before {reason} …")
            _release_model(_llm)
            _llm = None

        if is_gguf:
            # Which backend actually RUNS this .gguf file — in-process
            # (llama-cpp-python, the original default) or an external
            # `llama-server` process talked to over HTTP. See
            # model_registry.LLM_BACKEND_MODE_OPTIONS / the "⚙️ LLM
            # Backend" dropdown in the UI. Only affects HOW the model
            # runs, not which .gguf file/folder it comes from.
            backend_mode = mr.get_saved_llm_backend_mode()

            if backend_mode == "server":
                print(f"[RAG] Starting/reusing llama-server for '{target}' with "
                      f"context window {target_ctx} tokens …")
                base_url = llama_backend.get_or_start_llama_server(
                    model_path=target,
                    n_ctx=target_ctx,
                    n_gpu_layers=-1,  # external llama-server has its own GPU support
                )
                _llm = llama_backend.LlamaServerModel(
                    base_url=base_url,
                    model_path=target,
                    temperature=0.6,
                    top_p=0.95,
                    max_new_tokens=mr.get_saved_max_new_tokens(),
                    # Per-request HTTP timeout (seconds) — user-configurable
                    # via the "⏱️ llama-server Request Timeout" dropdown (see
                    # model_registry.get_saved_llm_server_timeout()) instead
                    # of silently using LlamaServerModel's hardcoded 300s
                    # default. A large/slow model with a long agentic prompt
                    # (e.g. Deep Research's manager+sub-agent history) can
                    # easily need more than 300s per generation — see that
                    # function's docstring for the full "Error in code
                    # parsing" failure mode this fixes.
                    timeout=mr.get_saved_llm_server_timeout(),
                )
                _llm_n_ctx = target_ctx

            else:
                if not llama_backend.LLAMA_CPP_AVAILABLE:
                    if llama_backend.LLAMA_SERVER_EXE_PATH:
                        print(f"[RAG] llama-cpp-python not installed — auto-fallbacking "
                              f"to llama-server (external process) for '{target}' …")
                        base_url = llama_backend.get_or_start_llama_server(
                            model_path=target,
                            n_ctx=target_ctx,
                            n_gpu_layers=-1,  # external llama-server has its own GPU support
                        )
                        _llm = llama_backend.LlamaServerModel(
                            base_url=base_url,
                            model_path=target,
                            temperature=0.6,
                            top_p=0.95,
                            max_new_tokens=mr.get_saved_max_new_tokens(),
                            timeout=mr.get_saved_llm_server_timeout(),
                        )
                        _llm_n_ctx = target_ctx
                        _llm_model_id = target
                        return _llm
                    raise RuntimeError(
                        "llama-cpp-python is not installed, and no llama-server "
                        "executable is configured.\n\n"
                        "Option 1: Run SETUP.bat to install llama-cpp-python "
                        "(supports GPU offload).\n"
                        "Option 2: Set the '🖥️ llama-server.exe Path' under Model "
                        "Settings to point at a llama-server.exe binary from "
                        "https://github.com/ggml-org/llama.cpp/releases — then "
                        "GGUF models run via the external server instead."
                    )
                print(f"[RAG] Loading GGUF LLM '{target}' with context window "
                      f"{target_ctx} tokens on {DEVICE.upper()} …")
                try:
                    _llm = llama_backend.LlamaCppModel(
                        model_path=target,
                        n_ctx=target_ctx,
                        # -1 offloads every layer to GPU; on a CPU-only llama-cpp-python
                        # build this is harmless (llama.cpp silently ignores it and runs
                        # on CPU), but we set 0 explicitly once we know for sure so the
                        # load logs are accurate instead of claiming a GPU offload that
                        # won't happen.
                        n_gpu_layers=-1 if llama_backend.LLAMA_CPP_GPU_AVAILABLE else 0,
                        # Flash attention only helps (and is only reliably supported)
                        # when the model is actually running on GPU; LlamaCppModel
                        # itself also falls back gracefully if a specific model's
                        # architecture rejects FA even when the GPU build supports it.
                        flash_attn=llama_backend.LLAMA_CPP_GPU_AVAILABLE,
                        temperature=0.6,
                        top_p=0.95,
                        max_new_tokens=mr.get_saved_max_new_tokens(),
                    )
                except Exception as e:
                    # A larger n_ctx needs a proportionally larger KV-cache —
                    # on GPU this can OOM even when a smaller context window
                    # for the exact same model loaded fine. Make that
                    # connection explicit instead of leaving the user to
                    # guess from a raw allocation-failure message.
                    if target_ctx > 16384 and ("memory" in str(e).lower() or "alloc" in str(e).lower()):
                        raise RuntimeError(
                            f"Failed to load '{target}' with a {target_ctx}-token context "
                            f"window — this likely ran out of VRAM/RAM, since the KV-cache "
                            f"size grows with n_ctx. Try a smaller context window from the "
                            f"'🧠 Context Window' dropdown, or a smaller/more-quantized model.\n\n"
                            f"Original error: {e}"
                        ) from e
                    raise
                _llm_n_ctx = target_ctx
        elif target == mr.HF_INFERENCE_API_SENTINEL:
            from smolagents import InferenceClientModel
            hf_model_id = mr.get_saved_hf_model_id()
            hf_token = mr.get_saved_hf_token() or None
            hf_provider = mr.get_saved_hf_provider() or None
            if not hf_model_id:
                raise ValueError(
                    "Hugging Face Inference API selected, but no model ID is configured. "
                    "Enter a model ID in the '🤗 HF Model ID' field under Model Settings."
                )
            if ":" in hf_model_id and not hf_provider:
                hf_model_id, hf_provider = hf_model_id.rsplit(":", 1)
            print(f"[RAG] Using Hugging Face Inference API: model={hf_model_id} provider={hf_provider or 'auto'}")
            _llm = InferenceClientModel(
                model_id=hf_model_id,
                token=hf_token,
                provider=hf_provider,
                max_tokens=mr.get_saved_max_new_tokens(),
            )
            _llm_n_ctx = None
        elif target == mr.LITELLM_SENTINEL:
            try:
                from smolagents import LiteLLMModel
            except ImportError:
                raise RuntimeError(
                    "LiteLLM is not installed. Run: pip install 'smolagents[litellm]'"
                )
            litellm_model_id = mr.get_saved_litellm_model_id()
            litellm_api_key  = mr.get_saved_litellm_api_key() or None
            litellm_api_base = mr.get_saved_litellm_api_base() or None
            if not litellm_model_id:
                raise ValueError(
                    "LiteLLM selected, but no model ID is configured. "
                    "Enter a model ID in the '🔗 LiteLLM Model ID' field "
                    "under Model Settings."
                )
            print(f"[RAG] Using LiteLLM: model={litellm_model_id} base={litellm_api_base or 'default'}")
            _llm = LiteLLMModel(
                model_id=litellm_model_id,
                api_key=litellm_api_key,
                api_base=litellm_api_base,
                max_completion_tokens=mr.get_saved_max_new_tokens(),
            )
            _llm_n_ctx = None
        else:
            _check_transformers_version_for(target)
            import inspect
            from smolagents import TransformersModel
            print(f"[RAG] Loading LLM '{target}' on {DEVICE.upper()} …")

            base_kwargs = dict(
                model_id=target,
                device_map=DEVICE,
                max_new_tokens=mr.get_saved_max_new_tokens(),
                temperature=0.6,
                top_p=0.95,
                trust_remote_code=True,
            )
            # smolagents' TransformersModel constructor only recognizes a
            # fixed set of named parameters for MODEL LOADING (model_id,
            # device_map, torch_dtype, trust_remote_code, model_kwargs,
            # max_new_tokens, ...) — see
            # https://huggingface.co/docs/smolagents/en/reference/models.
            # Anything passed that ISN'T one of those named parameters
            # does NOT raise a TypeError; it's silently absorbed into
            # TransformersModel's own **kwargs, which it then re-forwards
            # into EVERY subsequent model.generate() call, not just at
            # load time. Passing `dtype=` here (a name TransformersModel's
            # constructor doesn't define) used to slip through this way —
            # load succeeded with no error, and the model only blew up the
            # first time an agent actually tried to generate, with
            # "The following `model_kwargs` are not used by the model:
            # ['dtype']" — easy to misread as a tool-calling problem
            # rather than a stale kwarg name. Detect the real parameter
            # name instead of guessing, so this fails loudly at load time
            # (a clear, immediate error) if some future smolagents version
            # renames it again.
            ctor_params = inspect.signature(TransformersModel.__init__).parameters
            if "torch_dtype" in ctor_params:
                base_kwargs["torch_dtype"] = TORCH_DTYPE
            elif "dtype" in ctor_params:
                base_kwargs["dtype"] = TORCH_DTYPE
            else:
                print(
                    "[RAG] Warning: installed smolagents' TransformersModel exposes "
                    "neither 'torch_dtype' nor 'dtype' as a constructor parameter — "
                    "loading without an explicit dtype (will use the model's default)."
                )
            _llm = TransformersModel(**base_kwargs)
            # n_ctx doesn't apply to the HF backend — clear it so a later
            # switch back to a GGUF model doesn't skip a reload it needs
            # by comparing against a stale value from a previous GGUF load.
            _llm_n_ctx = None
        _llm_model_id = target
        return _llm


def _call_llm(model_id: str, system: str, user: str, history: Optional[list] = None) -> tuple[str, float]:
    """Direct (non-agentic) single-turn-or-multi-turn LLM call, shared by
    General Chat's and RAG Chat's *direct* paths (chat.py).

    Built as a plain list of smolagents `ChatMessage`s — the same message
    object smolagents' own `CodeAgent`/`TransformersModel`/`LlamaCppModel`
    machinery uses internally — so this goes through the exact same
    `model(messages)` call contract as the agentic paths, just without a
    CodeAgent wrapped around it. `role` is passed via smolagents'
    `MessageRole` enum rather than a bare string, matching how smolagents
    documents/constructs `ChatMessage` itself.

    `history` (optional): prior turns as `[{"role": "user"|"assistant",
    "content": str}, ...]`, coming from chat.py's `_recent_memory_messages()`.
    Folded in between the system prompt and the current `user` message so
    follow-up questions can refer back to earlier turns — see chat.py's
    "🧠 Conversation Memory" checkbox.
    """
    from smolagents.models import ChatMessage, MessageRole

    llm = get_llm(model_id)

    messages = [
        ChatMessage(role=MessageRole.SYSTEM, content=[{"type": "text", "text": system}])
    ]
    for turn in (history or []):
        role = turn.get("role")
        content = turn.get("content", "")
        if not content:
            continue
        if role == "user":
            msg_role = MessageRole.USER
        elif role == "assistant":
            msg_role = MessageRole.ASSISTANT
        else:
            continue
        messages.append(ChatMessage(role=msg_role, content=[{"type": "text", "text": content}]))
    messages.append(ChatMessage(role=MessageRole.USER, content=[{"type": "text", "text": user}]))

    t0  = time.time()
    out = llm(messages)
    if hasattr(out, "content"):
        c = out.content
        if isinstance(c, list):
            ans = " ".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in c)
        else:
            ans = str(c)
    else:
        ans = str(out)
    return ans.strip(), time.time() - t0


def get_vlm(model_id: Optional[str] = None, mmproj_path: Optional[str] = None):
    global _vlm_model, _vlm_processor, _vlm_model_id

    target = model_id or mr.DEFAULT_VLM_MODEL

    if _vlm_model is not None and target == _vlm_model_id:
        return _vlm_model, _vlm_processor

    if _vlm_model is not None:
        print(f"[VLM] Unloading previous VLM '{_vlm_model_id}' before loading '{target}' …")
        _release_model(_vlm_model)
        _vlm_model = None
        _vlm_processor = None

    # ── HF Inference API ──────────────────────────────────────────
    if target == mr.HF_INFERENCE_API_SENTINEL:
        hf_model_id = mr.get_saved_hf_model_id()
        if not hf_model_id:
            raise ValueError(
                "Hugging Face Inference API selected for Vision, but no "
                "model ID is configured. Enter a model ID in the "
                "'🤗 HF Model ID' field under Model Settings."
            )
        _vlm_model = InferenceApiVLMModel(model_id=hf_model_id)
        _vlm_processor = None
        _vlm_model_id = target
        return _vlm_model, _vlm_processor

    # ── GGUF vision model (llama.cpp) ─────────────────────────────
    if str(target).lower().endswith(".gguf"):
        if not llama_backend.LLAMA_CPP_AVAILABLE:
            if llama_backend.LLAMA_SERVER_EXE_PATH:
                if not mmproj_path:
                    mmproj_path = mr.GGUF_VLM_MMPROJ_MAP.get(target)
                if not mmproj_path:
                    raise RuntimeError(
                        f"No mmproj (vision projector) file is registered for "
                        f"'{target}'. Select one from the mmproj dropdown in the "
                        f"sidebar, or click '🔍 Scan' on the GGUF model folder so "
                        f"it can be paired with a matching mmproj .gguf file."
                    )
                print(f"[VLM] llama-cpp-python not available — routing GGUF vision "
                      f"through external llama-server …")
                base_url = llama_backend.get_or_start_llama_server(target, mmproj_path=mmproj_path)
                _vlm_model = llama_backend.LlamaServerVLMModel(
                    base_url=base_url,
                    model_path=target,
                    timeout=mr.get_saved_llm_server_timeout(),
                )
                _vlm_processor = None
                _vlm_model_id = target
                return _vlm_model, _vlm_processor
            raise RuntimeError(
                "llama-cpp-python is not installed — GGUF vision models "
                "unavailable. Run SETUP.bat, or install it manually."
            )
        if not mmproj_path:
            mmproj_path = mr.GGUF_VLM_MMPROJ_MAP.get(target)
        if not mmproj_path:
            raise RuntimeError(
                f"No mmproj (vision projector) file is registered for "
                f"'{target}'. Select one from the mmproj dropdown in the "
                f"sidebar, or click '🔍 Scan' on the GGUF model folder so "
                f"it can be paired with a matching mmproj .gguf file."
            )
        _vlm_model = llama_backend.LlamaCppVLMModel(
            model_path=target,
            mmproj_path=mmproj_path,
            n_ctx=mr.get_saved_context_window(),
            n_gpu_layers=-1 if llama_backend.LLAMA_CPP_GPU_AVAILABLE else 0,
        )
        _vlm_processor = None
        _vlm_model_id = target
        return _vlm_model, _vlm_processor

    # ── Local HuggingFace VLM ─────────────────────────────────────
    print(f"[VLM] Loading '{target}' on {DEVICE.upper()} …")
    from transformers import AutoProcessor

    if target in mr.QWEN_VL_IDS:
        from transformers import Qwen2_5_VLForConditionalGeneration

        _vlm_processor = AutoProcessor.from_pretrained(
            target,
            trust_remote_code=True,
            min_pixels=256 * 28 * 28,
            max_pixels=1280 * 28 * 28,
        )

        _vlm_model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            target,
            torch_dtype=TORCH_DTYPE,
            device_map=DEVICE,
            trust_remote_code=True,
        )

        _vlm_model._arch = "qwen_vl"

    elif target in mr.SMOL_VLM_IDS:
        try:
            from transformers import AutoModelForImageTextToText
            ModelClass = AutoModelForImageTextToText
            print("[VLM] Using AutoModelForImageTextToText")
        except ImportError:
            try:
                from transformers import AutoModelForVision2Seq
                ModelClass = AutoModelForVision2Seq
                print("[VLM] Using AutoModelForVision2Seq")
            except ImportError:
                from transformers import AutoModel
                ModelClass = AutoModel
                print("[VLM] Falling back to AutoModel")

        _vlm_processor = AutoProcessor.from_pretrained(
            target,
            trust_remote_code=True,
        )

        _vlm_model = ModelClass.from_pretrained(
            target,
            torch_dtype=TORCH_DTYPE,
            device_map=DEVICE,
            trust_remote_code=True,
        )

        _vlm_model._arch = "smolvlm"

    else:
        raise ValueError(f"Unknown VLM: {target}")

    _vlm_model_id = target

    return _vlm_model, _vlm_processor


def vlm_answer(question: str, images: list, context: str = "", model_id: Optional[str] = None, mmproj_path: Optional[str] = None, lang_key: str = "kh") -> str:
    try:
        model, processor = get_vlm(model_id, mmproj_path=mmproj_path)
        # GGUF vision model (in-process llama-cpp-python or external llama-server) — self-contained answer() method.
        if isinstance(model, (llama_backend.LlamaCppVLMModel, llama_backend.LlamaServerVLMModel)):
            return model.answer(question, images, context=context, max_tokens=mr.get_saved_max_new_tokens())
        # HF Inference API VLM — also self-contained answer().
        if isinstance(model, InferenceApiVLMModel):
            return model.answer(question, images, context=context, max_tokens=mr.get_saved_max_new_tokens())
        arch = getattr(model, "_arch", "smolvlm")
        lang_instruction = "Answer in Khmer.\n\n" if lang_key == "kh" else ""
        system_prompt = lang_instruction + "You are a helpful assistant. Answer based on images and context."
        user_text = question + (f"\n\nContext:\n{context}" if context else "")
        if arch == "qwen_vl":
            from qwen_vl_utils import process_vision_info
            content = [{"type": "image", "image": img} for img in images]
            content.append({"type": "text", "text": user_text})
            messages = [{"role": "system", "content": system_prompt},
                        {"role": "user",   "content": content}]
            text_in = processor.apply_chat_template(messages, tokenize=False,
                                                    add_generation_prompt=True)
            img_in, _ = process_vision_info(messages)
            inputs = processor(text=[text_in], images=img_in,
                               padding=True, return_tensors="pt").to(DEVICE)
        else:
            content = [{"type": "image"} for _ in images]
            content.append({"type": "text", "text": user_text})
            messages = [{"role": "system", "content": system_prompt},
                        {"role": "user",   "content": content}]
            text_in = processor.apply_chat_template(messages, add_generation_prompt=True)
            inputs  = processor(text=text_in, images=images or None, return_tensors="pt").to(DEVICE)
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=mr.get_saved_max_new_tokens())
        trimmed = out[0][inputs["input_ids"].shape[-1]:]
        return processor.decode(trimmed, skip_special_tokens=True)
    except Exception as e:
        import traceback
        return f"❌ Error during VLM generation: {str(e)}\n\n{traceback.format_exc()}"


def get_stt_pipeline(model_id: Optional[str] = None):
    global _stt_pipeline, _stt_model_id
    target = model_id or mr.DEFAULT_STT_MODEL

    if _stt_pipeline is not None and target == _stt_model_id:
        return _stt_pipeline

    with _stt_lock:
        if _stt_pipeline is not None and target == _stt_model_id:
            return _stt_pipeline

        if _stt_pipeline is not None:
            print(f"[STT] Unloading previous STT model '{_stt_model_id}' before loading '{target}' …")
            _release_model(_stt_pipeline)
            _stt_pipeline = None

        # ── HF Inference API ──────────────────────────────────────
        if target == mr.HF_INFERENCE_API_SENTINEL:
            hf_model_id = mr.get_saved_hf_model_id()
            if not hf_model_id:
                raise ValueError(
                    "Hugging Face Inference API selected for Speech, but no "
                    "model ID is configured."
                )
            _stt_pipeline = InferenceApiSTTModel(model_id=hf_model_id)
            _stt_model_id = target
            return _stt_pipeline

        # ── whisper.cpp server ────────────────────────────────────
        suffix = str(target).lower()
        if suffix.endswith(".ggml") or suffix.endswith(".bin"):
            base_url = whisper_cpp_backend.get_or_start_whisper_server(target)
            _stt_pipeline = whisper_cpp_backend.WhisperServerModel(
                base_url=base_url, model_path=target,
            )
            _stt_model_id = target
            return _stt_pipeline

        # ── Local HuggingFace Whisper pipeline ────────────────────
        print(f"[STT] Loading '{target}' on {DEVICE.upper()} …")
        from transformers import pipeline as hf_pipeline

        if DEVICE == "cuda":
            device_arg = 0
        elif DEVICE == "mps":
            device_arg = "mps"
        else:
            device_arg = -1

        _stt_pipeline = hf_pipeline(
            "automatic-speech-recognition",
            model=target,
            torch_dtype=TORCH_DTYPE,
            device=device_arg,
            chunk_length_s=30,
            stride_length_s=5,
        )
        if hasattr(_stt_pipeline, "model") and hasattr(_stt_pipeline.model, "generation_config"):
            gen_cfg = _stt_pipeline.model.generation_config
            gen_cfg.forced_decoder_ids = None

            # Some community Whisper fine-tunes (e.g. the Khmer-tuned
            # checkpoints in STT_OPTIONS) ship a generation_config.json
            # predating transformers' current language-forcing mechanism —
            # it's missing lang_to_id/task_to_id, which makes
            # generate(language=...) raise "generation config is outdated"
            # the moment a specific language (not auto-detect) is picked.
            # Patch the missing multilingual mapping in from the matching
            # stock openai/whisper checkpoint of the same size — same
            # tokenizer/architecture, so the mapping is valid — instead of
            # only discovering this the first time someone picks a language.
            if getattr(gen_cfg, "lang_to_id", None) is None:
                try:
                    from transformers import GenerationConfig
                    size_hint = next(
                        (s for s in ("large-v3", "large-v2", "large", "medium", "small", "base", "tiny")
                         if s in target.lower()),
                        "small",
                    )
                    base_id  = f"openai/whisper-{size_hint}"
                    base_cfg = GenerationConfig.from_pretrained(base_id)
                    for attr in ("lang_to_id", "task_to_id", "is_multilingual"):
                        if hasattr(base_cfg, attr):
                            setattr(gen_cfg, attr, getattr(base_cfg, attr))
                    gen_cfg.forced_decoder_ids = None
                    print(f"[STT] '{target}' had an outdated generation_config — "
                          f"patched language mapping from '{base_id}'.")
                except Exception as e:
                    print(f"[STT] Could not patch outdated generation_config for '{target}': {e}")
        _stt_model_id = target
        return _stt_pipeline


def transcribe_audio(audio_path: Optional[str], language: Optional[str] = None,
                     model_id: Optional[str] = None) -> str:
    if not audio_path:
        return ""
    try:
        asr = get_stt_pipeline(model_id)

        # InferenceApiSTTModel and WhisperServerModel have their own
        # transcribe() method that handles the HTTP request — no audio
        # array decoding needed.
        if hasattr(asr, "transcribe") and callable(asr.transcribe):
            return asr.transcribe(audio_path, language=language)

        gen_kwargs = {}
        if language and language != "auto":
            gen_kwargs["language"] = language
            gen_kwargs["task"] = "transcribe"

        # Decode the audio file ourselves via soundfile/librosa (both already
        # in requirements.txt) instead of handing transformers a raw filepath,
        # which requires ffmpeg to be separately installed and on PATH.
        import numpy as np
        target_sr = getattr(getattr(asr, "feature_extractor", None), "sampling_rate", 16000)

        try:
            import soundfile as sf
            audio_array, src_sr = sf.read(audio_path, dtype="float32", always_2d=False)
        except Exception:
            import librosa
            audio_array, src_sr = librosa.load(audio_path, sr=None, mono=False)

        audio_array = np.asarray(audio_array, dtype="float32")
        if audio_array.ndim == 2:
            # Collapse multi-channel audio to mono (channel axis is whichever is smaller)
            channel_axis = 0 if audio_array.shape[0] < audio_array.shape[1] else 1
            audio_array = audio_array.mean(axis=channel_axis).astype("float32")

        if src_sr != target_sr:
            import librosa
            audio_array = librosa.resample(audio_array, orig_sr=src_sr, target_sr=target_sr)

        try:
            result = asr({"array": audio_array, "sampling_rate": target_sr}, generate_kwargs=gen_kwargs)
        except ValueError as e:
            # Belt-and-braces: if the generation_config patch in
            # get_stt_pipeline() didn't apply (e.g. a different checkpoint
            # hits the same issue in the future), don't crash the whole
            # transcription just because a *specific* language was
            # requested — retry once with auto language detection instead.
            if gen_kwargs and "generation config is outdated" in str(e):
                print(f"[STT] Forced language failed ({e}); retrying with auto-detect …")
                result = asr({"array": audio_array, "sampling_rate": target_sr})
            else:
                raise
        text = result.get("text", "") if isinstance(result, dict) else str(result)
        return text.strip()
    except Exception as e:
        import traceback
        return f"❌ {e}\n\n{traceback.format_exc()}"


# ──────────────────────────────────────────────────────────────────
# HF Inference API model proxies — thin wrappers that call
# huggingface_hub.InferenceClient for model types that don't have a
# smolagents built-in equivalent (InferenceClientModel only covers
# text-generation).  Each shares the HF token / model ID configured
# in the shared provider settings below.
# ──────────────────────────────────────────────────────────────────

class InferenceApiVLMModel:
    """Vision‑language model via HF Inference API — sends image + text
    to the remote endpoint instead of loading weights locally."""

    def __init__(self, model_id: str):
        self.model_id = model_id
        self._client = None

    def _get_client(self):
        if self._client is None:
            from huggingface_hub import InferenceClient
            token = mr.get_saved_hf_token() or None
            self._client = InferenceClient(token=token)
        return self._client

    def answer(self, question: str, images: list, context: str = "",
               max_tokens: int = 512) -> str:
        client = self._get_client()
        user_text = question + (f"\n\nContext:\n{context}" if context else "")
        messages = [{"role": "user", "content": user_text}]
        try:
            resp = client.chat_completion(
                messages=messages,
                model=self.model_id,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content
        except Exception as e:
            # Some VLM models on HF IAPI need images passed differently
            # — try again with image content.
            if images:
                img_b64 = _image_to_base64(images[0])
                content = [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                    {"type": "text", "text": user_text},
                ]
                messages = [{"role": "user", "content": content}]
                resp = client.chat_completion(
                    messages=messages,
                    model=self.model_id,
                    max_tokens=max_tokens,
                )
                return resp.choices[0].message.content
            raise


class InferenceApiSTTModel:
    """Speech‑to‑text via HF Inference API — posts audio to the remote
    endpoint instead of loading Whisper locally."""

    def __init__(self, model_id: str):
        self.model_id = model_id
        self._client = None

    def _get_client(self):
        if self._client is None:
            from huggingface_hub import InferenceClient
            token = mr.get_saved_hf_token() or None
            self._client = InferenceClient(token=token)
        return self._client

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> str:
        client = self._get_client()
        with open(audio_path, "rb") as f:
            data = f.read()
        result = client.automatic_speech_recognition(
            data,
            model=self.model_id,
        )
        return (result.get("text", "") if isinstance(result, dict)
                else str(result))


class InferenceApiEmbeddingModel:
    """Embedding model via HF Inference API — calls the feature-extraction
    endpoint instead of loading SentenceTransformer locally."""

    def __init__(self, model_id: str):
        self.model_id = model_id
        self._client = None

    def _get_client(self):
        if self._client is None:
            from huggingface_hub import InferenceClient
            token = mr.get_saved_hf_token() or None
            self._client = InferenceClient(token=token)
        return self._client

    def encode(self, texts: list, normalize: bool = True) -> list:
        client = self._get_client()
        result = client.feature_extraction(texts, model=self.model_id)
        # Result may be a list of lists or a numpy array
        import numpy as np
        arr = np.asarray(result, dtype=np.float32)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        if normalize:
            norms = np.linalg.norm(arr, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1.0, norms)
            arr = arr / norms
        return arr.tolist()


class EmbeddingServerModel:
    """Embedding model via llama.cpp server's /v1/embeddings endpoint
    (OpenAI-compatible).  Spawns/reuses the same llama-server process
    managed by llama_backend.get_or_start_llama_server()."""

    def __init__(self, model_path: str, base_url: str):
        self.model_id = model_path
        self.model_path = model_path
        self.base_url = base_url.rstrip("/")

    def encode(self, texts: list, normalize: bool = True) -> list:
        import requests
        import numpy as np

        # For a single string, wrap it
        if isinstance(texts, str):
            texts = [texts]

        payload = {
            "input": texts,
            "model": self.model_path,
        }

        resp = requests.post(
            f"{self.base_url}/v1/embeddings",
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()

        # Extract embeddings in order of the input indices
        embeddings = [d["embedding"] for d in sorted(data["data"], key=lambda x: x["index"])]

        arr = np.asarray(embeddings, dtype=np.float32)
        if normalize:
            norms = np.linalg.norm(arr, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1.0, norms)
            arr = arr / norms
        return arr.tolist()


def _image_to_base64(img) -> str:
    """Convert a PIL image to a base64-encoded JPEG string."""
    import base64
    from io import BytesIO
    buf = BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


# ──────────────────────────────────────────────────────────────────
# Explicit "force unload / offload from VRAM" actions — wired to an
# "Unload from VRAM" button on each relevant tab. These free memory
# immediately via _release_model() without loading any replacement,
# unlike get_llm()/get_vlm()/get_stt_pipeline() which only release the
# *previous* model right before loading a new one.
# ──────────────────────────────────────────────────────────────────
def unload_llm_fn(lang_key: str = "kh") -> str:
    global _llm, _llm_model_id
    l = LANGUAGES.get(lang_key, LANGUAGES["kh"])
    if _llm is None:
        return l["btn_unload_none"]
    mid = _llm_model_id
    _release_model(_llm)
    _llm = None
    return l["msg_unloaded"].format(model=mid)


def unload_vlm_fn(lang_key: str = "kh") -> str:
    global _vlm_model, _vlm_processor, _vlm_model_id
    l = LANGUAGES.get(lang_key, LANGUAGES["kh"])
    if _vlm_model is None:
        return l["btn_unload_none"]
    mid = _vlm_model_id
    _release_model(_vlm_model)
    _vlm_model = None
    _vlm_processor = None
    _vlm_model_id = None
    return l["msg_unloaded"].format(model=mid)


def unload_stt_fn(lang_key: str = "kh") -> str:
    global _stt_pipeline, _stt_model_id
    l = LANGUAGES.get(lang_key, LANGUAGES["kh"])
    if _stt_pipeline is None:
        return l["btn_unload_none"]
    mid = _stt_model_id
    _release_model(_stt_pipeline)
    _stt_pipeline = None
    _stt_model_id = None
    return l["msg_unloaded"].format(model=mid)


def force_reload_llm(target_model_id: str, n_ctx: Optional[int] = None):
    """Used by the tab-level 'Load' buttons and the global '🧠 Context
    Window' control: fully release whatever LLM is currently loaded
    (regardless of id) and load `target_model_id` fresh — optionally with
    a specific context window (GGUF backend only; ignored for HF models)."""
    global _llm
    _release_model(_llm)
    _llm = None
    return get_llm(target_model_id, n_ctx=n_ctx)


def force_reload_vlm(target_model_id: str, mmproj_path: Optional[str] = None):
    global _vlm_model, _vlm_processor
    _release_model(_vlm_model)
    _vlm_model = _vlm_processor = None
    return get_vlm(target_model_id, mmproj_path=mmproj_path)


def force_reload_stt(target_model_id: str):
    global _stt_pipeline, _stt_model_id
    _release_model(_stt_pipeline)
    _stt_pipeline = None
    _stt_model_id = None
    return get_stt_pipeline(target_model_id)
