"""
chat.py — Chat-turn handlers for the General Chat, RAG Chat, and Vision
Chat tabs, plus the <think>-tag reasoning/answer formatter shared by the
text tabs.
"""

import re
import time
from typing import Optional

from PIL import Image

from i18n import LANGUAGES
import knowledge_base as kb
import model_registry as mr
import models
import general_agent
import rag_agent
import deep_research_agent
import agent_memory
import agent_streaming
from hardware import DEVICE

# NOTE: agentic memory (agent.memory.steps) lives only in RAM, for as long
# as the cached CodeAgent object for that tab stays alive — see
# agent_memory.py's module docstring for why this app deliberately does
# NOT persist it to disk. The "🧠 Conversation Memory" checkbox is marked
# experimental in the UI for the same reason: it resets on a model
# switch, "Clear", or an app restart, and — especially with small/local
# models — can occasionally produce a confused reply if a step written by
# one model gets replayed against a different one after a mid-conversation
# model switch.

# How many prior user+assistant exchanges to feed back into the *direct*
# (non-agentic) chat paths as short-term conversation memory. Agentic
# paths don't use this — they get real memory from smolagents' own
# agent.memory (see general_agent.py / rag_agent.py / agent_memory.py).
DIRECT_CHAT_MEMORY_TURNS = 6

# How many turns of memory an agentic CodeAgent is allowed to keep before
# older turns get dropped (see agent_memory.cap_agent_memory()).
AGENTIC_MEMORY_TURNS = 6

# Deep Research reports are much longer per turn than a normal chat
# answer (and each turn can also include several delegated sub-agent
# calls), so its memory budget is kept smaller than the other agentic
# tabs' default — same reasoning as data_analysis.DATA_AGENT_MEMORY_TURNS.
DEEP_RESEARCH_MEMORY_TURNS = 4





# Reusable HTML templates for format_llm_response() — extracted to
# module-level constants so the same HTML strings aren't built from scratch
# on every single chat turn (see the three branches in
# format_llm_response() below, which each use some combination of these).
_THINK_TPL = (
    '<details class="think-block" {open}>\n'
    '<summary class="think-summary">\n'
    '<span class="think-badge">{summary}</span>\n'
    '<span class="think-hint">(click to toggle)</span>\n'
    '</summary>\n'
    '<div class="think-body">\n{body}\n</div>\n'
    '</details>\n'
)

_ANSWER_TPL = (
    '<div class="final-answer-block">\n'
    '<div class="answer-header-badge">{title}</div>\n'
    '<div class="answer-body">\n{body}\n</div>\n'
    '</div>'
)


def format_llm_response(text: str, lang_key: str = "kh") -> str:
    if not text or not isinstance(text, str):
        return text or ""

    l = LANGUAGES.get(lang_key, LANGUAGES["kh"])
    reasoning_title = l.get("err_reasoning", "🧠 ដំណើរការគិត / Reasoning Process")
    answer_title = l.get("err_answer", "✨ ចម្លើយចុងក្រោយ / Final Answer")
    no_reasoning = l.get("no_reasoning_text", "គ្មានព័ត៌មានគិត")
    truncated_notice = l.get("truncated_notice", "⚠️ ការគិតត្រូវបានកាត់ផ្តាច់ (Truncated)")

    thinking = None
    answer = None

    # 1. Match <think>...</think> or <reasoning>...</reasoning> or <thought>...</thought>
    m_tag = re.search(r"<(think|reasoning|thought)>(.*?)</\1>(.*)", text, re.DOTALL | re.IGNORECASE)
    if m_tag:
        thinking = m_tag.group(2).strip()
        answer = m_tag.group(3).strip()
    else:
        # 2. Match " thinking... response..."
        m_resp = re.search(r" thinking(.*?) response(.*)", text, re.DOTALL)
        if m_resp:
            thinking = m_resp.group(1).strip()
            answer = m_resp.group(2).strip()
        else:
            # 3. Unclosed <think> or " thinking"
            m_unclosed = re.search(r"<(think|reasoning|thought)>(.*)", text, re.DOTALL | re.IGNORECASE)
            if m_unclosed:
                thinking = m_unclosed.group(2).strip()
                answer = ""
            elif " thinking" in text and " response" not in text:
                thinking = text.split(" thinking", 1)[1].strip()
                answer = ""

    if thinking is not None:
        think_html = _THINK_TPL.format(
            open="",
            summary=reasoning_title,
            body=thinking if thinking else no_reasoning,
        )
        if answer:
            ans_html = _ANSWER_TPL.format(
                title=answer_title,
                body=answer,
            )
            return think_html + ans_html
        else:
            ans_html = _ANSWER_TPL.format(
                title=answer_title,
                body=truncated_notice,
            )
            return think_html + ans_html

    return text


def _strip_response_html(text: str) -> str:
    """Recover the plain-text answer from a previously HTML-formatted assistant reply."""
    if not text:
        return text
    text = re.sub(r"<details.*?</details>", "", text, flags=re.DOTALL)
    text = re.sub(r"<div class=\"final-answer-block\".*?<div class=\"answer-body\">(.*?)</div>\s*</div>", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"<hr>.*$", "", text, flags=re.DOTALL)
    text = re.sub(r"<b>\U0001F4AC[^<]*</b>\s*", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def _recent_memory_messages(history: list, max_turns: int = DIRECT_CHAT_MEMORY_TURNS) -> list:
    """Build a clean list of prior {"role", "content"} turns from the
    Gradio chatbot history, to hand to models._call_llm() as short-term
    conversation memory for the *direct* (non-agentic) chat paths.

    Keeps only the last `max_turns` user+assistant exchanges and strips
    HTML formatting from assistant replies (see _strip_response_html())
    so old markup/timing footers don't pollute the prompt.
    """
    if not history:
        return []
    cleaned = []
    for turn in history:
        role, content = turn.get("role"), turn.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        if role == "assistant":
            content = _strip_response_html(content)
            if not content:
                continue
        elif role != "user":
            continue
        cleaned.append({"role": role, "content": content})
    return cleaned[-(max_turns * 2):]


def _lang_instruction(lang_key: str) -> str:
    return "Answer in Khmer.\n\n" if lang_key == "kh" else ""


def chat_general_direct(user_message: str, history: list, model_label: str, use_memory: bool = True, lang_key: str = "kh"):
    """A generator yielding exactly ONE (history, "") tuple — the direct
    path has no intermediate agent steps to stream, but is written as a
    generator (rather than a plain function) so chat_general()'s
    `yield from` dispatch works uniformly regardless of which path (direct
    or agentic) it delegates to. See chat_general_agentic() below for the
    path that actually yields multiple times as live agent steps arrive.
    """
    if not user_message.strip():
        yield history, ""
        return
    history = history or []
    history.append({"role": "user", "content": user_message})
    model_id = mr.MODEL_OPTIONS.get(model_label, mr.DEFAULT_LLM_MODEL)
    try:
        # Memory: feed back the recent conversation (minus the message we
        # just appended above, which is passed separately as `user`) so
        # follow-ups like "and what about X?" have something to refer to.
        # Skipped entirely when the "🧠 Conversation Memory" checkbox is off.
        memory_messages = _recent_memory_messages(history[:-1]) if use_memory else []

        system = _lang_instruction(lang_key) + "You are a helpful, friendly assistant."
        # IMPORTANT: without this, instruct-tuned models (small ones
        # especially) tend to give a trained canned disclaimer like "I
        # don't have memory of past conversations" to any meta-question
        # about memory ("do you remember what I said earlier?") — even
        # though `memory_messages` below genuinely IS being sent as real
        # prior turns in this same request. The model isn't actually
        # checking its context; it's a reflexive trained response. The
        # agentic path (general_agent.GENERAL_AGENT_INSTRUCTIONS) already
        # has to explicitly counter this exact behavior — this applies
        # the same fix to the direct (non-agentic) path, which previously
        # had no such reminder at all. Only added when there's actually
        # prior history to reference, so a first message's system prompt
        # stays minimal.
        if memory_messages:
            system += (
                " The messages below marked as earlier turns in this "
                "conversation ARE genuinely visible to you in full — they "
                "are not hidden or inaccessible. If asked what was said "
                "earlier in this conversation, or a follow-up refers back "
                "to something mentioned before, look at those earlier "
                "turns and answer from them directly. Do NOT claim you "
                "lack memory or cannot see prior messages — you can."
            )

        # Apply the "🧠 Enable Model Reasoning" toggle (see
        # model_registry.apply_reasoning_toggle()'s docstring) right
        # before the call — a no-op unless the user has turned reasoning
        # off in ⚙️ Model Settings.
        user_message_final = mr.apply_reasoning_toggle(user_message)
        ans, elapsed = models._call_llm(model_id, system, user_message_final, history=memory_messages)
        formatted = format_llm_response(ans, lang_key)

        response = (
            formatted +
            f"\n\n<hr><sub>⏱ {elapsed:.1f}s | model: <code>{model_id}</code> ({DEVICE.upper()})</sub>"
        )

    except Exception as e:
        import traceback
        response = f"❌ {e}\n\n{traceback.format_exc()}"
    history.append({"role": "assistant", "content": response})
    yield history, ""


def chat_general_agentic(user_message: str, history: list, model_label: str,
                          use_memory: bool = True, lang_key: str = "kh",
                          max_steps: Optional[int] = None,
                          execution_timeout: Optional[int] = None,
                          use_tool_calling: bool = True):
    """Agentic General Chat: a smolagents CodeAgent (see general_agent.py)
    with the library's own built-in web-search/webpage tools
    (DuckDuckGoSearchTool, VisitWebpageTool), deciding for itself whether
    a question needs a web lookup before answering. Unlike RAG Chat's
    agent, this has no knowledge-base grounding requirement — it's meant
    for open-ended questions, not strictly-cited document Q&A.

    A GENERATOR: yields (history, "") once per live agent step as it
    happens (see agent_streaming.stream_agent_steps()), then one final
    time with the polished final answer appended — instead of blocking
    silently until the whole run finishes. Mirrors smolagents' own
    GradioUI streaming behaviour, adapted to this app's chat history
    shape/styling (see agent_streaming.py's module docstring).
    """
    if not user_message.strip():
        yield history, ""
        return
    history = history or []
    history.append({"role": "user", "content": user_message})
    model_id = mr.MODEL_OPTIONS.get(model_label, mr.DEFAULT_LLM_MODEL)
    try:
        agent = general_agent.get_general_agent(model_id, max_steps=max_steps, execution_timeout=execution_timeout, use_tool_calling=use_tool_calling)
        general_agent.reset_tool_usage()
        t0     = time.time()
        # reset=False keeps this CodeAgent's own memory (agent.memory.steps)
        # across turns instead of wiping it every message — see
        # https://huggingface.co/docs/smolagents/tutorials/memory. Capped
        # right after so a long conversation doesn't grow the prompt
        # unboundedly turn after turn. When the "🧠 Conversation Memory"
        # checkbox is off, reset=True instead, so every message starts
        # from a clean slate (no memory to cap either).
        #
        # The message is wrapped with a per-task citation reminder (NOT
        # just the raw user_message) because GENERAL_AGENT_INSTRUCTIONS'
        # citation requirement only reaches the model at all if this
        # installed smolagents version's CodeAgent accepts an
        # `instructions=` kwarg (see general_agent._build_code_agent()) —
        # on a version where it doesn't, this per-call reminder is the
        # ONLY place the model ever sees the requirement. Without it, the
        # model never writes a '### References' section, and the
        # "Sources used" block below always ends up empty even after a
        # turn that genuinely searched the web.
        task = general_agent.build_task_with_citation_reminder(user_message, lang_key)
        # See chat_general_direct()'s matching comment — a no-op unless
        # the "🧠 Enable Model Reasoning" toggle is off.
        task = mr.apply_reasoning_toggle(task)
        # Live step streaming — see agent_streaming.stream_agent_steps()'s
        # docstring for the shared (step_msg, is_final, final_output)
        # generator contract every agentic call site in this app now uses.
        result = None
        for step_msg, is_final, final_output in agent_streaming.stream_agent_steps(agent, task, reset=not use_memory):
            if not is_final:
                if step_msg is not None:
                    history.append(step_msg)
                    yield history, ""
                continue
            result = final_output
        if use_memory:
            agent_memory.cap_agent_memory(agent, max_turns=AGENTIC_MEMORY_TURNS)
        elapsed = time.time() - t0

        turn_count = sum(1 for s in agent.memory.steps if s.__class__.__name__ == "TaskStep")
        ans = str(result)
        # Only show sources the model actually appears to have USED in
        # its final answer — not every link `web_search` happened to
        # return this turn (most search hits are never read or relied on;
        # dumping all of them produced a misleading "sources" list full
        # of irrelevant results, e.g. random weather sites showing up for
        # an unrelated question just because one search query returned
        # them). general_agent.resolve_actually_used_sources() cross-
        # checks the model's own '### References' section against what
        # was really searched/visited this turn, falling back to pages
        # actually opened via visit_webpage (never to the full link dump)
        # if the model's citations don't check out. Its own (unverified)
        # References section is then swapped out for this verified one.
        queries, urls, links = general_agent.get_tool_usage()
        used_sources = general_agent.resolve_actually_used_sources(ans, urls, links)
        ans = general_agent.strip_trailing_references_section(ans)
        if used_sources:
            ref_lines = ["**🔗 Sources used for this answer:**"]
            ref_lines.extend(
                f"- {url}" if title == url else f"- [{title}]({url})"
                for title, url in used_sources
            )
            ans += "\n\n---\n" + "\n".join(ref_lines)
        formatted = format_llm_response(ans, lang_key)
        response = (
            formatted +
            f"\n\n<hr><sub>⏱ {elapsed:.1f}s | model: <code>{model_id}</code> "
            f"({DEVICE.upper()}) | agentic · web search + code · memory: "
            f"{'on (' + str(turn_count) + ' turn(s))' if use_memory else 'off'}</sub>"
        )
    except Exception as e:
        import traceback
        response = f"❌ {e}\n\n{traceback.format_exc()}"
    history.append({"role": "assistant", "content": response})
    yield history, ""


def chat_general(user_message: str, history: list, model_label: str,
                 use_agentic: bool = False, use_memory: bool = True,
                 lang_key: str = "kh",
                 max_steps: Optional[int] = None,
                 execution_timeout: Optional[int] = None,
                 use_tool_calling: bool = True):
    """General Chat entry point. Dispatches to:

    - use_agentic=False (default, unchanged behaviour): one direct LLM
      call, no tools — see chat_general_direct().
    - use_agentic=True: a CodeAgent with web-search/webpage tools decides
      for itself whether to look things up — see chat_general_agentic().
      Same reliability caveat as agentic RAG Chat: works best with
      capable models (roughly Gemma-4-E4B and above); small models may never
      call a tool at all.

    `use_memory` controls the "🧠 Conversation Memory" checkbox: whether
    prior turns in this conversation are remembered (direct path) or kept
    in the CodeAgent's own memory (agentic path). Memory is never
    persisted to disk either way — see agent_memory.py.

    A GENERATOR (via `yield from`): both branches are generators
    themselves (chat_general_direct() yields once; chat_general_agentic()
    yields once per live agent step — see agent_streaming.py), so callers
    (ui.py) always iterate this the same way regardless of which mode is
    selected, rather than needing to special-case "does this return a
    generator or a plain tuple".
    """
    if use_agentic:
        yield from chat_general_agentic(user_message, history, model_label, use_memory, lang_key,
                                         max_steps=max_steps, execution_timeout=execution_timeout,
                                         use_tool_calling=use_tool_calling)
    else:
        yield from chat_general_direct(user_message, history, model_label, use_memory, lang_key)


def chat_rag_direct(user_message: str, history: list, model_label: str, use_memory: bool = True,
                    theme: str = "", subtheme: str = "", lang_key: str = "kh"):
    """Non-agentic RAG: always retrieve context from ChromaDB first (same
    retrieval call the agentic path's `retriever` tool wraps), then hand
    that context straight to the LLM in one direct call — no CodeAgent,
    no tool-calling, no code-generation steps to parse.

    This exists because tool-calling reliability depends heavily on the
    underlying model (see rag_agent.py's caveat about Gemma-4-E2B): small
    or older models often never call the retriever tool, call it
    malformed, or burn every retry step failing to parse, and end up
    hallucinating or timing out instead of answering. Retrieval here is
    unconditional and handled entirely by the app, so even a very small
    model just has to read the provided context and answer — nothing to
    invoke, nothing to parse.
    """
    if not user_message.strip():
        yield history, ""
        return
    history = history or []
    history.append({"role": "user", "content": user_message})
    model_id = mr.MODEL_OPTIONS.get(model_label, mr.DEFAULT_LLM_MODEL)
    try:
        context, sources = kb.retrieve_context(user_message, theme, subtheme)
        if not context:
            ans = rag_agent.NOTHING_FOUND_MESSAGE
            formatted = format_llm_response(ans, lang_key)
            response = (
                formatted +
                f"\n\n<hr><sub>model: <code>{model_id}</code> ({DEVICE.upper()}) "
                f"| direct RAG (no relevant context found)</sub>"
            )
        else:
            system = _lang_instruction(lang_key) + (
                "You are a strict retrieval-augmented assistant. Answer the "
                "user's question using ONLY the context below, which was "
                "retrieved from the user's own indexed knowledge base. Never "
                "use your own general knowledge or training data, even if you "
                "believe you know the answer. If the context doesn't contain "
                "the answer, say clearly that the knowledge base doesn't "
                "contain this information — do not guess or fill the gap "
                "yourself.\n\n"
                "CITATION REQUIREMENT: each context chunk below is tagged "
                "with its source in brackets, e.g. '[report.pdf]'. Cite that "
                "exact bracketed tag in-text immediately after every claim "
                "you make from it, and finish your answer with a "
                "'### References' section listing every distinct source you "
                "cited.\n\n"
                f"Context:\n{context}"
            )
            # Memory: same short-term conversation recall as General Chat's
            # direct path, so a follow-up question can refer back to what
            # was just discussed, on top of the always-fresh retrieval above.
            # Skipped entirely when the "🧠 Conversation Memory" checkbox is off.
            memory_messages = _recent_memory_messages(history[:-1]) if use_memory else []
            # See chat_general_direct()'s matching comment: without this,
            # instruct-tuned models tend to give a canned "I don't have
            # memory" disclaimer to meta-questions about earlier turns,
            # even though memory_messages genuinely is sent as real prior
            # turns below. Only added when there's actual history to
            # reference.
            if memory_messages:
                system += (
                    "\n\nThe earlier turns of this conversation shown below "
                    "ARE genuinely visible to you in full — they are not "
                    "hidden or inaccessible. If asked what was said earlier "
                    "in this conversation, or a follow-up refers back to "
                    "something mentioned before, look at those earlier turns "
                    "and answer from them directly (this is separate from — "
                    "and does not override — the knowledge-base-only rule "
                    "above for actual content questions). Do NOT claim you "
                    "lack memory or cannot see prior messages — you can."
                )
            # See chat_general_direct()'s matching comment — a no-op
            # unless the "🧠 Enable Model Reasoning" toggle is off.
            user_message_final = mr.apply_reasoning_toggle(user_message)
            ans, elapsed = models._call_llm(model_id, system, user_message_final, history=memory_messages)
            # Guaranteed-accurate references list, appended regardless of
            # whether the model remembered its own in-text citations/
            # "### References" section — built from the sources ChromaDB
            # ACTUALLY returned for this query (not trusting the model to
            # report them correctly itself).
            # Strip any "### References" the model may have written
            # (the system prompt asks it to) before adding the verified one
            ans = general_agent.strip_trailing_references_section(ans)
            if sources:
                refs = "\n".join(f"- {s}" for s in sorted(sources))
                ans += f"\n\n---\n**📚 Sources retrieved this turn:**\n{refs}"
            formatted = format_llm_response(ans, lang_key)
            response = (
                formatted +
                f"\n\n<hr><sub>⏱ {elapsed:.1f}s | model: <code>{model_id}</code> "
                f"({DEVICE.upper()}) | direct RAG</sub>"
            )
    except Exception as e:
        import traceback
        response = f"❌ {e}\n\n{traceback.format_exc()}"
    history.append({"role": "assistant", "content": response})
    yield history, ""


def chat_rag(user_message: str, history: list, model_label: str, use_agentic: bool = True, use_memory: bool = True,
             theme: str = "", subtheme: str = "", max_steps: Optional[int] = None,
             lang_key: str = "kh", use_tool_calling: bool = False):
    """RAG Chat entry point. Dispatches to one of two retrieval strategies:

    - use_agentic=True (default): a smolagents CodeAgent or ToolCallingAgent
      (see rag_agent.py) decides for itself whether/when to call the
      `retriever` tool against ChromaDB — and can call it more than once
      to refine its search — before writing a final answer. Strictly
      grounded: the agent is instructed (system + per-task level) to answer
      ONLY from retrieved content, and the answer is also checked after
      the fact against the RetrieverTool's own self-tracked call/found
      counts (rag_agent.get_retriever_stats()). If it never searched, or
      searched and found nothing relevant, the answer is replaced with a
      clear "not in the knowledge base" message instead of trusting
      whatever the model wrote.

      `use_tool_calling=True` requests ToolCallingAgent (native function-
      calling API) instead of CodeAgent (code generation). Falls back to
      CodeAgent if the loaded model doesn't support native tool calls.

    - use_agentic=False: see chat_rag_direct() — always retrieves context
      first, then asks the LLM directly in one call. No tool-calling
      required, so small/older/weaker models (e.g. Gemma-4-E2B) can use RAG
      reliably too, at the cost of never refining or skipping the search.

    `use_memory` controls the "🧠 Conversation Memory" checkbox — see
    chat_general()'s docstring for what it does on each path.

    A GENERATOR (via `yield from` on the direct path; native multi-yield
    streaming on the agentic path) — see chat_general()'s matching note
    and agent_streaming.py's module docstring.
    """
    if not use_agentic:
        yield from chat_rag_direct(user_message, history, model_label, use_memory, theme, subtheme, lang_key)
        return

    if not user_message.strip():
        yield history, ""
        return
    history = history or []
    history.append({"role": "user", "content": user_message})
    model_id = mr.MODEL_OPTIONS.get(model_label, mr.DEFAULT_LLM_MODEL)
    try:
        agent = rag_agent.get_rag_agent(model_id, theme, subtheme, max_steps, use_tool_calling=use_tool_calling)
        rag_agent.reset_retriever_stats()
        task = rag_agent.build_strict_task(user_message, lang_key)
        # See chat_general_direct()'s matching comment — a no-op unless
        # the "🧠 Enable Model Reasoning" toggle is off.
        task = mr.apply_reasoning_toggle(task)

        t0     = time.time()
        # reset=False keeps this CodeAgent's memory across turns — see
        # https://huggingface.co/docs/smolagents/tutorials/memory — capped
        # right after via agent_memory.cap_agent_memory() so the prompt
        # doesn't grow without bound over a long conversation. reset=True
        # (memory checkbox off) makes every message stateless instead.
        # Live step streaming — see chat_general_agentic()'s matching
        # comment / agent_streaming.stream_agent_steps()'s docstring.
        result = None
        for step_msg, is_final, final_output in agent_streaming.stream_agent_steps(agent, task, reset=not use_memory):
            if not is_final:
                if step_msg is not None:
                    history.append(step_msg)
                    yield history, ""
                continue
            result = final_output
        if use_memory:
            agent_memory.cap_agent_memory(agent, max_turns=AGENTIC_MEMORY_TURNS)
        elapsed = time.time() - t0

        call_count, found_count, sources_used = rag_agent.get_retriever_stats()
        if call_count == 0:
            ans = rag_agent.NEVER_SEARCHED_MESSAGE
        elif found_count == 0:
            ans = rag_agent.NOTHING_FOUND_MESSAGE
        else:
            ans = str(result)
            # Strip the model's own (unverified) "### References" section
            # before appending the guaranteed-accurate one from the tool's
            # own self-tracked sources — same verified-sources approach
            # general_agentic and deep_research already use. Without this
            # strip, references appear twice: once from the model (which
            # may hallucinate or omit sources) and once from the tool's
            # actual tracked data.
            ans = general_agent.strip_trailing_references_section(ans)
            if sources_used:
                refs = "\n".join(f"- {s}" for s in sorted(sources_used))
                ans += f"\n\n---\n**📚 Sources retrieved this turn:**\n{refs}"

        formatted = format_llm_response(ans, lang_key)
        response = (
            formatted +
            f"\n\n<hr><sub>⏱ {elapsed:.1f}s | model: <code>{model_id}</code> "
            f"({DEVICE.upper()}) | agentic RAG · strict grounding "
            f"(searched {call_count}x) · memory: {'on' if use_memory else 'off'}</sub>"
        )
    except Exception as e:
        import traceback
        response = f"❌ {e}\n\n{traceback.format_exc()}"
    history.append({"role": "assistant", "content": response})
    yield history, ""


def chat_vision(user_message: str, uploaded_image, history: list,
                vlm_label: str, use_visual_rag: bool, use_memory: bool = True,
                lang_key: str = "kh", mmproj_label: str = ""):
    if not user_message.strip() and uploaded_image is None:
        return history, None
    history = history or []
    history.append({"role": "user", "content": user_message or "(image)"})
    vlm_id = mr.VLM_OPTIONS.get(vlm_label, mr.DEFAULT_VLM_MODEL)
    mmproj_path = mr.GGUF_VLM_MMPROJ_MAP.get(vlm_id) if not mmproj_label else None
    if mmproj_label and vlm_id:
        candidates = mr.get_mmproj_choices_for_vlm(vlm_id)
        mmproj_path = candidates.get(mmproj_label) or mmproj_path
    try:
        # Pre-load VLM outside vlm_answer so errors surface cleanly
        models.get_vlm(vlm_id, mmproj_path=mmproj_path)
        pil_images = []
        if uploaded_image is not None:
            if isinstance(uploaded_image, Image.Image):
                pil_images.append(uploaded_image)
            elif isinstance(uploaded_image, str):
                pil_images.append(Image.open(uploaded_image).convert("RGB"))
        if use_visual_rag and user_message:
            pil_images.extend(kb.visual_retrieve(user_message, top_k=2))
        context, _ = kb.retrieve_context(user_message) if user_message else ("", [])
        # Memory: Vision Chat has no smolagents CodeAgent (and images
        # aren't replayed turn-to-turn to keep prompts small), but folding
        # the last couple of Q&A exchanges' *text* in as extra context lets
        # simple follow-ups ("what color is it?" after "what's in the
        # photo?") still make sense without re-uploading the image.
        recent = _recent_memory_messages(history[:-1], max_turns=3) if use_memory else []
        if recent:
            convo = "\n".join(f"{t['role']}: {t['content']}" for t in recent)
            context = f"Recent conversation:\n{convo}\n\n{context}" if context else f"Recent conversation:\n{convo}"
        t0  = time.time()
        ans = models.vlm_answer(user_message, pil_images, context=context, model_id=vlm_id, mmproj_path=mmproj_path, lang_key=lang_key)
        elapsed  = time.time() - t0
        response = (f"{ans}\n\n*⏱ {elapsed:.1f}s | VLM: `{vlm_id}` ({DEVICE.upper()})"
                    f" | images: {len(pil_images)}*")
    except Exception as e:
        import traceback
        response = f"❌ {e}\n\n{traceback.format_exc()}"
    history.append({"role": "assistant", "content": response})
    return history, None


def chat_deep_research(user_message: str, history: list, model_label: str, use_memory: bool = True, use_playwright: bool = False, headless: bool = True, manager_max_steps: int = 12, search_max_steps: int = 6, timeout: int = 90, lang_key: str = "kh", use_tool_calling: bool = True):
    """Deep Research tab: a two-agent smolagents setup modeled on
    HuggingFace's own open_deep_research example (see
    https://github.com/huggingface/smolagents/tree/main/examples/open_deep_research)
    — a manager CodeAgent that periodically re-plans (`planning_interval`)
    and delegates focused sub-questions to a dedicated `web_search_agent`
    sub-agent (see deep_research_agent.py), rather than one agent doing
    everything itself the way General Chat's agentic mode does. Produces
    a longer, structured Markdown report with a verified sources list
    instead of a short conversational answer — expect this to take
    noticeably longer per turn than General/RAG Chat.

    Same reliability caveat as every agentic tab in this app: needs a
    genuinely capable model (roughly Gemma-4-E4B and above) — the manager
    also has to correctly invoke a SUB-AGENT (not just a tool) and
    periodically re-plan, which is a harder ask than General Chat's
    single-agent tool use.

    `use_memory` controls the "🧠 Conversation Memory (Experimental)"
    checkbox — see chat_general()'s docstring for what it does; same
    RAM-only, resets-on-model-switch/Clear/restart behaviour applies here.
    """
    if not user_message.strip():
        yield history, ""
        return
    history = history or []
    history.append({"role": "user", "content": user_message})
    model_id = mr.MODEL_OPTIONS.get(model_label, mr.DEFAULT_LLM_MODEL)
    try:
        agent = deep_research_agent.get_deep_research_agent(model_id, use_playwright, headless, manager_max_steps, search_max_steps, timeout, use_tool_calling=use_tool_calling)
        deep_research_agent.reset_tool_usage()
        t0     = time.time()
        # reset=False keeps the manager's own memory (its steps include
        # every call it made to web_search_agent) across turns — same
        # smolagents pattern as every other agentic tab. Capped right
        # after so a long research conversation doesn't grow the prompt
        # unboundedly turn after turn.
        #
        # Wrapped with a per-task citation reminder (NOT just the raw
        # user_message) for the same reason as chat_general_agentic()
        # above: DEEP_RESEARCH_INSTRUCTIONS' citation requirement only
        # reaches the manager if this smolagents version's CodeAgent
        # accepts `instructions=` — on a version where it doesn't, this
        # is the only place the requirement is ever stated.
        task = deep_research_agent.build_task_with_citation_reminder(user_message, lang_key)
        # See chat_general_direct()'s matching comment — a no-op unless
        # the "🧠 Enable Model Reasoning" toggle is off. This is the tab
        # most likely to benefit: a heavy thinking-tuned manager model
        # (e.g. Gemma-4-26B-A4B) burning its whole MAX_NEW_TOKENS budget
        # on internal reasoning is exactly what produces the "Executing
        # parsed code:" steps with an EMPTY body / Out: None seen in
        # practice on this tab.
        task = mr.apply_reasoning_toggle(task)
        # Live step streaming — the manager's OWN steps stream (its
        # thought/code, and each call it makes to the `web_search_agent`
        # sub-agent shows up as a tool-call-shaped line with that call's
        # returned text as the "output"). The search sub-agent's own
        # internal steps don't stream separately — deep_research_agent.py's
        # managed_agents mechanism runs it as one synchronous Python call
        # from inside the manager's executed code, same as smolagents
        # itself — but seeing each delegated sub-question and what it
        # found, live, is already a large improvement over a single
        # "thinking…" line for however many minutes the whole multi-step
        # research run takes (see MANAGER_DEFAULT_MAX_STEPS's comment in
        # deep_research_agent.py).
        result = None
        for step_msg, is_final, final_output in agent_streaming.stream_agent_steps(agent, task, reset=not use_memory):
            if not is_final:
                if step_msg is not None:
                    history.append(step_msg)
                    yield history, ""
                continue
            result = final_output
        if use_memory:
            agent_memory.cap_agent_memory(agent, max_turns=DEEP_RESEARCH_MEMORY_TURNS)
        elapsed = time.time() - t0

        turn_count = sum(1 for s in agent.memory.steps if s.__class__.__name__ == "TaskStep")
        ans = str(result)
        # Same verified-sources approach as General Chat's agentic mode —
        # reuses general_agent's own citation-checking helpers rather than
        # duplicating that logic, since they're generic string/list
        # functions with no dependency on general_agent's own tool state.
        queries, urls, links = deep_research_agent.get_tool_usage()
        used_sources = general_agent.resolve_actually_used_sources(ans, urls, links)
        ans = general_agent.strip_trailing_references_section(ans)
        if used_sources:
            ref_lines = ["**🔗 Sources used for this report:**"]
            ref_lines.extend(
                f"- {url}" if title == url else f"- [{title}]({url})"
                for title, url in used_sources
            )
            ans += "\n\n---\n" + "\n".join(ref_lines)
        formatted = format_llm_response(ans, lang_key)
        response = (
            formatted +
            f"\n\n<hr><sub>⏱ {elapsed:.1f}s | model: <code>{model_id}</code> "
            f"({DEVICE.upper()}) | deep research · manager + web-search sub-agent · "
            f"memory: {'on (' + str(turn_count) + ' turn(s))' if use_memory else 'off'}</sub>"
        )
    except Exception as e:
        import traceback
        response = f"❌ {e}\n\n{traceback.format_exc()}"
    history.append({"role": "assistant", "content": response})
    yield history, ""
