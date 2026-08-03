"""
agent_streaming.py — Shared live step-streaming for every smolagents
CodeAgent-driven chat handler in this app (General Chat / RAG Chat /
Deep Research / Data Analysis — see chat.py / data_analysis.py).

smolagents' own GradioUI (see smolagents' `gradio_ui.py` /
`stream_to_gradio()`) streams each ActionStep/PlanningStep live by
calling `agent.run(task, stream=True, ...)` and iterating the returned
generator, rather than blocking silently until the whole run finishes —
the LAST item that generator yields is the plain final answer itself
(not wrapped in a step object). This module adapts that exact pattern to
this app's own chat history shape (plain {"role", "content"} dicts
appended to a Gradio Chatbot's history), so every agentic tab here
(chat.py's chat_general_agentic / chat_rag / chat_deep_research, and
data_analysis.py's run_data_analysis()) can show live progress instead
of a single frozen "thinking…" bubble for however long a multi-step run
takes.

Public contract
----------------
stream_agent_steps(agent, task, reset=True) is a generator yielding
(step_msg, is_final, final_output) 3-tuples:

  - While the run is still in progress: `step_msg` is a plain
    {"role": "assistant", "content": "..."} dict describing the step
    that just happened (or None if that particular step produced
    nothing worth showing), `is_final` is False, and `final_output` is
    None. Callers append step_msg to their chat history and yield.

  - On the LAST item: `step_msg` is None, `is_final` is True, and
    `final_output` holds the agent's actual final answer (whatever a
    plain, non-streaming `agent.run()` call would have returned) —
    callers use this as the "real" result to post-process (citations,
    formatting, etc.) instead of trying to parse it back out of the
    step stream.

Every call site in this app follows the same loop shape:

    result = None
    for step_msg, is_final, final_output in agent_streaming.stream_agent_steps(agent, task, reset=not use_memory):
        if not is_final:
            if step_msg is not None:
                history.append(step_msg)
                yield history, ...
            continue
        result = final_output

Version compatibility
----------------------
Different smolagents releases expose live streaming slightly
differently. This module tries, in order:

  1. `agent.run(task, reset=reset, stream=True)` — the standard way to
     get a live generator of memory steps as they happen. Each yielded
     item is either a memory-step object (ActionStep / PlanningStep /
     ...) or, on the very last item, the final answer itself.
  2. If `stream=True` isn't accepted at all (raises TypeError — an
     older smolagents without streaming support), falls back to a
     single non-streaming `agent.run(task, reset=reset)` call and
     yields just ONE (None, True, result) tuple — no live steps, but
     the app still works exactly as it did before streaming existed.

Because the exact memory-step shape/attributes can also vary by
version, step formatting below is defensive: every attribute is read
with getattr(..., default) inside a try/except, so a field this
installed version doesn't have (or a totally unrecognized step type)
degrades to a shorter message — or is silently skipped — instead of
crashing the whole run.
"""

import traceback
from typing import Optional

# Best-effort import of smolagents' own memory-step classes, for a
# precise isinstance() check. Falls back to matching on the class NAME
# string (see _is_memory_step()) if this smolagents version has moved
# or renamed these — the same defensive fallback pattern general_agent.py
# / rag_agent.py already use for other smolagents version differences
# (e.g. the `code_block_tags` / `instructions` kwarg probing).
try:
    from smolagents.memory import ActionStep, PlanningStep, TaskStep, SystemPromptStep
    _MEMORY_STEP_TYPES = (ActionStep, PlanningStep, TaskStep, SystemPromptStep)
except ImportError:
    _MEMORY_STEP_TYPES = ()

_MEMORY_STEP_CLASS_NAMES = (
    "ActionStep", "PlanningStep", "TaskStep", "SystemPromptStep", "FinalAnswerStep",
)


def _patch_smolagents_code_parser():
    """Patch smolagents.utils.parse_code_blobs and smolagents.utils.parse_json_blob
    with smart fallback parsers.
    Handles:
    1. CodeAgent: Plain text final answers without ```python ... ``` code block tags.
    2. ToolCallingAgent: Model tool calls output in call:tool_name{key: val} format
       or unquoted JSON key format (common with Gemma-4 and local LLMs).
    """
    try:
        import json
        import re
        import smolagents.utils as su
        if getattr(su, "_smart_parser_installed", False):
            return
        _orig_parse_code_blobs = su.parse_code_blobs
        _orig_parse_json_blob = su.parse_json_blob

        def _smart_parse_code_blobs(text: str, code_block_tags: tuple) -> str:
            try:
                return _orig_parse_code_blobs(text, code_block_tags)
            except Exception:
                if not text or not isinstance(text, str):
                    return 'final_answer("")'
                clean_text = text.strip()
                if "final_answer(" in clean_text:
                    m = re.search(r"final_answer\(.*?\)", clean_text, re.DOTALL)
                    if m:
                        return m.group(0)
                if "Final Answer:" in clean_text:
                    clean_text = clean_text.split("Final Answer:", 1)[1].strip()
                elif "final_answer:" in clean_text.lower():
                    clean_text = re.sub(r"(?i)final_answer:\s*", "", clean_text).strip()

                escaped = clean_text.replace('"""', '\\"\\"\\"')
                return f'final_answer("""{escaped}""")'

        def _smart_parse_json_blob(json_blob: str) -> tuple:
            try:
                return _orig_parse_json_blob(json_blob)
            except Exception as orig_err:
                if not json_blob or not isinstance(json_blob, str):
                    raise orig_err

                # Match call:tool_name{key: val} format used by Gemma-4 and local LLMs
                call_match = re.search(r'call:([a-zA-Z0-9_]+)\s*\{(.*)\}', json_blob, re.DOTALL)
                if call_match:
                    tool_name = call_match.group(1).strip()
                    args_str = call_match.group(2).strip()
                    args_dict = {}
                    if args_str:
                        try:
                            args_dict = json.loads("{" + args_str + "}", strict=False)
                        except Exception:
                            pairs = re.findall(r'([a-zA-Z0-9_]+)\s*:\s*(".*?"|\'.*?\'|[^,}]+)', args_str, re.DOTALL)
                            for k, v in pairs:
                                v = v.strip().strip('"\'')
                                args_dict[k] = v

                    res_dict = {
                        "name": tool_name,
                        "arguments": args_dict,
                        "action": tool_name,
                        "action_input": args_dict,
                    }
                    return res_dict, json_blob[:call_match.start()]

                # Fallback for plain text model outputs without any JSON blob
                clean_text = json_blob.strip()
                if clean_text:
                    if "Final Answer:" in clean_text:
                        clean_text = clean_text.split("Final Answer:", 1)[1].strip()
                    elif "final_answer:" in clean_text.lower():
                        clean_text = re.sub(r"(?i)final_answer:\s*", "", clean_text).strip()

                    res_dict = {
                        "name": "final_answer",
                        "arguments": {"answer": clean_text},
                        "action": "final_answer",
                        "action_input": {"answer": clean_text},
                    }
                    return res_dict, ""

                raise orig_err

        su.parse_code_blobs = _smart_parse_code_blobs
        su.parse_json_blob = _smart_parse_json_blob

        try:
            import smolagents.models as sm
            sm.parse_json_blob = _smart_parse_json_blob
        except Exception:
            pass

        try:
            import smolagents.agents as sa
            sa.parse_json_blob = _smart_parse_json_blob
        except Exception:
            pass

        su._smart_parser_installed = True
    except Exception:
        pass


_patch_smolagents_code_parser()


def _truncate(text, limit: int = 1500) -> str:
    text = str(text or "")
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n…(truncated)"


def _format_tool_calls(tool_calls) -> str:
    if not tool_calls:
        return ""
    lines = []
    for tc in tool_calls:
        name = (
            getattr(tc, "name", None)
            or (tc.get("name") if isinstance(tc, dict) else None)
            or "tool"
        )
        args = getattr(tc, "arguments", None)
        if args is None and isinstance(tc, dict):
            args = tc.get("arguments")
        args_str = str(args) if args is not None else ""
        if len(args_str) > 800:
            args_str = args_str[:800] + "…(truncated)"
        lines.append(
            f'<div class="tool-header">🛠️ <b>Tool Execution:</b> <code>{name}</code></div>\n'
            f'<pre class="obs-code"><code>{args_str}</code></pre>'
        )
    return "\n".join(lines)


def _format_step(step) -> Optional[str]:
    """Best-effort human-readable rendition of one smolagents memory step
    (ActionStep / PlanningStep / ...) formatted with distinct step log styling.
    """
    try:
        cls_name = step.__class__.__name__

        if cls_name == "PlanningStep":
            plan = getattr(step, "plan", None) or getattr(step, "facts", None)
            if not plan:
                return None
            return (
                '<details class="agent-step-details" open>\n'
                '<summary class="agent-step-summary">🗺️ <b>Planning & Strategy Step</b></summary>\n'
                '<div class="agent-log-block">\n'
                f'<div class="agent-plan-box"><div class="plan-header">🗺️ Strategy</div>{_truncate(plan)}</div>\n'
                '</div>\n</details>'
            )

        if cls_name in ("TaskStep", "SystemPromptStep"):
            return None

        step_number = getattr(step, "step_number", None)
        header_text = f"⚙️ Step {step_number} — Execution Log & Tools" if step_number is not None else "⚙️ Agent Step — Execution Log"

        parts = []

        model_output = getattr(step, "model_output", None)
        if model_output:
            cleaned_out = _truncate(model_output)
            parts.append(f'<div class="agent-thought-box"><b>🧠 Reasoning:</b>\n{cleaned_out}</div>')

        tool_calls = getattr(step, "tool_calls", None)
        tc_str = _format_tool_calls(tool_calls)
        if tc_str:
            parts.append(f'<div class="agent-tool-box">{tc_str}</div>')

        observations = getattr(step, "observations", None)
        if observations:
            obs_text = _truncate(observations, 1200)
            parts.append(
                f'<div class="agent-obs-box">\n'
                f'<div class="obs-header">📝 Execution Logs & Terminal Output</div>\n'
                f'<pre class="obs-code"><code>{obs_text}</code></pre>\n'
                '</div>'
            )

        error = getattr(step, "error", None)
        if error:
            parts.append(
                f'<div class="agent-err-box">\n'
                f'<div class="err-header">⚠️ Execution Error</div>\n'
                f'<div>{_truncate(str(error), 800)}</div>\n'
                '</div>'
            )

        if not parts:
            return None

        body_html = "\n".join(parts)
        return (
            f'<details class="agent-step-details" open>\n'
            f'<summary class="agent-step-summary">{header_text}</summary>\n'
            f'<div class="agent-log-block">\n{body_html}\n</div>\n'
            '</details>'
        )
    except Exception:
        # Never let a formatting glitch break the whole streamed run
        return None


def _is_memory_step(item) -> bool:
    """Distinguish a smolagents memory-step object (ActionStep,
    PlanningStep, ...) from the final answer itself. smolagents' own
    streaming run yields the plain final answer, UNWRAPPED, as the very
    last item — so anything that isn't recognizably a memory step is
    treated as the final answer by the caller (see stream_agent_steps()).
    """
    if _MEMORY_STEP_TYPES and isinstance(item, _MEMORY_STEP_TYPES):
        return True
    return item.__class__.__name__ in _MEMORY_STEP_CLASS_NAMES


def stream_agent_steps(agent, task: str, reset: bool = True):
    """Run `agent` on `task`, yielding live steps as they happen.

    See this module's docstring for the full (step_msg, is_final,
    final_output) contract every caller in this app relies on.
    """
    try:
        run_result = agent.run(task, reset=reset, stream=True)
    except TypeError:
        # Installed smolagents version doesn't accept stream= at all —
        # fall back to a single blocking call. No live steps, but the
        # caller still gets a real final answer.
        try:
            result = agent.run(task, reset=reset)
        except Exception as e:
            err_msg = {"role": "assistant", "content": f"❌ {e}\n\n{traceback.format_exc()}"}
            yield err_msg, True, f"❌ {e}"
            return
        yield None, True, result
        return

    # Tracks the most recent item that did NOT look like a full memory
    # step (ActionStep/PlanningStep/...). smolagents' own convention is
    # that the plain final answer is the last thing the stream yields
    # (see module docstring) — but some smolagents versions ALSO stream
    # finer-grained intermediate objects mid-run (e.g. raw ToolCall
    # objects, or streamed text-delta chunks) that are NOT the final
    # answer either, just noise to skip rather than display. A single
    # item's type alone can't tell us which case we're in — only once
    # the generator is fully exhausted do we know "the very last thing
    # it ever yielded" is genuinely the final answer, rather than a
    # preview of a step still to come. Finalizing on the FIRST
    # unrecognized item (an earlier version of this function did this)
    # incorrectly ended runs the moment ANY such intermediate object
    # appeared — sometimes after a single step — producing garbage like
    # a raw "ToolCall(name=..., arguments=...)" repr as the "final
    # answer" instead of letting the agent actually finish researching.
    candidate_final = None

    last_item = None
    try:
        try:
            for item in run_result:
                last_item = item

                # FinalAnswerStep (present in some newer smolagents
                # versions) is an EXPLICIT, unambiguous signal — it wraps
                # the actual completed final answer, so it's safe to act
                # on immediately instead of waiting for the generator to
                # end.
                if item.__class__.__name__ == "FinalAnswerStep":
                    final_answer = getattr(item, "final_answer", None)
                    if final_answer is None:
                        final_answer = getattr(item, "output", item)
                    yield None, True, final_answer
                    return

                if _is_memory_step(item):
                    msg_text = _format_step(item)
                    if msg_text is not None:
                        yield {"role": "assistant", "content": msg_text}, False, None
                    # A genuine step just happened — the agent is clearly
                    # still going, so any unrecognized "final answer
                    # candidate" picked up right before this was just
                    # noise from an earlier in-progress step, not the
                    # real final answer. Discard it.
                    candidate_final = None
                    continue

                # Not a recognized memory-step type. Could be the plain
                # final answer (the normal end-of-stream case), or it
                # could be an intermediate delta/tool-call object some
                # smolagents versions stream mid-step. Don't decide yet —
                # remember it and keep iterating; see candidate_final's
                # declaration above for why.
                candidate_final = item

            # The generator is genuinely exhausted now — whatever the
            # LAST unrecognized item was (if any) is the real final
            # answer.
            if candidate_final is not None:
                yield None, True, candidate_final
            elif last_item is not None:
                # Every single item the whole run ever yielded was a
                # recognized memory step (no bare final answer ever
                # appeared, unusual but possible on some versions) —
                # fall back to that last step's own text rather than
                # yielding nothing.
                yield None, True, (_format_step(last_item) or "")
            else:
                yield None, True, ""
        except Exception as e:
            err_msg = {"role": "assistant", "content": f"❌ {e}\n\n{traceback.format_exc()}"}
            yield err_msg, True, f"❌ {e}"
            return
    finally:
        # See this function's matching comment above the `try:` this is
        # attached to (module docstring section on version compatibility)
        # — proactively close the underlying smolagents step generator
        # ourselves, synchronously, rather than leaving it for CPython's
        # garbage collector to close at some later, unpredictable point.
        # If `run_result` was abandoned mid-iteration (an early `return`
        # above, after an error or once the final answer arrived), Python
        # will eventually GC it and call its own `.close()`, sending it a
        # GeneratorExit. Some smolagents versions' internal
        # `MultiStepAgent._run_stream` generator doesn't handle that
        # cleanly — it keeps yielding instead of stopping — which raises
        # "RuntimeError: generator ignored GeneratorExit", printed by the
        # interpreter as a scary but harmless "Exception ignored in: ..."
        # warning during cleanup (it does not propagate into this app's
        # own control flow or crash the run — the real answer above has
        # already been yielded by this point). Closing it here instead,
        # while we still hold a live reference to it, and swallowing that
        # specific error, prevents the noisy warning entirely.
        try:
            run_result.close()
        except RuntimeError:
            pass
        except Exception:
            pass
