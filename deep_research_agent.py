"""
deep_research_agent.py — Agentic "Deep Research" via a two-agent smolagents
setup, modeled on HuggingFace's own open_deep_research example:
https://github.com/huggingface/smolagents/tree/main/examples/open_deep_research

That example uses a MANAGER agent that plans out a research task and
delegates focused sub-questions to a dedicated browser/search agent
(there: a `ToolCallingAgent` wrapping `GoogleSearchTool` + page-reading
tools, requiring a paid search API key and typically a hosted model like
`o1`). This app has neither a search API key nor a hosted-model
requirement, so the same manager+search-agent shape is rebuilt here using
what's already available:

  - The manager is a `CodeAgent` with NO tools of its own except the
    search sub-agent (passed via `managed_agents=`, which smolagents
    exposes to the manager as a callable — `web_search_agent(task="...")`
    — same as the real example's manager calling its own sub-agent).
  - `planning_interval` makes the manager periodically stop and
    re-evaluate its plan against what it's learned so far — the
    characteristic "deep" part of deep research, as opposed to
    general_agent.py's single-pass agentic chat.
  - The search sub-agent reuses general_agent.py's own
    TrackedDuckDuckGoSearchTool / TrackedVisitWebpageTool (free,
    API-key-free DuckDuckGo search + page reading — already proven out
    by General Chat's agentic mode) instead of GoogleSearchTool, and its
    citation-tracking/verification helpers (resolve_actually_used_sources
    etc.) are reused as-is from general_agent.py rather than duplicated.

Same reliability caveat as every other agentic tab in this app: this
needs a genuinely capable model to work well — small/local models can
struggle even more here than in General Chat's agentic mode, since a
manager also has to correctly invoke a SUB-AGENT (not just a tool) and
periodically re-plan. Expect this to work best on Gemma-4-E4B and above,
same guidance as the other agentic tabs.
"""

import inspect
import re
import threading
from typing import Optional

from smolagents import CodeAgent, SpeechToTextTool, Tool, ToolCallingAgent, WikipediaSearchTool, UserInputTool

import general_agent
import model_registry as mr
import models

try:
    import playwright_search_tool
    _playwright_available = True
except ImportError:
    _playwright_available = False

if _playwright_available:
    class TrackedPlaywrightDuckDuckGoSearchTool(playwright_search_tool.PlaywrightDuckDuckGoSearchTool):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.queries_run = []
            self.result_links = []

        def forward(self, query: str) -> str:
            self.queries_run.append(query)
            result = super().forward(query)
            import re
            _MARKDOWN_LINK_RE = re.compile(r'\[([^\]]+)\]\((https?://[^\s\)]+)\)')
            for title, url in _MARKDOWN_LINK_RE.findall(result or ""):
                pair = (title.strip(), url.strip())
                if pair not in self.result_links:
                    self.result_links.append(pair)
            return result

    class TrackedPlaywrightGoogleSearchTool(playwright_search_tool.PlaywrightGoogleSearchTool):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.queries_run = []
            self.result_links = []

        def forward(self, query: str, filter_year: str | None = None) -> str:
            self.queries_run.append(query)
            result = super().forward(query, filter_year)
            import re
            _MARKDOWN_LINK_RE = re.compile(r'\[([^\]]+)\]\((https?://[^\s\)]+)\)')
            for title, url in _MARKDOWN_LINK_RE.findall(result or ""):
                pair = (title.strip(), url.strip())
                if pair not in self.result_links:
                    self.result_links.append(pair)
            return result

    class TrackedPlaywrightVisitPageTool(playwright_search_tool.PlaywrightVisitPageTool):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.urls_visited = []

        def forward(self, url: str) -> str:
            self.urls_visited.append(url)
            return super().forward(url)


class PlaywrightTextInspectorTool(Tool):
    name = "playwright_inspect_file"
    description = (
        "Read a file from a local path or URL and return its text content. "
        "Handles .txt, .md, .html, .json, .csv, .py, and similar text formats. "
        "For PDF files use playwright_read_embedded_pdf instead. "
        "For images use playwright_visualizer instead."
    )
    inputs = {
        "file_path": {
            "type": "string",
            "description": "The local path or URL to the file to read.",
        },
    }
    output_type = "string"

    def forward(self, file_path: str) -> str:
        import mimetypes
        import requests

        file_path = file_path.strip()
        if not file_path:
            return "Error: empty file path."

        try:
            if file_path.startswith("http://") or file_path.startswith("https://"):
                resp = requests.get(file_path, timeout=30)
                resp.raise_for_status()
                content = resp.text
            else:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
        except Exception as e:
            return f"Error reading file '{file_path}': {e}"

        if len(content) > 50000:
            content = content[:50000] + "\n...[truncated at 50000 chars]"

        return f"## File: {file_path}\n\n```\n{content}\n```"


class PlaywrightVisualizerTool(Tool):
    name = "playwright_visualizer"
    description = (
        "Answer a question about an image file. Provide the local path to the image "
        "and an optional question. If no question is given, a detailed caption is returned."
    )
    inputs = {
        "image_path": {
            "type": "string",
            "description": "The local path to the image file to analyze.",
        },
        "question": {
            "type": "string",
            "description": "The question about the image. Optional — if omitted, a caption is generated.",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(self, image_path: str, question: str | None = None) -> str:
        from PIL import Image

        image_path = image_path.strip()
        if not image_path:
            return "Error: empty image path."

        try:
            pil_image = Image.open(image_path).convert("RGB")
        except Exception as e:
            return f"Error opening image '{image_path}': {e}"

        q = question or "Please describe this image in detail."
        try:
            answer = models.vlm_answer(q, [pil_image])
        except Exception as e:
            answer = f"Could not process image through VLM: {e}"

        if not question:
            answer = f"Caption for '{image_path}':\n{answer}"

        return answer


_manager_agent          = None
_manager_agent_model_id = None
_manager_agent_config   = {}
_manager_agent_lock     = threading.Lock()

# Module-level refs to the CURRENT run's tracked-tool instances (the
# search sub-agent's own tools), so chat.py can read/reset them the same
# way it does for general_agent.py's tools — see
# general_agent.TrackedDuckDuckGoSearchTool / TrackedVisitWebpageTool.
_search_tool  = None
_webpage_tool = None

# The search sub-agent answers ONE focused sub-question per call and has
# no memory of its own across calls, so it needs far fewer steps than the
# manager, which is juggling the whole research task. The manager's
# budget is larger than general_agent.py's single-agent default (12 vs
# 8) since planning + delegation calls both cost steps on top of the
# actual research.
SEARCH_AGENT_DEFAULT_MAX_STEPS = 4
MANAGER_DEFAULT_MAX_STEPS      = 12

# How often (in manager steps) the manager stops to re-plan — smolagents'
# own `planning_interval` mechanism. This is the main thing that makes
# this agent "deep" rather than a single-pass agentic chat: every few
# steps it re-reads what it has found so far and can revise its approach
# instead of blindly executing an initial plan to the end.
DEEP_RESEARCH_PLANNING_INTERVAL = 3

SEARCH_AGENT_DESCRIPTION = (
    "Give this agent ONE focused sub-question (a plain-text string) and "
    "it will search the web and read pages to answer just that "
    "sub-question, returning what it found as plain text. It has NO "
    "memory of any other call you make to it, so every call must be "
    "fully self-contained — include whatever context it needs in the "
    "sub-question itself. Call it once per sub-question; don't ask it "
    "multiple unrelated things in one call.\n\n"
    "IMPORTANT: You MUST write all code in markdown fenced blocks with the "
    "language tag, like this:\n"
    "```python\n"
    "result = web_search_agent(task=\"your question here\")\n"
    "print(result)\n"
    "```\n"
    "Do NOT use <code>...</code> tags. Do NOT write code outside of "
    "fenced blocks."
)

DEEP_RESEARCH_INSTRUCTIONS = (
    "You are a deep-research assistant. You have NO web-search tool of "
    "your own — the ONLY way to get outside information is to delegate a "
    "focused sub-question to the `web_search_agent`, by writing code "
    "like:\n"
    "```python\n"
    "result = web_search_agent(task=\"<one focused sub-question>\")\n"
    "print(result)\n"
    "```\n\n"
    "THE ONLY AGENT THAT EXISTS is `web_search_agent`. There is no other "
    "tool or function available — in particular there is no "
    "`web_search`, `visit_webpage`, `conversation_history`, or `memory` "
    "function. Never call, import, or reference anything else; it will "
    "fail with a 'Forbidden function evaluation' error and waste a step.\n\n"
    "YOUR OWN CONVERSATION HISTORY IS ALREADY VISIBLE TO YOU: earlier "
    "turns in this conversation (including your own past reports) are "
    "already included in what you can see. If a follow-up refers back to "
    "your last report, reuse what you already found instead of "
    "re-researching it from scratch — only delegate NEW sub-questions for "
    "genuinely new information.\n\n"
    "Work like this:\n"
    "1. Break the question down into 2-5 focused sub-questions that, "
    "together, cover what's needed to answer it well.\n"
    "2. Call `web_search_agent` ONCE PER SUB-QUESTION. Every call MUST be "
    "in a ```python``` block with a print() statement. Never invent or "
    "assume a fact yourself — every factual claim in your final answer "
    "must trace back to a `web_search_agent` call from this run.\n"
    "3. Re-check your plan periodically against what you've actually "
    "found: if it changes what you still need to look up, adjust instead "
    "of blindly finishing the original plan.\n"
    "4. Once you have enough to answer well, STOP calling "
    "`web_search_agent` and submit your final answer by calling the "
    "special `final_answer(...)` function — this is the ONLY way to "
    "actually end the task. Simply printing or writing the report as "
    "plain text does NOT end the run: if you don't call `final_answer`, "
    "you will be given another step and will end up starting new "
    "research rounds even though you already had a complete answer. "
    "Call it like this, with the FULL Markdown report as the argument:\n"
    "```python\n"
    "final_answer(report_text)\n"
    "```\n"
    "where `report_text` is a well-structured Markdown report: a short "
    "introduction, clearly-headed sections covering each theme/sub-"
    "question, and a brief conclusion.\n"
    "5. CITATION REQUIREMENT: cite sources in-text with a bracketed "
    "number (e.g. [1], [2]) immediately after every claim that came from "
    "a `web_search_agent` call, and the report text passed to "
    "`final_answer(...)` must end with a '### References' section "
    "listing each numbered source's title and URL, e.g.:\n"
    "### References\n"
    "[1] Page Title — https://example.com/page\n\n"
    "CRITICAL: Every step MUST be a SINGLE ```python``` fenced block "
    "containing EITHER one call to web_search_agent followed by print(), "
    "OR — once you're done researching — exactly one call to "
    "final_answer(report_text) and nothing else. Do NOT write plain text "
    "between code blocks during research steps. Do NOT use <code> tags. "
    "Do NOT omit the print() call during research steps. Do NOT forget "
    "to call final_answer(...) once you have enough information — "
    "forgetting this is the single most common mistake and it causes "
    "unnecessary extra research rounds."
)


def build_task_with_citation_reminder(user_message: str, lang_key: str = "kh") -> str:
    """Wrap the user's question with an explicit, PER-TASK reminder of the
    citation requirement AND the final_answer(...) termination
    requirement — mirrors general_agent.build_task_with_citation_reminder()
    and rag_agent.build_strict_task()'s belt-and-braces pattern exactly.

    DEEP_RESEARCH_INSTRUCTIONS (including its citation requirement AND its
    "you must call final_answer(...) to actually stop" requirement) is
    only ever attached to the manager agent if this installed smolagents
    version's CodeAgent.__init__ happens to expose an `instructions=`
    parameter — see the `if "instructions" in params:` guard in
    _build_manager_agent() below. On a version where it doesn't, the
    manager never sees either requirement at all — it never writes a
    '### References' section for
    general_agent.resolve_actually_used_sources() to parse in chat.py's
    chat_deep_research(), AND (the more disruptive gap) it never learns
    that it must call the special `final_answer(...)` tool to end the
    run — writing the report as plain printed text does NOT terminate a
    smolagents CodeAgent, so without this reminder the manager can
    finish a perfectly good report and then just keep going, re-planning
    and starting new research rounds it didn't need. Repeating both
    requirements here — in the per-call task text, which always reaches
    the manager regardless of smolagents version — closes that gap.
    """
    kh = "ឆ្លើយជាភាសាខ្មែរ។\n\n" if lang_key == "kh" else ""
    return (
        kh + f"{user_message}\n\n"
        "---\n"
        "Reminder: every factual claim in your final report that came "
        "from a web_search_agent call must be cited in-text with a "
        "bracketed number (e.g. [1]) placed right after the claim, and "
        "your final report must end with a '### References' section "
        "listing each numbered source's title and URL, e.g.:\n"
        "### References\n"
        "[1] Page Title — https://example.com/page\n\n"
        "Reminder: once your report is ready, you MUST submit it by "
        "calling final_answer(report_text) in a ```python``` code block — "
        "this is the ONLY way to end the task. Just printing or writing "
        "the report as plain text does NOT stop the run; without calling "
        "final_answer(...), you will be given another step and may end "
        "up starting unnecessary new research rounds even though your "
        "report was already complete."
    )


# ──────────────────────────────────────────────────────────────────
# Strict grounding — layer 4: a `final_answer_checks` validator on the
# MANAGER agent. See the file's revision notes: smolagents' CodeAgent
# accepts `final_answer_checks: list[Callable]`, each run against
# whatever the model passes to `final_answer(...)` before the run is
# allowed to end. Raising an exception from a check feeds that message
# back to the model as the reason its answer was rejected, and it gets
# another step to fix it — rather than a bad/incomplete report silently
# becoming the final result.
#
# Deliberately does NOT validate citation *accuracy* (e.g. "does every
# [n] have a matching reference line") — that's handled, more leniently
# and more reliably, by general_agent.resolve_actually_used_sources()
# AFTER the run completes. Only two cheap, high-value checks:
#   1. The report isn't empty/near-empty.
#   2. IF this run actually called web_search_agent, the report has a
#      '### References' heading at all (a run that never needed to
#      search isn't forced to fabricate one).
# ──────────────────────────────────────────────────────────────────
_REPORT_REFERENCES_RE = re.compile(r'#{1,6}\s*references?\b', re.IGNORECASE)
MIN_FINAL_REPORT_CHARS = 200


def _validate_final_report(final_answer, agent_memory=None) -> bool:
    """`final_answer_checks` validator for the Deep Research manager.

    Raises a plain Exception with an actionable message on rejection —
    smolagents surfaces that message back to the model as feedback for
    its next step.
    """
    text = str(final_answer or "").strip()

    if len(text) < MIN_FINAL_REPORT_CHARS:
        raise ValueError(
            f"Your final answer is only {len(text)} character(s) — too "
            f"short to be a real research report (need at least "
            f"{MIN_FINAL_REPORT_CHARS}). Write a complete Markdown report "
            "(a short introduction, a clearly-headed section per "
            "sub-question you researched, and a brief conclusion), then "
            "call final_answer(report_text) again with the FULL report "
            "text as the argument."
        )

    searched_this_run = bool(_search_tool is not None and _search_tool.queries_run)
    if searched_this_run and not _REPORT_REFERENCES_RE.search(text):
        raise ValueError(
            "You called web_search_agent during this run, but your final "
            "report has no '### References' section. Every claim drawn "
            "from a web_search_agent call must be cited in-text with a "
            "bracketed number (e.g. [1]) right after the claim, and the "
            "report must end with a section like:\n"
            "### References\n"
            "[1] Page Title — https://example.com/page\n\n"
            "Add the References section (listing every source you "
            "actually used) and call final_answer(report_text) again with "
            "the FULL corrected report."
        )

    return True


def _build_search_agent(llm, model_id: str = "", use_playwright: bool = False, headless: bool = True, max_steps: Optional[int] = None, timeout: Optional[int] = None):
    global _search_tool, _webpage_tool
    
    tools = []
    if use_playwright and _playwright_available:
        _search_tool = TrackedPlaywrightDuckDuckGoSearchTool(headless=headless)
        _webpage_tool = TrackedPlaywrightVisitPageTool(headless=headless)
        tools = [
            _search_tool,
            TrackedPlaywrightGoogleSearchTool(headless=headless),
            _webpage_tool,
            playwright_search_tool.PlaywrightExtractLegalDocumentLinksTool(headless=headless),
            playwright_search_tool.PlaywrightReadEmbeddedPdfTool(),
            playwright_search_tool.PlaywrightPageDownTool(),
            playwright_search_tool.PlaywrightPageUpTool(),
            playwright_search_tool.PlaywrightFindOnPageTool(),
            playwright_search_tool.PlaywrightFindNextTool(),
            playwright_search_tool.PlaywrightArchiveSearchTool(),
            SpeechToTextTool(),
            WikipediaSearchTool(),
            UserInputTool(),
            PlaywrightTextInspectorTool(),
            PlaywrightVisualizerTool(),
        ]
        desc = (
            "Give this agent ONE focused sub-question (a plain-text string) and "
            "it will search the web using Playwright headless browser tools and read pages to answer just that "
            "sub-question, returning what it found as plain text. It has NO "
            "memory of any other call you make to it, so every call must be "
            "fully self-contained — include whatever context it needs in the "
            "sub-question itself. Call it once per sub-question; don't ask it "
            "multiple unrelated things in one call."
        )
    else:
        _search_tool  = general_agent.TrackedDuckDuckGoSearchTool()
        _webpage_tool = general_agent.TrackedVisitWebpageTool()
        tools = [_search_tool, _webpage_tool]
        desc = SEARCH_AGENT_DESCRIPTION

    final_max_steps = max_steps if max_steps is not None else mr.get_max_steps_for_model(model_id, SEARCH_AGENT_DEFAULT_MAX_STEPS)
    kwargs = dict(
        model=llm,
        tools=tools,
        max_steps=final_max_steps,
        verbosity_level=1,
        name="web_search_agent",
        description=desc,
        planning_interval=4,
        provide_run_summary=True,
    )
    try:
        params = inspect.signature(ToolCallingAgent.__init__).parameters
        if "instructions" in params:
            if use_playwright and _playwright_available:
                kwargs["instructions"] = (
                    "You are a focused web search agent using real browser "
                    "(Playwright) tools — none of these tools use a paid API or "
                    "require an API key. Your tools are:\n\n"
                    "=== Search & Browse ===\n"
                    "  - `playwright_duckduckgo_search(query=\"...\")` — your PRIMARY "
                    "search tool. Use this first for almost every search.\n"
                    "  - `playwright_google_search(query=\"...\", filter_year=\"...\")` "
                    "— the FALLBACK search tool (queries Google via a real browser). "
                    "filter_year is optional. Use this only if "
                    "`playwright_duckduckgo_search` comes back empty, or the topic "
                    "needs Google's broader index.\n"
                    "  - `playwright_visit_page(url=\"...\")` — opens a URL and returns "
                    "its visible text plus every link found on it (note: it is named "
                    "`playwright_visit_page`, NOT `visit_webpage` — that name does not "
                    "exist in this mode).\n"
                    "  - `playwright_extract_legal_document_links(url=\"...\", "
                    "topic_keywords=\"...\")` — opens a listing/index page and returns "
                    "its links ranked by relevance to topic_keywords. Use this BEFORE "
                    "opening individual candidate pages one by one.\n"
                    "  - `playwright_read_embedded_pdf(url=\"...\")` — opens a page, "
                    "finds any embedded/linked PDF, and extracts its text.\n"
                    "  - `playwright_find_archived_url(url=\"...\", date=\"...\")` — "
                    "searches the Wayback Machine for an archived snapshot of a URL "
                    "near a given date. Use when a page is dead or has changed.\n\n"
                    "=== Page Navigation ===\n"
                    "  - `playwright_page_down()` — scroll the viewport DOWN one page.\n"
                    "  - `playwright_page_up()` — scroll the viewport UP one page.\n"
                    "  - `playwright_find_on_page(search_string=\"...\")` — Ctrl+F "
                    "search on the currently visited page.\n"
                    "  - `playwright_find_next()` — jump to the next match of the "
                    "last find_on_page search.\n\n"
                    "=== Utilities ===\n"
                    "  - `transcriber(audio_url=\"...\")` — transcribes an audio file/URL "
                    "to text.\n"
                    "  - `wikipedia_search(query=\"...\")` — search Wikipedia for a "
                    "given query and return a summary.\n"
                    "  - `ask_user(question=\"...\")` — ask the user for clarification "
                    "or additional input.\n"
                    "  - `playwright_inspect_file(file_path=\"...\")` — read a local "
                    "or remote text file and return its contents.\n"
                    "  - `playwright_visualizer(image_path=\"...\", question=\"...\")` "
                    "— answer a question about an image file.\n\n"
                    "There is no `web_search`, `visit_webpage`, or `web_search_agent` "
                    "function available to you (that last name is only how something "
                    "ELSE calls you from outside; it does not exist inside your own "
                    "code).\n\n"
                    "You do NOT need to write code or use fenced code blocks. Simply "
                    "call the tools by their name — this system understands structured "
                    "tool calls natively, without any Python scaffolding.\n\n"
                    "Work like this:\n"
                    "1. Search with `playwright_duckduckgo_search` first.\n"
                    "2. Open promising results with `playwright_visit_page` to read "
                    "their content.\n"
                    "3. If you find a PDF you need text from, use "
                    "`playwright_read_embedded_pdf` to extract it.\n"
                    "4. Once you have enough information, just respond with your "
                    "answer as plain text — that naturally ends the task. You can "
                    "also use the `final_answer` tool to explicitly finish with your "
                    "findings.\n\n"
                    "If after searching you find that you need more information to "
                    "answer the question, you can use `final_answer` with your "
                    "request for clarification as argument to request for more "
                    "information from the user."
                )
            else:
                kwargs["instructions"] = (
                    "You are a focused web search agent. Your ONLY job is to answer "
                    "the sub-question you are given by searching the web and reading "
                    "pages. You have NO other tools besides `web_search` and "
                    "`visit_webpage` — there is no `web_search_agent` function "
                    "available to you (that name is only how something ELSE calls "
                    "you from outside; it does not exist inside your own code).\n\n"
                    "You do NOT need to write code or use fenced code blocks. Simply "
                    "call the tools by their name — this system understands structured "
                    "tool calls natively, without any Python scaffolding.\n\n"
                    "Work like this:\n"
                    "1. Search with `web_search` to find relevant pages.\n"
                    "2. Open promising results with `visit_webpage` to read their "
                    "content.\n"
                    "3. Once you have enough information, just respond with your "
                    "answer as plain text — that naturally ends the task. You can "
                    "also use the `final_answer` tool to explicitly finish with "
                    "your findings.\n\n"
                    "If after searching you find that you need more information to "
                    "answer the question, you can use `final_answer` with your "
                    "request for clarification as argument to request for more "
                    "information from the user."
                )
        if "executor_kwargs" in params and timeout is not None:
            kwargs["executor_kwargs"] = {"timeout_seconds": timeout}
    except (TypeError, ValueError):
        pass

    agent = ToolCallingAgent(**kwargs)
    # Append managed-agent task prompt so the search agent knows how to
    # handle .txt, .pdf, YouTube, and how to request clarification —
    # mirrors the canonical open_deep_research pattern exactly:
    #   https://github.com/huggingface/smolagents/blob/main/examples/open_deep_research/run.py
    agent.prompt_templates["managed_agent"]["task"] += (
        "\nYou can navigate to .txt online files. "
        "If a non-html page is in another format, especially .pdf or a Youtube "
        "video, use a tool like 'inspect_file_as_text' or "
        "'playwright_read_embedded_pdf' to inspect it. "
        "Additionally, if after some searching you find out that you need more "
        "information to answer the question, you can use `final_answer` with "
        "your request for clarification as argument to request for more information."
    )
    return agent


def _supports_native_tool_calls(llm) -> bool:
    """Heuristic: does *llm* support native tool-calling (function-calling
    API) — meaning we should use ToolCallingAgent instead of CodeAgent?"""
    cls_name = type(llm).__name__
    if cls_name == "LiteLLMModel":
        return True
    if cls_name == "InferenceClientModel":
        model_id = getattr(llm, "model_id", "") or ""
        tc_hints = ("qwen3", "qwen2.5", "llama-3", "llama-4", "phi-4",
                    "deepseek-v3", "deepseek-r1", "mistral-large",
                    "gemma-3", "gemma-4", "command-r")
        return any(h in model_id.lower() for h in tc_hints)
    return False


def _build_manager_agent(llm, search_agent, model_id: str = "", max_steps: Optional[int] = None, timeout: Optional[int] = None, use_playwright: bool = False, headless: bool = True, use_tool_calling: bool = True):
    final_max_steps = max_steps if max_steps is not None else mr.get_max_steps_for_model(model_id, MANAGER_DEFAULT_MAX_STEPS)
    tools = []
    if use_playwright and _playwright_available:
        tools = [
            PlaywrightTextInspectorTool(),
            PlaywrightVisualizerTool(),
        ]

    use_tc = use_tool_calling and _supports_native_tool_calls(llm)
    AgentClass = ToolCallingAgent if use_tc else CodeAgent
    agent_name = AgentClass.__name__

    kwargs = dict(
        model=llm,
        tools=tools,
        managed_agents=[search_agent],
        planning_interval=DEEP_RESEARCH_PLANNING_INTERVAL,
        max_steps=final_max_steps,
        verbosity_level=1,
    )
    try:
        params = inspect.signature(AgentClass.__init__).parameters
        if AgentClass is CodeAgent and "code_block_tags" in params:
            kwargs["code_block_tags"] = "markdown"
        if "instructions" in params:
            base_instructions = DEEP_RESEARCH_INSTRUCTIONS
            extra = ""
            if use_playwright and _playwright_available:
                extra = (
                    "You also have direct access to these utility tools:\n"
                    "  - `playwright_inspect_file(file_path=\"...\")` — read a local "
                    "or remote text file and return its contents. Use this to inspect "
                    "downloaded or referenced files without needing to delegate to the "
                    "web_search_agent.\n"
                    "  - `playwright_visualizer(image_path=\"...\", question=\"...\")` — "
                    "answer a question about an image file. Use this when you need to "
                    "analyze an image the user provided or that was found during research.\n\n"
                )
            kwargs["instructions"] = base_instructions + extra
        if "executor_kwargs" in params and timeout is not None:
            kwargs["executor_kwargs"] = {"timeout_seconds": timeout}
        if "final_answer_checks" in params:
            kwargs["final_answer_checks"] = [_validate_final_report]
    except (TypeError, ValueError):
        pass
    print(f"[DeepResearch] Building manager {agent_name} on '{model_id or '(shared)'}' …")
    return AgentClass(**kwargs)


def reset_tool_usage() -> None:
    """Call right before agent.run() so this run's tracked queries/URLs
    start from zero — mirrors general_agent.reset_tool_usage()."""
    if _search_tool is not None:
        _search_tool.queries_run = []
        _search_tool.result_links = []
    if _webpage_tool is not None:
        _webpage_tool.urls_visited = []


def get_tool_usage() -> tuple:
    """Call right after agent.run() returns. Returns (queries_run,
    urls_visited, result_links) from the search sub-agent's own tools —
    see general_agent.get_tool_usage() for the equivalent on that tab.
    Passed to general_agent.resolve_actually_used_sources() so chat.py
    can print a guaranteed-accurate References list for this report."""
    queries = list(_search_tool.queries_run) if _search_tool is not None else []
    urls    = list(_webpage_tool.urls_visited) if _webpage_tool is not None else []
    links   = list(_search_tool.result_links) if _search_tool is not None else []
    return queries, urls, links


def get_deep_research_agent(model_id: Optional[str] = None, use_playwright: bool = False, headless: bool = True, manager_max_steps: Optional[int] = None, search_max_steps: Optional[int] = None, timeout: Optional[int] = None, use_tool_calling: bool = True):
    """Lazily build (or rebuild, if the model changed) the manager agent
    and its search sub-agent."""
    global _manager_agent, _manager_agent_model_id, _manager_agent_config
    target = model_id or models._llm_model_id

    current_config = {
        "use_playwright": use_playwright,
        "headless": headless,
        "manager_max_steps": manager_max_steps,
        "search_max_steps": search_max_steps,
        "timeout": timeout
    }

    if _manager_agent is not None and target == _manager_agent_model_id and current_config == _manager_agent_config:
        return _manager_agent

    with _manager_agent_lock:
        if _manager_agent is not None and target == _manager_agent_model_id and current_config == _manager_agent_config:
            return _manager_agent

        print(f"[DeepResearch] Building manager + web_search_agent on '{target}' (Playwright: {use_playwright}, Headless: {headless}) …")
        llm = models.get_llm(target)
        search_agent = _build_search_agent(llm, target, use_playwright, headless, search_max_steps, timeout)
        _manager_agent = _build_manager_agent(llm, search_agent, target, manager_max_steps, timeout, use_playwright, headless, use_tool_calling=use_tool_calling)
        _manager_agent_model_id = target
        _manager_agent_config = current_config
        # Standard smolagents behaviour: a freshly-built agent starts with
        # empty memory (see agent_memory.py's module docstring for why
        # this app doesn't try to restore memory from a previous
        # model/session here either).
        return _manager_agent


def reset_agent():
    """Drop the cached manager (and its search sub-agent). Does NOT unload
    the underlying LLM itself — that's shared/managed by models.get_llm().
    Call this whenever the Deep Research tab's model changes or the LLM
    is force-reloaded/unloaded elsewhere — mirrors general_agent.reset_agent().
    """
    global _manager_agent, _manager_agent_model_id, _manager_agent_config, _search_tool, _webpage_tool
    _manager_agent = None
    _manager_agent_model_id = None
    _manager_agent_config = {}
    _search_tool = None
    _webpage_tool = None
