"""
ui.py — Builds the Gradio Blocks UI and wires every event handler.

Layout convention used on every tab that has settings: the primary input
control (message box, file upload, audio recorder) sits at the top of the
main (left) column, the chat/results area follows inside a `gr.Accordion`
that starts CLOSED and pops open automatically the first time there's
something to show — a reply came back, an upload finished, etc. Everything
secondary (model pickers, load/unload buttons, status messages) lives in a
narrow sidebar column to the right of the main column, instead of a
collapsed "⚙️ Settings" accordion stacked underneath the chat like before.

Tabs without a settings equivalent (Knowledge Base, About) keep their
original single-column layout.

All handlers are defined and wired at the top level of build_ui() (never
inside a gr.render() block) — see the "Gradio 6 breaks event handler
rebinding on render cycles" learning: defining .click()/.submit() inside a
@gr.render() causes all buttons/dropdowns to silently stop working after
the first language switch.

INPUT-BOX CLEARING (stash-then-clear pattern)
----------------------------------------------
Every chat/analysis tab (General, RAG, Vision, Data Analysis) clears its
message textbox via a two-step chained event instead of a single handler
that both answers the question AND clears the box:

    msg.submit(stash_fn, [msg], [msg, pending_state], queue=False).then(
        do_chat_fn, [pending_state, ...], [...]
    )

Why: the actual chat/agent call can take anywhere from a few seconds to
several minutes (agentic tabs with a slow local GGUF model hitting
max_steps can run for minutes — see general_agent.py/rag_agent.py module
docstrings). If that single combined call is interrupted by a dropped
connection, a reverse-proxy/browser timeout, or any server-side exception
that occurs outside the handler's own try/except, the textbox-clearing
output update never reaches the browser — even though chat.py's handlers
already return "" unconditionally in every normal case. The result is a
textbox that appears "stuck" with the old message after a failure,
especially on the longest-running tab (General Chat's agentic mode).

The fix: split "clear the input" into its own lightweight step that runs
FIRST, synchronously, with queue=False (so it fires immediately and isn't
stuck behind the slow call in the queue), and STASH the just-submitted
message into a gr.State first — never re-read the textbox's own value in
the second step, since by then the textbox has already been cleared
client-side and would hand the second function an empty string. This
guarantees the box empties the instant the message is sent, independent
of whether the subsequent chat/agent call succeeds, errors, hits
max_steps, or the connection drops entirely.
"""

import gradio as gr

import branding
import chat
import data_analysis
import deep_research_agent
import general_agent
import hardware
import knowledge_base as kb
import llama_backend
import model_registry as mr
import models
import whisper_cpp_backend
import rag_agent
from hardware import DEVICE
from i18n import LANGUAGES

APP_VERSION = branding.APP_VERSION

CSS = """
.status-bar   { font-size:0.82rem; color:#888; padding:4px 8px; }
.header-wrap  { display:flex; align-items:baseline; gap:12px; margin-bottom:6px; }
.header-title { font-size:1.6rem; font-weight:700; }
.header-sub   { font-size:0.9rem; color:#aaa; }
.dev-logo     { width:88px !important; height:88px !important; min-width:88px !important;
                max-width:88px !important; aspect-ratio:1/1; border-radius:50% !important;
                object-fit:cover !important; object-position:center; display:block;
                box-shadow:0 0 10px rgba(120,80,255,0.6); flex-shrink:0; margin-right:4px; }
.beta-badge   { display:inline-block; font-size:0.68rem; font-weight:700; letter-spacing:0.5px;
                color:#1a1a1a; background:#ffcc66; border-radius:999px; padding:2px 9px;
                margin-left:6px; vertical-align:middle; }
.tab-sidebar  { border-right:1px solid #444; padding-right:16px; margin-right:4px; }
.sidebar-hd   { margin-top:0 !important; opacity:0.85; }
.gpu-warning  { background:#3a2e0f; border:1px solid #a87c1f; border-radius:8px;
                padding:10px 14px; margin-bottom:10px; font-size:0.88rem; line-height:1.5; }
"""


def _gpu_warning_html(lang_key: str) -> str:
    """Build the (possibly empty) GPU-incompatibility warning banner HTML.

    Returns "" (nothing rendered) when the GPU is fine or there's no GPU
    at all — see hardware._detect_gpu_kernel_incompatibility(). Only
    non-empty when a CUDA GPU was detected but this PyTorch build has no
    compiled kernels for it (e.g. an old Pascal-class card like an MX230
    on a recent PyTorch release) — the exact case where the app silently
    falls back to CPU and a non-technical user would otherwise have no
    idea why, since torch.cuda.is_available() alone can't tell them.
    """
    info = hardware.get_gpu_incompatibility_info()
    if not info:
        return ""
    l = LANGUAGES.get(lang_key, LANGUAGES["kh"])
    msg = l["gpu_incompat_warning"].format(
        gpu=info["gpu_name"], cc=info["compute_capability"], archs=info["supported_archs"]
    )
    return f'<div class="gpu-warning">{msg}</div>'


def build_ui():
    # Start with Khmer as default
    L = LANGUAGES["kh"]

    with gr.Blocks(title=f"🤖 {branding.APP_NAME_EN} — LocalAiLab") as demo:
        lang_state = gr.State("kh")

        # ── Header ────────────────────────────────────────────────
        with gr.Row():
            with gr.Column(scale=8):
                with gr.Row():
                    if branding.DEVELOPER_LOGO_B64:
                        with gr.Column(scale=0, min_width=100):
                            gr.HTML(
                                f'<img src="data:image/jpeg;base64,{branding.DEVELOPER_LOGO_B64}" '
                                f'class="dev-logo" alt="{branding.DEVELOPER_NAME} logo" />'
                            )
                    with gr.Column():
                        header_title = gr.HTML(
                            f'<div class="header-wrap"><span class="header-title">{L["title"]}</span>'
                            f'<span class="beta-badge">BETA</span></div>'
                        )
                        header_sub = gr.HTML(
                            f'<div class="header-wrap"><span class="header-sub">'
                            f'{L["subtitle"].format(device=DEVICE.upper(), version=APP_VERSION)}</span></div>'
                        )
            with gr.Column(scale=2, variant="panel"):
                lang_dropdown = gr.Dropdown(
                    choices=["Khmer", "English"], value="Khmer",
                    label="🌐 Language", scale=1
                )

        # ── GPU-incompatibility warning banner (hidden when there's ──
        # nothing to warn about — see hardware.get_gpu_incompatibility_
        # info()). Built once at UI-build time from whatever DEVICE was
        # already resolved to at app-import time; updated on a language
        # switch via switch_lang() below so it re-renders in the newly
        # selected language instead of staying stuck in Khmer/English.
        gpu_warning_html = gr.HTML(value=_gpu_warning_html("kh"))

        with gr.Accordion(L["accordion_model_settings"], open=False) as acc_model_settings:
            # ── Provider / Backend ────────────────────────────────
            provider_section_md = gr.Markdown(f"### {L['label_provider_section']}")
            with gr.Row():
                hf_token_tb = gr.Textbox(
                    value=mr.get_saved_hf_token(),
                    placeholder="hf_... or your HF API token",
                    label="🤗 HF API Token", type="password", scale=4,
                )
                hf_model_id_tb = gr.Textbox(
                    value=mr.get_saved_hf_model_id(),
                    placeholder="e.g. Qwen/Qwen3.6-35B-A3B",
                    label="🤗 HF Model ID", scale=4,
                )
                hf_provider_tb = gr.Textbox(
                    value=mr.get_saved_hf_provider(),
                    placeholder="optional — leave blank for auto",
                    label="🤗 HF Provider (optional)", scale=3,
                )
            hf_api_status = gr.Textbox(show_label=False, interactive=False, visible=False)
            with gr.Row():
                litellm_model_id_tb = gr.Textbox(
                    value=mr.get_saved_litellm_model_id(),
                    placeholder="e.g. anthropic/claude-4-sonnet-20250514 or gpt-4o",
                    label="🔗 LiteLLM Model ID", scale=4,
                )
                litellm_api_key_tb = gr.Textbox(
                    value=mr.get_saved_litellm_api_key(),
                    placeholder="sk-... or your API key",
                    label="🔗 LiteLLM API Key", type="password", scale=4,
                )
                litellm_api_base_tb = gr.Textbox(
                    value=mr.get_saved_litellm_api_base(),
                    placeholder="optional — leave blank for default",
                    label="🔗 LiteLLM API Base URL", scale=3,
                )
            litellm_status = gr.Textbox(show_label=False, interactive=False, visible=False)
            with gr.Row():
                llama_server_exe_tb = gr.Textbox(
                    value=llama_backend.LLAMA_SERVER_EXE_PATH,
                    placeholder=r"e.g. D:\llama.cpp\llama-server.exe",
                    label="🖥️ llama-server.exe Path", scale=5,
                )
                llama_server_args_tb = gr.Textbox(
                    value=llama_backend.LLAMA_SERVER_EXTRA_ARGS,
                    placeholder="optional extra flags",
                    label="Extra llama-server Args", scale=3,
                )
                llama_server_timeout_dd = gr.Dropdown(
                    choices=list(mr.LLAMA_SERVER_TIMEOUT_OPTIONS.keys()),
                    value=mr.get_saved_llm_server_timeout_label(),
                    label="⏱️ llama-server Timeout", scale=3,
                )
            llama_server_status = gr.Textbox(show_label=False, interactive=False, visible=False)
            with gr.Accordion(L["accordion_details"], open=False) as acc_llama_server_detail:
                llama_server_detail_md = gr.Markdown(
                    "The default backend (**llama-cpp-python, in-process**) loads a "
                    "`.gguf` model directly inside this app's own Python process — "
                    "no extra setup needed beyond what SETUP.bat already installs.\n\n"
                    "**llama-server (external process)** instead launches a real "
                    "`llama-server` executable as a separate process and talks to it over "
                    "its OpenAI-compatible HTTP API.\n\n"
                    "**⏱️ llama-server Request Timeout**: how long (in seconds) this "
                    "app will wait for a single generation to finish before giving "
                    "up. The default (300s) is enough for most models, but a large "
                    "or CPU-bound model can genuinely need more time than that."
                )
            with gr.Row():
                whisper_server_exe_tb = gr.Textbox(
                    value=whisper_cpp_backend.WHISPER_CPP_SERVER_EXE_PATH,
                    placeholder=r"e.g. D:\whisper.cpp\whisper-server.exe",
                    label="🖥️ whisper.cpp Server Path", scale=5,
                )
                whisper_server_args_tb = gr.Textbox(
                    value=whisper_cpp_backend.WHISPER_CPP_SERVER_EXTRA_ARGS,
                    placeholder="optional extra flags",
                    label="Extra whisper-server Args", scale=3,
                )
            whisper_server_status = gr.Textbox(show_label=False, interactive=False, visible=False)
            with gr.Row():
                gguf_dir_tb = gr.Textbox(
                    value=llama_backend.LLAMA_CPP_MODEL_DIR,
                    placeholder=L["gguf_dir_placeholder"],
                    label=L["label_gguf_dir"], scale=8,
                )
                scan_gguf_btn = gr.Button(L["btn_scan_gguf"], scale=2)
            gguf_scan_status = gr.Textbox(show_label=False, interactive=False, visible=False)

        # ── Global action: free all models (visible on every tab) ──
        with gr.Row():
            free_all_btn = gr.Button("💥 Free All VRAM", variant="stop", size="sm")
            free_all_status = gr.Textbox(show_label=False, interactive=False, visible=False)

        # ── Tabs ──────────────────────────────────────────────────
        with gr.Tabs():

            # ── Tab 1: General Chat ───────────────────────────────
            with gr.Tab(L["tab_general"]) as tab_gen:
                with gr.Row():
                    with gr.Column(scale=3, min_width=260, elem_classes=["tab-sidebar"]):
                        gen_settings_header = gr.Markdown(f"### {L['accordion_settings']}", elem_classes=["sidebar-hd"])
                        gen_desc = gr.Markdown(L["tab_general_desc"])
                        provider_dd_gen = gr.Dropdown(
                            choices=list(mr.LLM_PROVIDER_OPTIONS.keys()),
                            value=mr.get_provider_label(mr.LLM_PROVIDER_OPTIONS, mr.get_saved_provider("gen")),
                            label=L.get("label_provider", "Provider"),
                        )
                        model_dd_gen = gr.Dropdown(
                            choices=list(mr.MODEL_OPTIONS.keys()),
                            value=mr.DEFAULT_LLM_LABEL,
                            label="Model",
                        )
                        with gr.Row():
                            reload_gen = gr.Button(L["btn_load"], size="sm", scale=1)
                            unload_gen_btn = gr.Button(L["btn_unload"], size="sm", scale=1)
                        reload_gen_out = gr.Textbox(show_label=False, interactive=False, visible=False)
                        # ── Generation Settings (shared) ────────
                        gr.Markdown(f"### {L['label_generation_section']}")
                        ctx_window_dd = gr.Dropdown(
                            choices=list(mr.CONTEXT_WINDOW_OPTIONS.keys()),
                            value=mr.get_saved_context_window_label(),
                            label=L["label_context_window"],
                            info=L["info_context_window"],
                        )
                        max_tokens_dd = gr.Dropdown(
                            choices=list(mr.MAX_NEW_TOKENS_OPTIONS.keys()),
                            value=mr.get_saved_max_new_tokens_label(),
                            label="🧮 Max New Tokens",
                            info="Shared between reasoning and answer",
                        )
                        reasoning_chk = gr.Checkbox(
                            label="🧠 Enable Reasoning",
                            value=mr.get_saved_reasoning_enabled(),
                            info="Off = '/no_think' prepended (Qwen3-family only)",
                        )
                        ctx_window_status = gr.Textbox(show_label=False, interactive=False, visible=False)
                        max_tokens_status = gr.Textbox(show_label=False, interactive=False, visible=False)
                        with gr.Accordion(L["accordion_details"], open=False) as acc_ctx_detail:
                            ctx_window_detail_md = gr.Markdown(L["info_context_window_detail"])
                        free_vram_btn = gr.Button(L["btn_free_vram"], variant="stop", size="sm")
                        free_vram_out = gr.Textbox(show_label=False, interactive=False, visible=False)
                        # ── Tab-specific settings ───────────────
                        gen_agentic_chk = gr.Checkbox(
                            label=L["label_gen_agentic"], value=False,
                            info=L["info_gen_agentic"],
                        )
                        gen_memory_chk = gr.Checkbox(
                            label=L["label_memory"], value=True,
                            info=L["info_memory"],
                        )
                        with gr.Accordion(L["accordion_details"], open=False) as acc_gen_detail:
                            gen_agentic_detail_md = gr.Markdown(L["info_gen_agentic_detail"])
                            gen_memory_detail_md  = gr.Markdown(L["info_memory_detail"])
                        with gr.Accordion("Advanced Agent Settings", open=False):
                            gen_max_steps = gr.Slider(
                                minimum=1, maximum=30, step=1, value=8,
                                label="Max Steps",
                                info="Agentic mode only. How many steps before giving up. "
                                     "Raise for complex multi-step questions, lower to fail fast.",
                            )
                            gen_execution_timeout = gr.Slider(
                                minimum=30, maximum=600, step=10, value=120,
                                label="Code Execution Timeout (seconds)",
                                info="Agentic mode only. How long a single Python code block "
                                     "can run before being killed. Default in smolagents is 30s.",
                            )
                        pending_gen_msg = gr.State("")
                    with gr.Column(scale=7):
                        with gr.Accordion(L["accordion_chat"], open=False) as acc_gen_chat:
                            bot_gen   = gr.Chatbot(height=440)
                            clear_gen = gr.Button(L["btn_clear"], size="sm")
                        with gr.Row():
                            msg_gen  = gr.Textbox(placeholder=L["placeholder_gen"], show_label=False, scale=8)
                            send_gen = gr.Button(L["btn_send"], variant="primary", scale=1)
                        # Status indicator — hidden until a message is sent,
                        # then shows "thinking" text immediately (before the
                        # potentially slow LLM/agent call even starts) so the
                        # UI never looks frozen. See show_thinking_gen() /
                        # do_chat_general() below.
                        status_gen = gr.Markdown(visible=False)

            # ── Tab 2: Vision Chat ────────────────────────────────
            with gr.Tab(L["tab_vision"]) as tab_vis:
                with gr.Row():
                    with gr.Column(scale=3, min_width=260, elem_classes=["tab-sidebar"]):
                        vis_settings_header = gr.Markdown(f"### {L['accordion_settings']}", elem_classes=["sidebar-hd"])
                        vis_desc = gr.Markdown(L["tab_vision_desc"])
                        provider_dd_vlm = gr.Dropdown(
                            choices=list(mr.VLM_PROVIDER_OPTIONS.keys()),
                            value=mr.get_provider_label(mr.VLM_PROVIDER_OPTIONS, mr.get_saved_provider("vlm")),
                            label=L.get("label_provider", "Provider"),
                        )
                        vlm_dd = gr.Dropdown(
                            choices=list(mr.VLM_OPTIONS.keys()),
                            value=mr.DEFAULT_VLM_LABEL,
                            label="Model",
                        )
                        mmproj_dd_vis = gr.Dropdown(
                            choices=[],
                            value=None,
                            label="mmproj (vision projector)",
                            visible=False,
                        )
                        with gr.Row():
                            load_vlm_btn = gr.Button(L["btn_load"], size="sm", scale=1)
                            unload_vlm_btn = gr.Button(L["btn_unload"], size="sm", scale=1)
                        load_vlm_out = gr.Textbox(show_label=False, interactive=False, visible=False)
                        vis_rag_chk = gr.Checkbox(
                            label=L["label_vis_rag"], value=False,
                            info=L["label_vis_rag_info"],
                        )
                        vis_memory_chk = gr.Checkbox(
                            label=L["label_memory"], value=True,
                            info=L["info_memory"],
                        )
                        with gr.Accordion(L["accordion_details"], open=False) as acc_vis_detail:
                            vis_rag_detail_md    = gr.Markdown(L["label_vis_rag_info_detail"])
                            vis_memory_detail_md = gr.Markdown(L["info_memory_detail"])
                        pending_vis_msg = gr.State("")
                    with gr.Column(scale=7):
                        with gr.Accordion(L["accordion_chat"], open=False) as acc_vis_chat:
                            bot_vis   = gr.Chatbot(height=400)
                            clear_vis = gr.Button(L["btn_clear"], size="sm")
                        with gr.Row():
                            msg_vis    = gr.Textbox(placeholder=L["placeholder_vis"], show_label=False, scale=6)
                            img_upload = gr.Image(type="pil", sources=["upload", "clipboard"], scale=2)
                            send_vis   = gr.Button(L["btn_send"], variant="primary", scale=1)
                        # See status_gen above.
                        status_vis = gr.Markdown(visible=False)

            # ── Tab 3: Speech to Text ─────────────────────────────
            with gr.Tab(L["tab_stt"]) as tab_stt:
                with gr.Row():
                    with gr.Column(scale=3, min_width=260, elem_classes=["tab-sidebar"]):
                        stt_settings_header = gr.Markdown(f"### {L['accordion_settings']}", elem_classes=["sidebar-hd"])
                        stt_desc = gr.Markdown(L["tab_stt_desc"])
                        provider_dd_stt = gr.Dropdown(
                            choices=list(mr.STT_PROVIDER_OPTIONS.keys()),
                            value=mr.get_provider_label(mr.STT_PROVIDER_OPTIONS, mr.get_saved_provider("stt")),
                            label=L.get("label_provider", "Provider"),
                        )
                        stt_dd = gr.Dropdown(
                            choices=list(mr.STT_OPTIONS.keys()),
                            value=mr.DEFAULT_STT_LABEL,
                            label="Model",
                        )
                        with gr.Row():
                            load_stt_btn = gr.Button(L["btn_load"], size="sm", scale=1)
                            unload_stt_btn = gr.Button(L["btn_unload"], size="sm", scale=1)
                        load_stt_out = gr.Textbox(show_label=False, interactive=False, visible=False)
                        stt_lang_dd = gr.Dropdown(
                            choices=[("Auto-detect", "auto"), ("English", "english"), ("Khmer", "khmer"),
                                     ("French", "french"), ("Chinese", "chinese"), ("Japanese", "japanese")],
                            value="auto", label=L["label_stt_lang"],
                        )
                        stt_hint = gr.Markdown(L["stt_khmer_hint"])
                        with gr.Accordion(L["accordion_details"], open=False) as acc_stt_detail:
                            stt_hint_detail_md = gr.Markdown(L["stt_khmer_hint_detail"])
                    with gr.Column(scale=7):
                        with gr.Accordion(f"📝 {L['label_res']}", open=False) as acc_stt_result:
                            stt_output = gr.Textbox(label=L["label_res"], lines=8, interactive=True)
                        stt_audio      = gr.Audio(label=L["stt_audio_label"], sources=["microphone", "upload"], type="filepath")
                        transcribe_btn = gr.Button(L["btn_transcribe"], variant="primary")

            # ── Tab 4: Data Analysis ──────────────────────────────
            with gr.Tab(L["tab_data"]) as tab_data:
                with gr.Row():
                    with gr.Column(scale=3, min_width=260, elem_classes=["tab-sidebar"]):
                        data_settings_header = gr.Markdown(f"### {L['accordion_settings']}", elem_classes=["sidebar-hd"])
                        data_desc = gr.Markdown(L["tab_data_desc"])
                        provider_dd_data = gr.Dropdown(
                            choices=list(mr.LLM_PROVIDER_OPTIONS.keys()),
                            value=mr.get_provider_label(mr.LLM_PROVIDER_OPTIONS, mr.get_saved_provider("data")),
                            label=L.get("label_provider", "Provider"),
                        )
                        model_dd_data = gr.Dropdown(
                            choices=list(mr.MODEL_OPTIONS.keys()),
                            value=mr.DEFAULT_LLM_LABEL,
                            label="Model",
                        )
                        with gr.Row():
                            reload_data_btn = gr.Button(L["btn_load"], size="sm", scale=1)
                            unload_data_btn = gr.Button(L["btn_unload"], size="sm", scale=1)
                        reload_data_out = gr.Textbox(show_label=False, interactive=False, visible=False)
                        data_memory_chk = gr.Checkbox(
                            label=L["label_memory"], value=True,
                            info=L["info_memory"],
                        )
                        analysis_type_data = gr.Radio(
                            choices=[
                                ("exploratory", L["analysis_exploratory"]),
                                ("sales", L["analysis_sales"]),
                                ("customer", L["analysis_customer"]),
                                ("financial", L["analysis_financial"]),
                                ("payroll", L["analysis_payroll"]),
                            ],
                            label=L["label_analysis_type"],
                            value="exploratory",
                        )
                        with gr.Accordion(L["accordion_details"], open=False) as acc_data_detail:
                            data_memory_detail_md = gr.Markdown(L["info_memory_detail"])
                        with gr.Accordion("Advanced Agent Settings", open=False):
                            data_max_steps = gr.Slider(
                                minimum=1, maximum=30, step=1, value=15,
                                label="Max Steps",
                                info="How many agentic steps before giving up. "
                                     "Larger values let the agent do more work (more charts, "
                                     "deeper analysis) but take longer and cost more tokens.",
                            )
                            data_execution_timeout = gr.Slider(
                                minimum=30, maximum=600, step=10, value=120,
                                label="Code Execution Timeout (seconds)",
                                info="How long a single Python code block is allowed to run "
                                     "before being killed. Raise this for large datasets or "
                                     "slow models. Default in smolagents is 30s.",
                            )
                        reset_data_btn = gr.Button(L["btn_reset_agent"], size="sm")
                        reset_data_out = gr.Textbox(show_label=False, interactive=False, visible=False)
                        pending_data_question = gr.State("")
                    with gr.Column(scale=7):
                        with gr.Accordion(L["accordion_chat"], open=False) as acc_data_chat:
                            bot_data   = gr.Chatbot(height=420)
                            clear_data = gr.Button(L["btn_clear"], size="sm")
                        with gr.Accordion(L["accordion_data_results"], open=False) as acc_data_results:
                            data_gallery     = gr.Gallery(label=L["label_charts"], columns=3, height=280)
                            data_report_file = gr.File(label=L["label_report_file"], interactive=False)
                        data_file_up = gr.File(label=L["data_file_label"], file_types=[".csv", ".xlsx", ".xls"], file_count="multiple")
                        with gr.Row():
                            msg_data  = gr.Textbox(placeholder=L["placeholder_data"], show_label=False, scale=8)
                            send_data = gr.Button(L["btn_send"], variant="primary", scale=1)
                        # See status_gen above.
                        status_data = gr.Markdown(visible=False)

            # ── Tab 5: Knowledge Base ─────────────────────────────
            # No "⚙️ Settings" equivalent here — kept as a single column.
            with gr.Tab(L["tab_kb"]) as tab_kb:
                # Index stats (text chunks / visual index) — only relevant
                # here and on the RAG Chat tab (the two places retrieval
                # actually happens), not on every tab. Populated lazily via
                # demo.load() below (see that comment for why it isn't
                # computed inline at build time), and refreshed after any
                # upload/delete/clear action further down.
                kb_status_bar = gr.Textbox(
                    value="…", interactive=False,
                    show_label=False, elem_classes=["status-bar"]
                )
                provider_dd_embed = gr.Dropdown(
                    choices=list(mr.EMBED_PROVIDER_OPTIONS.keys()),
                    value=mr.get_provider_label(mr.EMBED_PROVIDER_OPTIONS, mr.get_saved_provider("embed")),
                    label=L.get("label_provider", "Provider"),
                )
                embed_dd = gr.Dropdown(
                    choices=list(mr.EMBED_OPTIONS.keys()),
                    value=mr.get_default_embed_label(),
                    label="Model",
                )
                with gr.Row():
                    load_embed_btn = gr.Button(L["btn_load"], size="sm", scale=1)
                    unload_embed_btn = gr.Button(L["btn_unload"], size="sm", scale=1)
                load_embed_out = gr.Textbox(show_label=False, interactive=False, visible=False)
                with gr.Accordion(L["accordion_details"], open=False) as acc_embed_detail:
                    embed_detail_md = gr.Markdown(L["info_embed_detail"])
                with gr.Accordion(L["accordion_add"], open=True) as acc_add:
                    file_up    = gr.File(label=L["file_label"], file_types=[".pdf",".txt",".md",".docx"], file_count="multiple")
                    vis_ret_dd = gr.Dropdown(choices=list(mr.VISUAL_RETRIEVER_OPTIONS.keys()), value=list(mr.VISUAL_RETRIEVER_OPTIONS.keys())[0], label=L["label_vis_ret"])
                    with gr.Row():
                        theme_tb    = gr.Textbox(label=L["theme_label"], placeholder=L["theme_placeholder"], scale=1)
                        subtheme_tb = gr.Textbox(label=L["subtheme_label"], placeholder=L["subtheme_placeholder"], scale=1)
                    with gr.Row():
                        up_btn             = gr.Button(L["btn_index"], variant="primary", scale=3)
                        unload_visual_btn  = gr.Button(L["btn_unload"], size="sm", scale=2)
                    up_msg = gr.Textbox(label=L["label_res"], interactive=False, lines=4, visible=False)

                with gr.Accordion(L["label_kb_docs"], open=False) as acc_kb_docs:
                    doc_table = gr.Dataframe(
                        headers=L["doc_table_headers"],
                        datatype=["str","str","str","number","str","str"],
                        value=kb.get_doc_table,
                        interactive=True, wrap=True,
                    )
                    with gr.Row():
                        refresh_btn    = gr.Button(L["btn_refresh"], size="sm", scale=2)
                        delete_sel_btn = gr.Button(L["btn_delete"], variant="stop", size="sm", scale=2)
                        clear_all_btn  = gr.Button(L["btn_clear_all"], variant="stop", size="sm", scale=2)
                    action_msg = gr.Textbox(label="", interactive=False, lines=1, visible=False)
                selected_rows_state = gr.State([])

            # ── Tab 7: RAG Chat (agentic — see rag_agent.py) ──────
            with gr.Tab(L["tab_rag"]) as tab_rag:
                with gr.Row():
                    with gr.Column(scale=3, min_width=260, elem_classes=["tab-sidebar"]):
                        rag_settings_header = gr.Markdown(f"### {L['accordion_settings']}", elem_classes=["sidebar-hd"])
                        rag_desc = gr.Markdown(L["tab_rag_desc"])
                        provider_dd_rag = gr.Dropdown(
                            choices=list(mr.LLM_PROVIDER_OPTIONS.keys()),
                            value=mr.get_provider_label(mr.LLM_PROVIDER_OPTIONS, mr.get_saved_provider("rag")),
                            label=L.get("label_provider", "Provider"),
                        )
                        model_dd_rag = gr.Dropdown(
                            choices=list(mr.MODEL_OPTIONS.keys()),
                            value=mr.DEFAULT_LLM_LABEL,
                            label="Model",
                        )
                        with gr.Row():
                            reload_rag = gr.Button(L["btn_load"], size="sm", scale=1)
                            unload_rag_btn = gr.Button(L["btn_unload"], size="sm", scale=1)
                        reload_rag_out = gr.Textbox(show_label=False, interactive=False, visible=False)
                        rag_status_bar = gr.Textbox(
                            value="…", interactive=False,
                            show_label=False, elem_classes=["status-bar"]
                        )
                        with gr.Row():
                            theme_tb_rag    = gr.Textbox(label=L["theme_label"], placeholder=L["theme_placeholder"], scale=1)
                            subtheme_tb_rag = gr.Textbox(label=L["subtheme_label"], placeholder=L["subtheme_placeholder"], scale=1)
                        rag_agentic_chk = gr.Checkbox(
                            label=L["label_rag_agentic"], value=True,
                            info=L["info_rag_agentic"],
                        )
                        rag_memory_chk = gr.Checkbox(
                            label=L["label_memory"], value=True,
                            info=L["info_memory"],
                        )
                        with gr.Accordion(L["accordion_details"], open=False) as acc_rag_detail:
                            rag_agentic_detail_md = gr.Markdown(L["info_rag_agentic_detail"])
                            rag_memory_detail_md  = gr.Markdown(L["info_memory_detail"])
                        with gr.Accordion("Advanced Agent Settings", open=False):
                            rag_max_steps = gr.Slider(
                                minimum=1, maximum=15, step=1, value=6,
                                label="Max Steps (agentic mode only)",
                            )
                            rag_tool_calling_chk = gr.Checkbox(
                                label="Use native tool calling (ToolCallingAgent)",
                                value=False,
                                info="Uses ToolCallingAgent instead of CodeAgent. "
                                     "Only works with models that support native "
                                     "function-calling (LiteLLM, HF Inference API "
                                     "on capable models). Falls back to CodeAgent "
                                     "if unsupported.",
                            )
                        pending_rag_msg = gr.State("")
                    with gr.Column(scale=7):
                        with gr.Accordion(L["accordion_chat"], open=False) as acc_rag_chat:
                            bot_rag   = gr.Chatbot(height=440)
                            clear_rag = gr.Button(L["btn_clear"], size="sm")
                        with gr.Row():
                            msg_rag  = gr.Textbox(placeholder=L["placeholder_rag"], show_label=False, scale=8)
                            send_rag = gr.Button(L["btn_send"], variant="primary", scale=1)
                        # See status_gen above.
                        status_rag = gr.Markdown(visible=False)

            # ── Tab 8: Deep Research (manager + web-search sub-agent — ──
            # see deep_research_agent.py) ─────────────────────────────
            with gr.Tab(L["tab_deep_research"]) as tab_deep_research:
                with gr.Row():
                    with gr.Column(scale=3, min_width=260, elem_classes=["tab-sidebar"]):
                        dr_settings_header = gr.Markdown(f"### {L['accordion_settings']}", elem_classes=["sidebar-hd"])
                        dr_desc = gr.Markdown(L["tab_deep_research_desc"])
                        provider_dd_dr = gr.Dropdown(
                            choices=list(mr.LLM_PROVIDER_OPTIONS.keys()),
                            value=mr.get_provider_label(mr.LLM_PROVIDER_OPTIONS, mr.get_saved_provider("dr")),
                            label=L.get("label_provider", "Provider"),
                        )
                        model_dd_dr = gr.Dropdown(
                            choices=list(mr.MODEL_OPTIONS.keys()),
                            value=mr.DEFAULT_LLM_LABEL,
                            label="Model",
                        )
                        with gr.Row():
                            reload_dr = gr.Button(L["btn_load"], size="sm", scale=1)
                            unload_dr_btn = gr.Button(L["btn_unload"], size="sm", scale=1)
                        reload_dr_out = gr.Textbox(show_label=False, interactive=False, visible=False)
                        dr_memory_chk = gr.Checkbox(
                            label=L["label_memory"], value=True,
                            info=L["info_memory"],
                        )
                        dr_use_playwright_chk = gr.Checkbox(
                            label="Use Playwright (Headless Browser) Tools", value=False,
                            info="Use Playwright for searching and browsing. Requires Playwright browsers installed.",
                        )
                        dr_headless_chk = gr.Checkbox(
                            label="Run Playwright Headless", value=False,
                            info="If unchecked, Playwright will open a visible browser window (with head).",
                        )
                        with gr.Accordion("Advanced Agent Settings", open=False):
                            dr_manager_max_steps = gr.Slider(
                                minimum=1, maximum=30, step=1, value=12,
                                label="Manager Agent Max Steps"
                            )
                            dr_search_max_steps = gr.Slider(
                                minimum=1, maximum=15, step=1, value=6,
                                label="Search Sub-agent Max Steps"
                            )
                            dr_timeout = gr.Slider(
                                minimum=30, maximum=1200, step=10, value=300,
                                label="Code Execution Timeout (seconds)"
                            )
                        with gr.Accordion(L["accordion_details"], open=False) as acc_dr_detail:
                            dr_memory_detail_md = gr.Markdown(L["info_memory_detail"])
                        reset_dr_btn = gr.Button(L["btn_reset_agent"], size="sm")
                        reset_dr_out = gr.Textbox(show_label=False, interactive=False, visible=False)
                        pending_dr_msg = gr.State("")
                    with gr.Column(scale=7):
                        with gr.Accordion(L["accordion_chat"], open=False) as acc_dr_chat:
                            bot_dr   = gr.Chatbot(height=460)
                            clear_dr = gr.Button(L["btn_clear"], size="sm")
                        with gr.Row():
                            msg_dr  = gr.Textbox(placeholder=L["placeholder_deep_research"], show_label=False, scale=8)
                            send_dr = gr.Button(L["btn_send"], variant="primary", scale=1)
                        # See status_gen above.
                        status_dr = gr.Markdown(visible=False)

            # ── Tab 9: About ──────────────────────────────────────
            with gr.Tab(L["tab_about"]) as tab_about:
                about_md_kh = gr.Markdown(branding.about_content_kh(DEVICE.upper(), APP_VERSION))
                gr.Markdown("---")
                about_md_en = gr.Markdown(branding.about_content_en(DEVICE.upper(), APP_VERSION))

        # ── Event handlers ────────────────────────────────────────

        # GGUF model folder — rescan updates every model dropdown at once,
        # and reveals the scan-result textbox (hidden until a scan runs).
        def do_rescan_gguf(folder_path, lang_key):
            msg, dd1, dd2, dd3, vlm_dd_update = mr.rescan_gguf_models(folder_path, lang_key)
            return gr.update(value=msg, visible=True), dd1, dd2, dd3, vlm_dd_update

        scan_gguf_btn.click(
            do_rescan_gguf,
            [gguf_dir_tb, lang_state],
            [gguf_scan_status, model_dd_gen, model_dd_rag, model_dd_data, vlm_dd],
        )
        gguf_dir_tb.submit(
            do_rescan_gguf,
            [gguf_dir_tb, lang_state],
            [gguf_scan_status, model_dd_gen, model_dd_rag, model_dd_data, vlm_dd],
        )

        # Context Window (n_ctx) — GGUF/llama.cpp only. Persists the choice
        # immediately (models.get_llm()'s fallback logic picks it up on any
        # future load), and if a GGUF model happens to be loaded right now,
        # force-reloads it with the new n_ctx so the change is felt right
        # away instead of silently waiting for the next unrelated reload.
        def do_change_context_window(label):
            n_ctx = mr.CONTEXT_WINDOW_OPTIONS.get(label, mr.DEFAULT_CONTEXT_WINDOW)
            mr.set_context_window(n_ctx)
            # Every agentic CodeAgent wrapper holds its own reference to
            # the shared LLM object — drop all four caches so none of
            # them keep pointing at the model instance we're about to
            # release below (same pattern as reload_gen_fn/reload_rag_fn).
            general_agent.reset_agent()
            rag_agent.reset_agent()
            data_analysis.reset_agent()
            deep_research_agent.reset_agent()
            currently_loaded = models._llm_model_id
            if models._llm is not None and str(currently_loaded).lower().endswith(".gguf"):
                try:
                    models.force_reload_llm(currently_loaded, n_ctx=n_ctx)
                    msg = f"✅ Context window set to {n_ctx} tokens — '{currently_loaded}' reloaded."
                except Exception as e:
                    msg = f"❌ Failed to reload with the new context window: {e}"
            else:
                msg = f"✅ Context window set to {n_ctx} tokens — will apply next time a GGUF model loads."
            return gr.update(value=msg, visible=True)

        ctx_window_dd.change(do_change_context_window, [ctx_window_dd], [ctx_window_status])

        # ── Max New Tokens + Reasoning toggle ─────────────────────────
        def do_change_max_new_tokens(label):
            n = mr.MAX_NEW_TOKENS_OPTIONS.get(label, mr.DEFAULT_MAX_NEW_TOKENS)
            mr.set_max_new_tokens(n)
            # LlamaCppModel / LlamaServerModel both read self.max_new_tokens
            # fresh on every generate() call — mutate it in place on an
            # already-loaded model instead of forcing a full multi-GB
            # reload just for a token-count tweak. TransformersModel may
            # not expose this the same way depending on smolagents
            # version, in which case this just falls through to "applies
            # next load" below, which is still accurate.
            if models._llm is not None and hasattr(models._llm, "max_new_tokens"):
                models._llm.max_new_tokens = n
                msg = f"✅ Max new tokens set to {n} — applied immediately."
            else:
                msg = f"✅ Max new tokens set to {n} — will apply next time a model loads."
            return gr.update(value=msg, visible=True)

        def do_change_reasoning(enabled):
            mr.set_reasoning_enabled(enabled)
            msg = ("✅ Reasoning enabled." if enabled else
                   "✅ Reasoning disabled — '/no_think' will be prepended to every "
                   "prompt from now on (only Qwen3-family models respect this tag; "
                   "other models simply ignore it as harmless extra text).")
            return gr.update(value=msg, visible=True)

        max_tokens_dd.change(do_change_max_new_tokens, [max_tokens_dd], [max_tokens_status])
        reasoning_chk.change(do_change_reasoning, [reasoning_chk], [max_tokens_status])

        # ── llama-server (external process) backend controls ────────
        def _reset_every_agent_cache():
            # Every agentic CodeAgent wrapper holds its own reference to
            # the shared LLM object — drop all four caches so none of
            # them keep pointing at a model instance that's about to be
            # replaced/reloaded under a different backend (mirrors
            # do_change_context_window()'s reset above).
            general_agent.reset_agent()
            rag_agent.reset_agent()
            data_analysis.reset_agent()
            deep_research_agent.reset_agent()

        def do_set_llama_server_path(path):
            llama_backend.set_llama_server_exe_path(path)
            msg = (f"✅ llama-server path saved: '{path}'" if path
                   else "ℹ️ Cleared — the llama-server backend is unavailable until a path is set.")
            return gr.update(value=msg, visible=True)

        def do_set_llama_server_args(args_str):
            llama_backend.set_llama_server_extra_args(args_str)
            return gr.update(value=f"✅ Extra llama-server args saved: '{args_str}'" if args_str
                              else "✅ Extra llama-server args cleared.", visible=True)

        def do_change_llm_backend(label):
            mode = mr.LLM_BACKEND_MODE_OPTIONS.get(label, "inprocess")
            mr.set_llm_backend_mode(mode)
            _reset_every_agent_cache()
            # A backend switch can't be hot-applied to an already-loaded
            # model — always fully release whatever's currently loaded
            # (in-process weights OR a running llama-server subprocess;
            # see models._release_model()'s LlamaServerModel branch) so
            # the NEXT get_llm() call rebuilds cleanly under the newly
            # selected backend instead of silently reusing a stale one.
            currently_loaded = models._llm_model_id
            had_model_loaded = models._llm is not None
            llama_backend.stop_llama_server()
            if had_model_loaded:
                models._release_model(models._llm)
                models._llm = None
            msg = (f"✅ Backend set to '{label}'."
                   + (f" '{currently_loaded}' will reload under the new backend on next use."
                      if had_model_loaded and str(currently_loaded).lower().endswith(".gguf") else ""))
            return gr.update(value=msg, visible=True)

        def do_change_llama_server_timeout(label):
            seconds = mr.LLAMA_SERVER_TIMEOUT_OPTIONS.get(label, mr.DEFAULT_LLAMA_SERVER_TIMEOUT)
            mr.set_llm_server_timeout(seconds)
            # This only affects the Python-side `requests.post(...,
            # timeout=...)` call in LlamaServerModel.generate()
            # (llama_backend.py) — llama-server itself (the actual
            # subprocess doing generation) is completely untouched by this
            # setting. So if a LlamaServerModel is already loaded, mutate
            # its `.timeout` attribute directly in place rather than going
            # through force_reload_llm()/_release_model() — that path would
            # call llama_backend.stop_llama_server() and respawn the whole
            # external process (a multi-GB model reload) just to change one
            # in-Python integer, which is both unnecessary and far slower
            # than the fix it's applying.
            if models._llm is not None and isinstance(models._llm, llama_backend.LlamaServerModel):
                models._llm.timeout = seconds
                msg = f"✅ llama-server request timeout set to {seconds}s — applied immediately (server left running)."
            else:
                msg = f"✅ llama-server request timeout set to {seconds}s — will apply next time a llama-server request is made."
            return gr.update(value=msg, visible=True)

        llama_server_exe_tb.submit(do_set_llama_server_path, [llama_server_exe_tb], [llama_server_status])
        llama_server_args_tb.submit(do_set_llama_server_args, [llama_server_args_tb], [llama_server_status])
        # llm_backend_dd was removed from the sidebar; backend switching
        # is now handled per-tab via the provider dropdown in the accordion.
        llama_server_timeout_dd.change(do_change_llama_server_timeout, [llama_server_timeout_dd], [llama_server_status])

        # ── Hugging Face Inference API settings ────────────────────
        def do_set_hf_token(token):
            mr.set_hf_token(token)
            return gr.update(value=f"✅ HF API token saved.", visible=True)

        def do_set_hf_model_id(model_id):
            mr.set_hf_model_id(model_id)
            return gr.update(value=f"✅ HF model ID saved: '{model_id}'", visible=True)

        def do_set_hf_provider(provider):
            mr.set_hf_provider(provider)
            return gr.update(value=f"✅ HF provider saved: '{provider}'" if provider
                              else "✅ HF provider cleared (will use auto).", visible=True)

        hf_token_tb.submit(do_set_hf_token, [hf_token_tb], [hf_api_status])
        hf_model_id_tb.submit(do_set_hf_model_id, [hf_model_id_tb], [hf_api_status])
        hf_provider_tb.submit(do_set_hf_provider, [hf_provider_tb], [hf_api_status])

        def do_set_litellm_model_id(model_id):
            mr.set_litellm_model_id(model_id)
            return gr.update(value=f"✅ LiteLLM model ID saved: '{model_id}'", visible=True)

        def do_set_litellm_api_key(api_key):
            mr.set_litellm_api_key(api_key)
            return gr.update(value=f"✅ LiteLLM API key saved.", visible=True)

        def do_set_litellm_api_base(api_base):
            mr.set_litellm_api_base(api_base)
            return gr.update(value=f"✅ LiteLLM API base saved: '{api_base}'", visible=True)

        litellm_model_id_tb.submit(do_set_litellm_model_id, [litellm_model_id_tb], [litellm_status])
        litellm_api_key_tb.submit(do_set_litellm_api_key, [litellm_api_key_tb], [litellm_status])
        litellm_api_base_tb.submit(do_set_litellm_api_base, [litellm_api_base_tb], [litellm_status])

        # ── Free All VRAM (unloads every model + resets all agents) ──
        def do_free_vram(lang_key):
            msgs = []
            msgs.append(models.unload_llm_fn(lang_key))
            msgs.append(models.unload_vlm_fn(lang_key))
            msgs.append(models.unload_stt_fn(lang_key))
            msgs.append(models.unload_embed_model_fn(lang_key))
            msgs.append(kb.unload_visual_retriever_fn(lang_key))
            general_agent.reset_agent()
            rag_agent.reset_agent()
            data_analysis.reset_agent()
            deep_research_agent.reset_agent()
            return gr.update(value="\n".join(msgs), visible=True)

        free_vram_btn.click(do_free_vram, [lang_state], [free_vram_out])
        free_all_btn.click(do_free_vram, [lang_state], [free_all_status])

        # General Chat
        def reload_gen_fn(label):
            # Both the general agentic CodeAgent and the data-analysis
            # agent hold their own reference to the shared LLM instance —
            # reset both caches so neither keeps the old model (or its
            # now-stale weights) alive; they rebuild cheaply against the
            # newly loaded one on next use.
            general_agent.reset_agent()
            data_analysis.reset_agent()
            mid = mr.MODEL_OPTIONS.get(label, mr.DEFAULT_LLM_MODEL)
            try:
                models.force_reload_llm(mid)
                return gr.update(value=f"✅ '{mid}' loaded", visible=True)
            except Exception as e:
                return gr.update(value=f"❌ {e}", visible=True)

        def unload_gen_fn(lang_key):
            msg = models.unload_llm_fn(lang_key)
            general_agent.reset_agent()
            data_analysis.reset_agent()
            return gr.update(value=msg, visible=True)

        def stash_gen(user_message):
            # Fires first, synchronously (queue=False) — clears msg_gen
            # immediately and hands the message off to pending_gen_msg for
            # the slow step below, instead of leaving it sitting in the
            # textbox for however long the (possibly multi-minute) agent
            # call takes. See module docstring: "INPUT-BOX CLEARING".
            return "", user_message

        def show_thinking_gen(use_agentic, lang_key):
            l = LANGUAGES.get(lang_key, LANGUAGES["kh"])
            msg = l["think_gen_agentic"] if use_agentic else l["think_gen"]
            return gr.update(value=msg, visible=True)

        def do_chat_general(pending_message, history, model_label, use_agentic,
                            use_memory, lang_key, max_steps, execution_timeout):
            # chat.chat_general() is itself a generator (see chat.py):
            # for the direct path it yields once; for the agentic path it
            # yields once per LIVE agent step (thought/code, tool calls,
            # output — see agent_streaming.py) before the polished final
            # answer. Re-yielding here streams each of those straight into
            # bot_gen as they arrive, instead of the UI sitting frozen
            # behind "🤖 Thinking…" until the whole run finishes. The
            # status line only clears on the LAST yield, once the loop
            # below is actually exhausted.
            last_history = history
            for updated_history, _ in chat.chat_general(
                pending_message, history, model_label, use_agentic, use_memory,
                lang_key=lang_key, max_steps=max_steps,
                execution_timeout=execution_timeout,
            ):
                last_history = updated_history
                yield last_history, gr.update(open=True), gr.update()
            yield last_history, gr.update(open=True), gr.update(visible=False)

        msg_gen.submit(stash_gen, [msg_gen], [msg_gen, pending_gen_msg], queue=False).then(
            show_thinking_gen, [gen_agentic_chk, lang_state], [status_gen], queue=False
        ).then(
            do_chat_general,
            [pending_gen_msg, bot_gen, model_dd_gen, gen_agentic_chk,
             gen_memory_chk, lang_state, gen_max_steps, gen_execution_timeout],
            [bot_gen, acc_gen_chat, status_gen]
        )
        send_gen.click(stash_gen, [msg_gen], [msg_gen, pending_gen_msg], queue=False).then(
            show_thinking_gen, [gen_agentic_chk, lang_state], [status_gen], queue=False
        ).then(
            do_chat_general,
            [pending_gen_msg, bot_gen, model_dd_gen, gen_agentic_chk,
             gen_memory_chk, lang_state, gen_max_steps, gen_execution_timeout],
            [bot_gen, acc_gen_chat, status_gen]
        )

        def clear_gen_fn():
            # Clearing the visible chat should also clear the agentic
            # CodeAgent's own memory (agent.memory.steps) — otherwise a
            # "fresh" conversation would still secretly remember the old
            # one via agent.run(..., reset=False). Dropping the cached
            # agent object is enough: the next build starts with empty
            # memory (standard smolagents behaviour — see
            # agent_memory.py's module docstring for why this app no
            # longer persists memory to disk that would need clearing
            # separately here).
            general_agent.reset_agent()
            return [], "", gr.update(open=False), gr.update(visible=False)

        clear_gen.click(clear_gen_fn, outputs=[bot_gen, msg_gen, acc_gen_chat, status_gen])
        reload_gen.click(reload_gen_fn, [model_dd_gen], [reload_gen_out])
        unload_gen_btn.click(unload_gen_fn, [lang_state], [reload_gen_out])

        # RAG Chat (agentic — see rag_agent.py — or direct, see chat.py)
        def reload_rag_fn(label):
            # The RAG CodeAgent and the data-analysis CodeAgent each hold
            # their own reference to the shared LLM instance — reset both
            # caches so neither keeps the old model (or stale weights)
            # alive; they rebuild cheaply against the newly loaded model.
            rag_agent.reset_agent()
            data_analysis.reset_agent()
            mid = mr.MODEL_OPTIONS.get(label, mr.DEFAULT_LLM_MODEL)
            try:
                models.force_reload_llm(mid)
                return gr.update(value=f"✅ '{mid}' loaded", visible=True)
            except Exception as e:
                return gr.update(value=f"❌ {e}", visible=True)

        def unload_rag_fn(lang_key):
            msg = models.unload_llm_fn(lang_key)
            rag_agent.reset_agent()
            data_analysis.reset_agent()
            return gr.update(value=msg, visible=True)

        def stash_rag(user_message):
            # See stash_gen() above.
            return "", user_message

        def show_thinking_rag(use_agentic, lang_key):
            l = LANGUAGES.get(lang_key, LANGUAGES["kh"])
            msg = l["think_rag_agentic"] if use_agentic else l["think_rag"]
            return gr.update(value=msg, visible=True)

        def do_chat_rag(pending_message, history, model_label, use_agentic, use_memory,
                        theme, subtheme, max_steps, use_tool_calling, lang_key):
            # See do_chat_general()'s matching comment above — chat.chat_rag()
            # is a generator on both paths; the agentic path streams a live
            # bubble per retriever call / model step instead of one frozen
            # "📚 Searching…" line for the whole run.
            last_history = history
            for updated_history, _ in chat.chat_rag(
                pending_message, history, model_label, use_agentic, use_memory,
                theme, subtheme, max_steps, lang_key=lang_key,
                use_tool_calling=use_tool_calling,
            ):
                last_history = updated_history
                yield last_history, gr.update(open=True), gr.update()
            yield last_history, gr.update(open=True), gr.update(visible=False)

        msg_rag.submit(stash_rag, [msg_rag], [msg_rag, pending_rag_msg], queue=False).then(
            show_thinking_rag, [rag_agentic_chk, lang_state], [status_rag], queue=False
        ).then(
            do_chat_rag, [pending_rag_msg, bot_rag, model_dd_rag, rag_agentic_chk, rag_memory_chk, theme_tb_rag, subtheme_tb_rag, rag_max_steps, rag_tool_calling_chk, lang_state],
            [bot_rag, acc_rag_chat, status_rag]
        )
        send_rag.click(stash_rag, [msg_rag], [msg_rag, pending_rag_msg], queue=False).then(
            show_thinking_rag, [rag_agentic_chk, lang_state], [status_rag], queue=False
        ).then(
            do_chat_rag, [pending_rag_msg, bot_rag, model_dd_rag, rag_agentic_chk, rag_memory_chk, theme_tb_rag, subtheme_tb_rag, rag_max_steps, rag_tool_calling_chk, lang_state],
            [bot_rag, acc_rag_chat, status_rag]
        )

        def clear_rag_fn():
            # See clear_gen_fn() above — dropping the cached CodeAgent is
            # enough to guarantee a fresh, empty-memory agent next build.
            rag_agent.reset_agent()
            return [], "", gr.update(open=False), gr.update(visible=False)

        clear_rag.click(clear_rag_fn, outputs=[bot_rag, msg_rag, acc_rag_chat, status_rag])
        reload_rag.click(reload_rag_fn, [model_dd_rag], [reload_rag_out])
        unload_rag_btn.click(unload_rag_fn, [lang_state], [reload_rag_out])

        # Deep Research (manager + web_search_agent — see deep_research_agent.py)
        def reload_dr_fn(label):
            deep_research_agent.reset_agent()
            mid = mr.MODEL_OPTIONS.get(label, mr.DEFAULT_LLM_MODEL)
            try:
                models.force_reload_llm(mid)
                return gr.update(value=f"✅ '{mid}' loaded", visible=True)
            except Exception as e:
                return gr.update(value=f"❌ {e}", visible=True)

        def unload_dr_fn(lang_key):
            msg = models.unload_llm_fn(lang_key)
            deep_research_agent.reset_agent()
            return gr.update(value=msg, visible=True)

        def reset_dr_agent_fn():
            deep_research_agent.reset_agent()
            return gr.update(value="✅ Agent reset — will rebuild on next run.", visible=True)

        def stash_dr(user_message):
            # See stash_gen() above.
            return "", user_message

        def show_thinking_dr(lang_key):
            l = LANGUAGES.get(lang_key, LANGUAGES["kh"])
            return gr.update(value=l["think_dr"], visible=True)

        def do_chat_deep_research(pending_message, history, model_label, use_memory, use_playwright, headless, manager_max_steps, search_max_steps, timeout, lang_key):
            # See do_chat_general()'s matching comment above. This is the
            # tab where live streaming matters most — a full research run
            # (manager planning + several delegated web_search_agent
            # calls) is easily the slowest single call in the app; seeing
            # each delegated sub-question and what it found as it happens
            # is a large improvement over one static "🔬🤖 Researching…"
            # line for however many minutes the run takes.
            last_history = history
            for updated_history, _ in chat.chat_deep_research(
                pending_message, history, model_label, use_memory, use_playwright,
                headless, manager_max_steps, search_max_steps, timeout, lang_key=lang_key
            ):
                last_history = updated_history
                yield last_history, gr.update(open=True), gr.update()
            yield last_history, gr.update(open=True), gr.update(visible=False)

        msg_dr.submit(stash_dr, [msg_dr], [msg_dr, pending_dr_msg], queue=False).then(
            show_thinking_dr, [lang_state], [status_dr], queue=False
        ).then(
            do_chat_deep_research, [pending_dr_msg, bot_dr, model_dd_dr, dr_memory_chk, dr_use_playwright_chk, dr_headless_chk, dr_manager_max_steps, dr_search_max_steps, dr_timeout, lang_state],
            [bot_dr, acc_dr_chat, status_dr]
        )
        send_dr.click(stash_dr, [msg_dr], [msg_dr, pending_dr_msg], queue=False).then(
            show_thinking_dr, [lang_state], [status_dr], queue=False
        ).then(
            do_chat_deep_research, [pending_dr_msg, bot_dr, model_dd_dr, dr_memory_chk, dr_use_playwright_chk, dr_headless_chk, dr_manager_max_steps, dr_search_max_steps, dr_timeout, lang_state],
            [bot_dr, acc_dr_chat, status_dr]
        )

        def clear_dr_fn():
            # See clear_gen_fn() above — dropping the cached manager agent
            # (and its search sub-agent) is enough to guarantee a fresh,
            # empty-memory agent next build.
            deep_research_agent.reset_agent()
            return [], "", gr.update(open=False), gr.update(visible=False)

        clear_dr.click(clear_dr_fn, outputs=[bot_dr, msg_dr, acc_dr_chat, status_dr])
        reload_dr.click(reload_dr_fn, [model_dd_dr], [reload_dr_out])
        unload_dr_btn.click(unload_dr_fn, [lang_state], [reload_dr_out])
        reset_dr_btn.click(reset_dr_agent_fn, outputs=[reset_dr_out])

        # Vision Chat
        def load_vlm_fn(label, mmproj_label):
            mid = mr.VLM_OPTIONS.get(label, mr.DEFAULT_VLM_MODEL)
            mmproj_path = None
            if mmproj_label and mid:
                candidates = mr.get_mmproj_choices_for_vlm(mid)
                mmproj_path = candidates.get(mmproj_label)
            try:
                models.force_reload_vlm(mid, mmproj_path=mmproj_path)
                return gr.update(value=f"✅ '{mid}' loaded", visible=True)
            except Exception as e:
                return gr.update(value=f"❌ {e}", visible=True)

        def unload_vlm_fn(lang_key):
            return gr.update(value=models.unload_vlm_fn(lang_key), visible=True)

        def stash_vis(user_message):
            # See stash_gen() above.
            return "", user_message

        def show_thinking_vis(use_visual_rag, lang_key):
            l = LANGUAGES.get(lang_key, LANGUAGES["kh"])
            msg = l["think_vis_rag"] if use_visual_rag else l["think_vis"]
            return gr.update(value=msg, visible=True)

        def do_chat_vision(pending_message, uploaded_image, history, vlm_label, use_visual_rag, use_memory, lang_key, mmproj_label):
            history, img_reset = chat.chat_vision(pending_message, uploaded_image, history, vlm_label, use_visual_rag, use_memory, lang_key=lang_key, mmproj_label=mmproj_label)
            return history, img_reset, gr.update(open=True), gr.update(visible=False)

        send_vis.click(stash_vis, [msg_vis], [msg_vis, pending_vis_msg], queue=False).then(
            show_thinking_vis, [vis_rag_chk, lang_state], [status_vis], queue=False
        ).then(
            do_chat_vision, [pending_vis_msg, img_upload, bot_vis, vlm_dd, vis_rag_chk, vis_memory_chk, lang_state, mmproj_dd_vis],
            [bot_vis, img_upload, acc_vis_chat, status_vis]
        )
        msg_vis.submit(stash_vis, [msg_vis], [msg_vis, pending_vis_msg], queue=False).then(
            show_thinking_vis, [vis_rag_chk, lang_state], [status_vis], queue=False
        ).then(
            do_chat_vision, [pending_vis_msg, img_upload, bot_vis, vlm_dd, vis_rag_chk, vis_memory_chk, lang_state, mmproj_dd_vis],
            [bot_vis, img_upload, acc_vis_chat, status_vis]
        )
        clear_vis.click(lambda: ([], None, gr.update(open=False), gr.update(visible=False)),
                        outputs=[bot_vis, img_upload, acc_vis_chat, status_vis])
        load_vlm_btn.click(load_vlm_fn, [vlm_dd, mmproj_dd_vis], [load_vlm_out])
        unload_vlm_btn.click(unload_vlm_fn, [lang_state], [load_vlm_out])

        # Speech to Text
        def load_stt_fn(label):
            mid = mr.STT_OPTIONS.get(label, mr.DEFAULT_STT_MODEL)
            try:
                models.force_reload_stt(mid)
                return gr.update(value=f"✅ '{mid}' loaded", visible=True)
            except Exception as e:
                return gr.update(value=f"❌ {e}", visible=True)

        def unload_stt_fn(lang_key):
            return gr.update(value=models.unload_stt_fn(lang_key), visible=True)

        def do_transcribe(audio_path, stt_label, lang_choice):
            mid = mr.STT_OPTIONS.get(stt_label, mr.DEFAULT_STT_MODEL)
            text = models.transcribe_audio(audio_path, language=lang_choice, model_id=mid)
            # Reveal (expand) the result accordion now that there's a
            # transcription to show — stays collapsed until this runs.
            return gr.update(value=text, visible=True), gr.update(open=True)

        transcribe_btn.click(do_transcribe, [stt_audio, stt_dd, stt_lang_dd], [stt_output, acc_stt_result])
        load_stt_btn.click(load_stt_fn, [stt_dd], [load_stt_out])
        unload_stt_btn.click(unload_stt_fn, [lang_state], [load_stt_out])

        # Data Analysis
        def reset_data_agent_fn():
            data_analysis.reset_agent()
            return gr.update(value="✅ Agent reset — will rebuild on next run.", visible=True)

        ANALYSIS_PROMPTS = {
            "exploratory": "",
            "sales": (
                "Perform a full sales analysis following this workflow:\n"
                "1. Show total sales by month (line chart)\n"
                "2. Identify top-performing products (bar chart)\n"
                "3. Break down by customer segment (pie/donut chart)\n"
                "4. Compare this year vs last year (grouped bar chart)\n"
                "5. Forecast next quarter based on trends\n\n"
                "Write the final report using the Insight Report template:\n"
                "## Executive Summary\n"
                "## Key Metrics (table: Metric | Value | Change)\n"
                "## Trends\n"
                "## Recommendations"
            ),
            "customer": (
                "Perform a full customer analysis following this workflow:\n"
                "1. Show customer distribution by segment (bar chart)\n"
                "2. Calculate key metrics per segment (avg spend, count)\n"
                "3. Identify top customers by value\n"
                "4. Analyze purchase frequency patterns\n\n"
                "Write the final report using the Insight Report template:\n"
                "## Executive Summary\n"
                "## Key Metrics\n"
                "## Customer Segments\n"
                "## Recommendations"
            ),
            "financial": (
                "Perform a full financial analysis following this workflow:\n"
                "1. Calculate profit margins by product (bar chart)\n"
                "2. Show expense breakdown (pie chart)\n"
                "3. Analyze revenue vs expense trends over time (line chart)\n"
                "4. Compare budget vs actual (grouped bar chart)\n\n"
                "Write the final report using the Insight Report template:\n"
                "## Executive Summary\n"
                "## Key Metrics\n"
                "## Trends\n"
                "## Recommendations"
            ),
            "payroll": (
                "Perform a full payroll analysis following this workflow:\n"
                "1. LOAD & VALIDATE — Load the payroll data; check for missing "
                "values in employee ID, hours worked, pay rate, deductions, and "
                "tax fields. Report any data quality issues.\n"
                "2. GROSS PAY — Calculate gross pay per employee (hours × rate, "
                "or salary proration). Show distribution with a histogram + "
                "boxplot. Flag any outliers.\n"
                "3. DEDUCTIONS & TAX — Break down deductions (health insurance, "
                "retirement, tax withholdings, etc.) per employee. Plot a "
                "stacked bar chart of deductions by department.\n"
                "4. NET PAY — Calculate net pay (gross − deductions − tax). "
                "Show summary stats (mean, median, min, max). Plot net pay "
                "distribution.\n"
                "5. DEPARTMENT SUMMARY — Aggregate payroll by department: total "
                "gross, total deductions, total net, headcount, avg salary. "
                "Plot a grouped bar chart comparing departments.\n"
                "6. COST TRENDS — If the data has a date column, plot total "
                "payroll cost over time (line chart).\n\n"
                "Write the final report using the Insight Report template:\n"
                "## Executive Summary\n"
                "## Key Metrics (total gross, total deductions, total net, "
                "headcount, avg cost per employee)\n"
                "## Department Breakdown (table)\n"
                "## Recommendations"
            ),
        }

        def set_analysis_prompt(choice):
            return ANALYSIS_PROMPTS.get(choice, "")

        def stash_data(question):
            # See stash_gen() above.
            return "", question

        def show_thinking_data(lang_key):
            l = LANGUAGES.get(lang_key, LANGUAGES["kh"])
            return gr.update(value=l["think_data"], visible=True)

        def do_data_analysis(files, pending_question, model_label, history,
                              use_memory, lang_key, max_steps, execution_timeout):
            # data_analysis.run_data_analysis() is a generator (see
            # data_analysis.py): yields once per live agent step during
            # the EDA (load, chart, correlate, ...) using gr.update()
            # no-op placeholders for the gallery/report outputs so they
            # don't flicker empty mid-run, then a final yield with the
            # real chart list + report file. Reveals (expands) both the
            # conversation and results accordions on the first yield —
            # both stay collapsed until an analysis actually runs — and
            # hides the "thinking" status line only once the run is
            # actually done.
            last = (history, gr.update(), gr.update())
            for h, gallery, report_file in data_analysis.run_data_analysis(
                files, pending_question, model_label, history, use_memory,
                lang_key=lang_key, max_steps=max_steps,
                execution_timeout=execution_timeout,
            ):
                last = (h, gallery, report_file)
                yield h, gallery, report_file, gr.update(open=True), gr.update(open=True), gr.update()
            h, gallery, report_file = last
            yield h, gallery, report_file, gr.update(open=True), gr.update(open=True), gr.update(visible=False)

        analysis_type_data.change(set_analysis_prompt, [analysis_type_data], [msg_data])

        send_data.click(stash_data, [msg_data], [msg_data, pending_data_question], queue=False).then(
            show_thinking_data, [lang_state], [status_data], queue=False
        ).then(
            do_data_analysis,
            [data_file_up, pending_data_question, model_dd_data, bot_data,
             data_memory_chk, lang_state, data_max_steps, data_execution_timeout],
            [bot_data, data_gallery, data_report_file, acc_data_chat, acc_data_results, status_data]
        )
        msg_data.submit(stash_data, [msg_data], [msg_data, pending_data_question], queue=False).then(
            show_thinking_data, [lang_state], [status_data], queue=False
        ).then(
            do_data_analysis,
            [data_file_up, pending_data_question, model_dd_data, bot_data,
             data_memory_chk, lang_state, data_max_steps, data_execution_timeout],
            [bot_data, data_gallery, data_report_file, acc_data_chat, acc_data_results, status_data]
        )

        def clear_data_fn():
            # See clear_gen_fn() above — dropping the cached agent is
            # enough to guarantee fresh memory next build. Also resets the
            # "last dataset" tracker so the next upload doesn't skip a
            # reset it should otherwise trigger.
            data_analysis.reset_agent()
            data_analysis._last_data_context["key"] = None
            return [], None, None, gr.update(open=False), gr.update(open=False), gr.update(visible=False)

        clear_data.click(clear_data_fn,
                         outputs=[bot_data, data_gallery, data_report_file, acc_data_chat, acc_data_results, status_data])
        reset_data_btn.click(reset_data_agent_fn, outputs=[reset_data_out])

        # Data Analysis — Load / Unload (NEW)
        def reload_data_fn(label):
            data_analysis.reset_agent()
            mid = mr.MODEL_OPTIONS.get(label, mr.DEFAULT_LLM_MODEL)
            try:
                models.force_reload_llm(mid)
                return gr.update(value=f"✅ '{mid}' loaded", visible=True)
            except Exception as e:
                return gr.update(value=f"❌ {e}", visible=True)

        def unload_data_fn(lang_key):
            msg = models.unload_llm_fn(lang_key)
            data_analysis.reset_agent()
            return gr.update(value=msg, visible=True)

        reload_data_btn.click(reload_data_fn, [model_dd_data], [reload_data_out])
        unload_data_btn.click(unload_data_fn, [lang_state], [reload_data_out])

        # ── whisper.cpp server settings ──────────────────────────
        def do_set_whisper_server_path(path):
            whisper_cpp_backend.set_whisper_server_exe_path(path)
            return gr.update(value=f"✅ whisper-server path saved", visible=True)

        def do_set_whisper_server_args(args_str):
            whisper_cpp_backend.set_whisper_server_extra_args(args_str)
            return gr.update(value=f"✅ Extra whisper-server args saved.", visible=True)

        whisper_server_exe_tb.submit(do_set_whisper_server_path, [whisper_server_exe_tb], [whisper_server_status])
        whisper_server_args_tb.submit(do_set_whisper_server_args, [whisper_server_args_tb], [whisper_server_status])

        # ── Provider change → filter model dropdown choices ──────
        def _filter_models_for_provider(provider_label, provider_map, model_type, current_model_dd):
            sentinel = provider_map.get(provider_label, mr.PROVIDER_LOCAL_HF)
            mr.set_saved_provider(model_type, sentinel)
            choices_dict = mr.get_model_options_for_provider(sentinel, model_type)
            choices = list(choices_dict.keys())
            # Try to keep the current selection if still valid
            current = current_model_dd if current_model_dd in choices else (choices[0] if choices else None)
            return gr.update(choices=choices, value=current)

        provider_dd_gen.change(
            lambda p, m: _filter_models_for_provider(p, mr.LLM_PROVIDER_OPTIONS, "llm", m),
            [provider_dd_gen, model_dd_gen], [model_dd_gen],
        )
        provider_dd_rag.change(
            lambda p, m: _filter_models_for_provider(p, mr.LLM_PROVIDER_OPTIONS, "llm", m),
            [provider_dd_rag, model_dd_rag], [model_dd_rag],
        )
        provider_dd_data.change(
            lambda p, m: _filter_models_for_provider(p, mr.LLM_PROVIDER_OPTIONS, "llm", m),
            [provider_dd_data, model_dd_data], [model_dd_data],
        )
        provider_dd_dr.change(
            lambda p, m: _filter_models_for_provider(p, mr.LLM_PROVIDER_OPTIONS, "llm", m),
            [provider_dd_dr, model_dd_dr], [model_dd_dr],
        )
        def _update_mmproj_choices(vlm_label: str, visible: bool = True) -> gr.update:
            if not visible:
                return gr.update(choices=[], value=None, visible=False)
            mid = mr.VLM_OPTIONS.get(vlm_label)
            if not mid or not str(mid).lower().endswith(".gguf"):
                return gr.update(choices=[], value=None, visible=False)
            candidates = mr.get_mmproj_choices_for_vlm(mid)
            choices = list(candidates.keys())
            auto = mr.GGUF_VLM_MMPROJ_MAP.get(mid)
            value = None
            if auto:
                for lbl, path in candidates.items():
                    if path == auto:
                        value = lbl
                        break
            return gr.update(choices=choices, value=value, visible=bool(choices))

        provider_dd_vlm.change(
            lambda p, m: _filter_models_for_provider(p, mr.VLM_PROVIDER_OPTIONS, "vlm", m),
            [provider_dd_vlm, vlm_dd], [vlm_dd],
        ).then(
            lambda p: gr.update(visible="llama.cpp" in p),
            [provider_dd_vlm], [mmproj_dd_vis],
        ).then(
            lambda p, m: _update_mmproj_choices(m, "llama.cpp" in p),
            [provider_dd_vlm, vlm_dd], [mmproj_dd_vis],
        )

        vlm_dd.change(
            lambda m, p: _update_mmproj_choices(m, "llama.cpp" in p),
            [vlm_dd, provider_dd_vlm], [mmproj_dd_vis],
        )
        provider_dd_stt.change(
            lambda p, m: _filter_models_for_provider(p, mr.STT_PROVIDER_OPTIONS, "stt", m),
            [provider_dd_stt, stt_dd], [stt_dd],
        )
        provider_dd_embed.change(
            lambda p, m: _filter_models_for_provider(p, mr.EMBED_PROVIDER_OPTIONS, "embed", m),
            [provider_dd_embed, embed_dd], [embed_dd],
        )

        # Knowledge Base — Embedding Model
        def load_embed_fn(label, lang_key):
            mid = mr.EMBED_OPTIONS.get(label, mr.DEFAULT_EMBED_MODEL)
            # Check BEFORE switching: if documents are already indexed,
            # warn about the dimension mismatch this can cause rather than
            # letting the user discover it only on the next query/upload —
            # see knowledge_base.get_collection_embedding_dim().
            existing_dim = kb.get_collection_embedding_dim()
            mr.set_embed_model(mid)
            try:
                models.force_reload_embed_model(mid)
                msg = f"✅ '{mid}' loaded."
                if existing_dim is not None:
                    new_dim = mr.EMBED_MODEL_DIMENSIONS.get(mid)
                    if new_dim is not None and new_dim != existing_dim:
                        msg += (
                            f" ⚠️ Your knowledge base was indexed at "
                            f"{existing_dim} dimensions — '{mid}' produces "
                            f"{new_dim}. Retrieval will fail until you switch "
                            f"back or clear ('💥 Clear ALL') and re-index."
                        )
                    else:
                        msg += (
                            " ⚠️ Your knowledge base already has indexed "
                            "documents — if this model's vector dimension "
                            "differs from what they were indexed with, "
                            "retrieval will fail until you switch back or "
                            "clear ('💥 Clear ALL') and re-index."
                        )
                return gr.update(value=msg, visible=True)
            except Exception as e:
                return gr.update(value=f"❌ {e}", visible=True)

        def unload_embed_fn(lang_key):
            return gr.update(value=models.unload_embed_model_fn(lang_key), visible=True)

        load_embed_btn.click(load_embed_fn, [embed_dd, lang_state], [load_embed_out])
        unload_embed_btn.click(unload_embed_fn, [lang_state], [load_embed_out])

        # Knowledge Base
        def on_select(evt: gr.SelectData, current):
            row = evt.index[0]
            if row in current: current.remove(row)
            else:              current.append(row)
            return current

        def do_upload(files, vis_ret_label, theme, subtheme, lang_key):
            import traceback
            try:
                msg = kb.index_uploaded_files(files, vis_ret_label, theme, subtheme)
            except Exception as e:
                msg = f"❌ {traceback.format_exc()}"
            stats = kb.get_index_stats(lang_key)
            return gr.update(value=msg, visible=True), kb.get_doc_table(), gr.update(open=True), stats, stats

        def unload_visual_fn(lang_key):
            return gr.update(value=kb.unload_visual_retriever_fn(lang_key), visible=True)

        def do_refresh(lang_key):
            stats = kb.get_index_stats(lang_key)
            return kb.get_doc_table(), gr.update(open=True), stats, stats

        def do_delete(selected, table_data, lang_key):
            rows = table_data if isinstance(table_data, list) else table_data.values.tolist()
            new_table, msg = kb.delete_selected_sources(selected, rows)
            stats = kb.get_index_stats(lang_key)
            return new_table, gr.update(value=msg, visible=True), [], gr.update(open=True), stats, stats

        def do_clear(lang_key):
            table, msg = kb.clear_index()
            stats = kb.get_index_stats(lang_key)
            return table, gr.update(value=msg, visible=True), [], gr.update(open=True), stats, stats

        doc_table.select(on_select,        [selected_rows_state], [selected_rows_state])
        up_btn.click(do_upload,            [file_up, vis_ret_dd, theme_tb, subtheme_tb, lang_state], [up_msg, doc_table, acc_kb_docs, kb_status_bar, rag_status_bar])
        unload_visual_btn.click(unload_visual_fn, [lang_state], [up_msg])
        refresh_btn.click(do_refresh,      [lang_state], [doc_table, acc_kb_docs, kb_status_bar, rag_status_bar])
        delete_sel_btn.click(do_delete,    [selected_rows_state, doc_table, lang_state], [doc_table, action_msg, selected_rows_state, acc_kb_docs, kb_status_bar, rag_status_bar])
        clear_all_btn.click(do_clear,      [lang_state], [doc_table, action_msg, selected_rows_state, acc_kb_docs, kb_status_bar, rag_status_bar])

        # ── Language switcher ─────────────────────────────────────
        def switch_lang(lang_name):
            lk = "kh" if lang_name == "Khmer" else "en"
            l  = LANGUAGES[lk]
            return (
                lk,
                # header
                f'<div class="header-wrap"><span class="header-title">{l["title"]}</span>'
                f'<span class="beta-badge">BETA</span></div>',
                f'<div class="header-wrap"><span class="header-sub">{l["subtitle"].format(device=DEVICE.upper(), version=APP_VERSION)}</span></div>',
                # Tab strip titles themselves (gr.Tab's own `label=`) — these
                # were previously never updated on a language switch, only
                # the CONTENT inside each tab was, which is why the tab
                # titles stayed stuck in Khmer even after switching to
                # English (or vice versa).
                gr.update(label=l["tab_general"]),
                gr.update(label=l["tab_vision"]),
                gr.update(label=l["tab_stt"]),
                gr.update(label=l["tab_data"]),
                gr.update(label=l["tab_kb"]),
                gr.update(label=l["tab_rag"]),
                gr.update(label=l["tab_deep_research"]),
                gr.update(label=l["tab_about"]),
                # GPU-incompatibility warning banner, re-rendered in the
                # newly selected language (empty string if there's
                # nothing to warn about — see _gpu_warning_html()).
                _gpu_warning_html(lk),
                # Model Settings accordion (collapsed by default)
                gr.update(value=l["accordion_model_settings"]),
                # GGUF model folder
                gr.update(label=l["label_gguf_dir"], placeholder=l["gguf_dir_placeholder"]),
                gr.update(value=l["btn_scan_gguf"]),
                gr.update(label=l["label_context_window"], info=l["info_context_window"]),
                # General Chat
                gr.update(placeholder=l["placeholder_gen"]),
                gr.update(value=l["btn_send"]),
                gr.update(value=l["btn_clear"]),
                gr.update(label=l["accordion_chat"]),
                gr.update(value=f"### {l['accordion_settings']}"),
                gr.update(value=l["tab_general_desc"]),
                gr.update(label=l["label_gen_agentic"], info=l["info_gen_agentic"]),
                gr.update(label=l["label_memory"], info=l["info_memory"]),
                gr.update(label=l["label_llm"]),
                gr.update(value=l["btn_load"]),
                gr.update(value=l["btn_unload"]),
                # RAG Chat
                gr.update(placeholder=l["placeholder_rag"]),
                gr.update(value=l["btn_send"]),
                gr.update(value=l["btn_clear"]),
                gr.update(label=l["accordion_chat"]),
                gr.update(value=f"### {l['accordion_settings']}"),
                gr.update(value=l["tab_rag_desc"]),
                gr.update(label=l["theme_label"], placeholder=l["theme_placeholder"]),
                gr.update(label=l["subtheme_label"], placeholder=l["subtheme_placeholder"]),
                gr.update(label=l["label_rag_agentic"], info=l["info_rag_agentic"]),
                gr.update(label=l["label_memory"], info=l["info_memory"]),
                gr.update(label=l["label_llm"]),
                gr.update(value=l["btn_load"]),
                gr.update(value=l["btn_unload"]),
                # Deep Research
                gr.update(placeholder=l["placeholder_deep_research"]),
                gr.update(value=l["btn_send"]),
                gr.update(value=l["btn_clear"]),
                gr.update(label=l["accordion_chat"]),
                gr.update(value=f"### {l['accordion_settings']}"),
                gr.update(value=l["tab_deep_research_desc"]),
                gr.update(label=l["label_memory"], info=l["info_memory"]),
                gr.update(label=l["label_llm"]),
                gr.update(value=l["btn_load"]),
                gr.update(value=l["btn_unload"]),
                gr.update(value=l["btn_reset_agent"]),
                # Vision Chat
                gr.update(placeholder=l["placeholder_vis"]),
                gr.update(value=l["btn_send"]),
                gr.update(value=l["btn_clear"]),
                gr.update(label=l["accordion_chat"]),
                gr.update(value=f"### {l['accordion_settings']}"),
                gr.update(value=l["tab_vision_desc"]),
                gr.update(label=l["label_vlm"]),
                gr.update(label=l["label_vis_rag"], info=l["label_vis_rag_info"]),
                gr.update(label=l["label_memory"], info=l["info_memory"]),
                gr.update(value=l["btn_load"]),
                gr.update(value=l["btn_unload"]),
                gr.update(value=l["btn_unload"]),
                # STT
                gr.update(label=l["stt_audio_label"]),
                gr.update(value=l["btn_transcribe"]),
                gr.update(label=f"📝 {l['label_res']}"),
                gr.update(label=l["label_res"]),
                gr.update(value=f"### {l['accordion_settings']}"),
                gr.update(value=l["tab_stt_desc"]),
                gr.update(label=l["label_stt"]),
                gr.update(label=l["label_stt_lang"]),
                gr.update(value=l["btn_load"]),
                gr.update(value=l["btn_unload"]),
                gr.update(value=l["stt_khmer_hint"]),
                # Data Analysis
                gr.update(label=l["data_file_label"]),
                gr.update(placeholder=l["placeholder_data"]),
                gr.update(value=l["btn_send"]),
                gr.update(value=l["btn_clear"]),
                gr.update(label=l["accordion_chat"]),
                gr.update(label=l["accordion_data_results"]),
                gr.update(label=l["label_charts"]),
                gr.update(label=l["label_report_file"]),
                gr.update(value=f"### {l['accordion_settings']}"),
                gr.update(value=l["tab_data_desc"]),
                gr.update(label=l["label_llm"]),
                gr.update(label=l["label_memory"], info=l["info_memory"]),
                gr.update(value=l["btn_reset_agent"]),
                gr.update(
                    label=l["label_analysis_type"],
                    choices=[
                        ("exploratory", l["analysis_exploratory"]),
                        ("sales", l["analysis_sales"]),
                        ("customer", l["analysis_customer"]),
                        ("financial", l["analysis_financial"]),
                        ("payroll", l["analysis_payroll"]),
                    ],
                ),
                # Knowledge Base
                gr.update(label=l["label_embed"], info=l["info_embed"]),
                gr.update(value=l["btn_load"]),
                gr.update(value=l["btn_unload"]),
                gr.update(label=l["accordion_details"]),
                gr.update(value=l["info_embed_detail"]),
                gr.update(label=l["accordion_add"]),
                gr.update(label=l["file_label"]),
                gr.update(label=l["label_vis_ret"]),
                gr.update(label=l["theme_label"], placeholder=l["theme_placeholder"]),
                gr.update(label=l["subtheme_label"], placeholder=l["subtheme_placeholder"]),
                gr.update(value=l["btn_index"]),
                gr.update(value=l["btn_unload"]),
                gr.update(label=l["label_res"]),
                gr.update(label=l["label_kb_docs"]),
                gr.update(value=l["btn_refresh"]),
                gr.update(value=l["btn_delete"]),
                gr.update(value=l["btn_clear_all"]),
                # Status bars (Knowledge Base tab + RAG Chat tab)
                kb.get_index_stats(lk),
                kb.get_index_stats(lk),
                # Status indicators — reset to hidden with correct language text
                gr.update(value=l["think_gen"], visible=False),
                gr.update(value=l["think_rag"], visible=False),
                gr.update(value=l["think_dr"], visible=False),
                gr.update(value=l["think_vis"], visible=False),
                gr.update(value=l["think_data"], visible=False),
                # "Details" accordions (collapsed long explanations) + their content
                gr.update(label=l["accordion_details"]), gr.update(value=l["info_context_window_detail"]),
                gr.update(label=l["accordion_details"]), gr.update(value=l["info_gen_agentic_detail"]), gr.update(value=l["info_memory_detail"]),
                gr.update(label=l["accordion_details"]), gr.update(value=l["info_rag_agentic_detail"]), gr.update(value=l["info_memory_detail"]),
                gr.update(label=l["accordion_details"]), gr.update(value=l["info_memory_detail"]),
                gr.update(label=l["accordion_details"]), gr.update(value=l["label_vis_rag_info_detail"]), gr.update(value=l["info_memory_detail"]),
                gr.update(label=l["accordion_details"]), gr.update(value=l["stt_khmer_hint_detail"]),
                gr.update(label=l["accordion_details"]), gr.update(value=l["info_memory_detail"]),
                # ── Global Model Settings accordion (new) ──────────
                gr.update(value=f"### {l['label_provider_section']}"),
                gr.update(label=l["label_provider"]),
                gr.update(label=l["label_provider"]),
                gr.update(label=l["label_provider"]),
                gr.update(label=l["label_provider"]),
                gr.update(label=l["label_provider"]),
                gr.update(label=l["label_provider"]),
                gr.update(label=l["label_provider"]),
                gr.update(value=l["btn_load"]),
                gr.update(value=l["btn_unload"]),
                gr.update(visible=False),
            )

        _lang_outputs = [
            lang_state, header_title, header_sub,
            # Tab strip titles (gr.Tab's own label=) — see switch_lang()'s
            # matching block above for why these are needed separately
            # from every other per-tab component below.
            tab_gen, tab_vis, tab_stt, tab_data, tab_kb, tab_rag, tab_deep_research, tab_about,
            gpu_warning_html,
            acc_model_settings,
            gguf_dir_tb, scan_gguf_btn, ctx_window_dd,
            # General Chat
            msg_gen, send_gen, clear_gen, acc_gen_chat, gen_settings_header, gen_desc, gen_agentic_chk, gen_memory_chk, model_dd_gen, reload_gen, unload_gen_btn,
            # RAG Chat
            msg_rag, send_rag, clear_rag, acc_rag_chat, rag_settings_header, rag_desc, theme_tb_rag, subtheme_tb_rag, rag_agentic_chk, rag_memory_chk, model_dd_rag, reload_rag, unload_rag_btn,
            # Deep Research
            msg_dr, send_dr, clear_dr, acc_dr_chat, dr_settings_header, dr_desc, dr_memory_chk, model_dd_dr, reload_dr, unload_dr_btn, reset_dr_btn,
            # Vision Chat
            msg_vis, send_vis, clear_vis, acc_vis_chat, vis_settings_header, vis_desc, vlm_dd, mmproj_dd_vis, vis_rag_chk, vis_memory_chk, load_vlm_btn, unload_vlm_btn,
            # STT
            stt_audio, transcribe_btn, acc_stt_result, stt_output, stt_settings_header, stt_desc,
            stt_dd, stt_lang_dd, load_stt_btn, unload_stt_btn, stt_hint,
            # Data Analysis
            data_file_up, msg_data, send_data, clear_data, acc_data_chat, acc_data_results, data_gallery, data_report_file,
            data_settings_header, data_desc, model_dd_data, data_memory_chk, reset_data_btn, analysis_type_data,
            # Knowledge Base
            embed_dd, load_embed_btn, unload_embed_btn, acc_embed_detail, embed_detail_md,
            acc_add, file_up, vis_ret_dd, theme_tb, subtheme_tb, up_btn, unload_visual_btn, up_msg,
            acc_kb_docs, refresh_btn, delete_sel_btn, clear_all_btn,
            # Status bars (Knowledge Base tab + RAG Chat tab)
            kb_status_bar, rag_status_bar,
            # Status indicators (hidden "thinking…" lines) — reset to
            # hidden on a language switch so a stale visible status from
            # right before the switch doesn't linger in the old language.
            status_gen, status_rag, status_dr, status_vis, status_data,
            # "Details" accordions (collapsed long explanations)
            acc_ctx_detail, ctx_window_detail_md,
            acc_gen_detail, gen_agentic_detail_md, gen_memory_detail_md,
            acc_rag_detail, rag_agentic_detail_md, rag_memory_detail_md,
            acc_dr_detail, dr_memory_detail_md,
            acc_vis_detail, vis_rag_detail_md, vis_memory_detail_md,
            acc_stt_detail, stt_hint_detail_md,
            acc_data_detail, data_memory_detail_md,
            # Accordion section headers
            provider_section_md,
            # Provider dropdowns
            provider_dd_gen, provider_dd_rag, provider_dd_data, provider_dd_dr,
            provider_dd_vlm, provider_dd_stt, provider_dd_embed,
            # Data Analysis load/unload buttons
            reload_data_btn, unload_data_btn,
            # Whisper server status (reset hidden)
            whisper_server_status,
        ]

        lang_dropdown.change(switch_lang, [lang_dropdown], _lang_outputs)

        # NOTE: no demo.load() re-initializer here. Every component above
        # is already created with the correct Khmer text/value via `L`
        # (e.g. label=L["label_llm"], placeholder=L["placeholder_gen"]),
        # so a startup call re-pushing the same Khmer values into all 68
        # components across every tab is redundant — and firing that many
        # updates into tabs the browser hasn't finished mounting yet (any
        # tab other than the default-active one) can leave those
        # components stuck showing a perpetual loading state. Only
        # lang_dropdown.change() needs to touch all of them, and that only
        # runs after the user explicitly switches languages, well after
        # the initial page mount has finished.

        # ── Live-refresh index stats on tab click ────────────────
        # NOT done via demo.load() — the embedding model should NOT load
        # until the user explicitly visits the Knowledge Base or RAG Chat
        # tab. The .select() hooks below populate the status bars on first
        # visit and refresh them on every subsequent click.
        tab_kb.select(kb.get_index_stats, [lang_state], [kb_status_bar, rag_status_bar])
        tab_rag.select(kb.get_index_stats, [lang_state], [kb_status_bar, rag_status_bar])

        return demo
