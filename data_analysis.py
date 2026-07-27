"""
data_analysis.py — smolagents CodeAgent that explores uploaded CSV/XLSX
files, builds charts, and writes a Markdown report. The agent can install
any missing Python packages itself via the `install_package` tool.
"""

import inspect
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

import gradio as gr
from smolagents import CodeAgent, tool

import agent_memory
import agent_streaming
import model_registry as mr
import models
from hardware import DEVICE
from knowledge_base import get_file_path

_data_agent          = None
_data_agent_model_id = None
_data_agent_max_steps = None
_data_agent_execution_timeout = None
_data_agent_lock      = threading.Lock()

# How many conversation turns the Data Analysis CodeAgent is allowed to
# remember (see agent_memory.cap_agent_memory()). Kept smaller than the
# other tabs' default of 6 because each turn's task prompt here is already
# long (the full EDA instructions in run_data_analysis() below), so memory
# grows the prompt much faster per turn than a one-line chat question would.
DATA_AGENT_MEMORY_TURNS = 3

# Tracks which uploaded file paths the agent's current memory "belongs
# to". A new/changed set of files means a different dataset, so old
# memory (which may reference the previous file's columns/stats) needs to
# be dropped even though the model itself hasn't changed — see
# agent_memory.reset_if_context_changed().
_last_data_context = {"key": None}


@tool
def install_package(package_name: str) -> str:
    """
    Install a Python package into the current environment using pip.
    Use this whenever a data-analysis step needs a library that is not
    yet installed (e.g. "openpyxl" for reading .xlsx files, "seaborn",
    "scikit-learn", "statsmodels", "plotly", "xlsxwriter").

    Args:
        package_name: The pip package name to install, e.g. "seaborn" or
            "scikit-learn==1.4.0". Pass a single package per call.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check", package_name],
            capture_output=True, text=True,             timeout=1200,
        )
        if result.returncode == 0:
            return f"✅ Installed '{package_name}' successfully."
        return f"❌ Failed to install '{package_name}':\n{result.stderr[-2000:]}"
    except subprocess.TimeoutExpired:
        return f"❌ Installing '{package_name}' timed out after 1200s."
    except Exception as e:
        return f"❌ Error installing '{package_name}': {e}"


@tool
def save_report(content: str, filename: str = "report.md") -> str:
    """
    Save Markdown report text to a file inside the data-analysis output
    directory.

    IMPORTANT: the sandboxed code executor blocks Python's built-in
    open()/write() for safety — calling open() directly always fails
    with "Forbidden function evaluation". Use THIS tool to save your
    report instead. (matplotlib's plt.savefig() is a separate whitelisted
    call and works fine for charts — no change needed there.)

    Args:
        content: The full Markdown report text to save.
        filename: File name to save it as, e.g. "report.md" (default).
    """
    try:
        out_dir = Path(mr.DATA_OUTPUT_DIR)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / filename
        path.write_text(content, encoding="utf-8")
        return f"✅ Saved report to '{path}' ({len(content)} chars)."
    except Exception as e:
        return f"❌ Failed to save report: {e}"


def get_data_agent(model_id: Optional[str] = None,
                   max_steps: Optional[int] = None,
                   execution_timeout: Optional[int] = None):
    """Lazily build (or rebuild, if the model changed) the data-analysis CodeAgent.

    Args:
        model_id: HuggingFace model id or GGUF path. Falls back to the currently
            loaded LLM if not given.
        max_steps: Maximum agentic steps before the agent gives up. Uses the
            module-level default (DATA_AGENT_MAX_STEPS) if not given.
        execution_timeout: Seconds before the Python sandbox kills a single
            code-execution block. Uses smolagents' default (30s) if not given.
    """
    global _data_agent, _data_agent_model_id
    global _data_agent_max_steps, _data_agent_execution_timeout
    target = model_id or models._llm_model_id

    if (_data_agent is not None
            and target == _data_agent_model_id
            and max_steps == _data_agent_max_steps
            and execution_timeout == _data_agent_execution_timeout):
        return _data_agent

    with _data_agent_lock:
        if (_data_agent is not None
                and target == _data_agent_model_id
                and max_steps == _data_agent_max_steps
                and execution_timeout == _data_agent_execution_timeout):
            return _data_agent

        print(f"[DataAgent] Building CodeAgent on '{target}' …")
        llm = models.get_llm(target)
        agent_kwargs = dict(
            model=llm,
            tools=[install_package, save_report],
            additional_authorized_imports=["*"],   # trusted local machine — full stdlib + installed pkgs
            max_steps=max_steps or mr.DATA_AGENT_MAX_STEPS,
        )
        _data_agent_model_id = target
        _data_agent_max_steps = max_steps
        _data_agent_execution_timeout = execution_timeout
        if execution_timeout is not None and execution_timeout > 0:
            agent_kwargs["executor_kwargs"] = {"timeout_seconds": execution_timeout}
        # Some models (esp. "thinking"-tuned ones, or anything running
        # through a raw llama.cpp chat template) reliably write plain
        # ```python fenced code instead of the <code></code> tags
        # CodeAgent expects by default, causing every step to fail
        # parsing. Use the more broadly-compatible markdown-fence
        # convention when this smolagents version supports it.
        try:
            if "code_block_tags" in inspect.signature(CodeAgent.__init__).parameters:
                agent_kwargs["code_block_tags"] = "markdown"
        except (TypeError, ValueError):
            pass
        _data_agent = CodeAgent(**agent_kwargs)
        # Standard smolagents behaviour: a freshly-built CodeAgent starts
        # with empty memory. This only happens on first use, or after a
        # model switch/reset via reset_agent() below — dataset changes are
        # handled separately by reset_if_context_changed() in
        # run_data_analysis(), which clears an EXISTING agent's memory in
        # place rather than rebuilding it (see agent_memory.py's module
        # docstring for why rebuilding-to-reset used to reintroduce the
        # very stale memory it was meant to drop).
        return _data_agent


def reset_agent():
    """Drop the CodeAgent wrapper. It references the shared LLM managed by
    models.get_llm(), whose memory is released there when the underlying
    model actually changes. Rebuilding is cheap since it reuses get_llm(target).

    Also called whenever the LLM is reloaded/unloaded elsewhere (the agent
    holds its own reference to that same model and would otherwise keep an
    unloaded model alive).
    """
    global _data_agent, _data_agent_model_id
    global _data_agent_max_steps, _data_agent_execution_timeout
    _data_agent = None
    _data_agent_model_id = None
    _data_agent_max_steps = None
    _data_agent_execution_timeout = None


def save_data_files(files) -> list:
    """Copy uploaded CSV/XLSX files into the persistent data-analysis workspace."""
    Path(mr.DATA_UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    paths = []
    if not files:
        return paths
    if not isinstance(files, list):
        files = [files]
    for f in files:
        src = get_file_path(f)
        if not src:
            continue
        dest = Path(mr.DATA_UPLOAD_DIR) / Path(src).name
        try:
            shutil.copy(src, dest)
            paths.append(str(dest))
        except Exception:
            pass
    return paths


def run_data_analysis(files, question: str, model_label: str, history: list,
                       use_memory: bool = True, lang_key: str = "kh",
                       max_steps: Optional[int] = None,
                       execution_timeout: Optional[int] = None):
    """Hand uploaded data + the user's question to the CodeAgent and collect its report.

    `use_memory` controls the "🧠 Conversation Memory" checkbox: when on,
    the CodeAgent remembers earlier turns about the SAME dataset (capped —
    see DATA_AGENT_MEMORY_TURNS) and old memory is dropped automatically
    if a different file is uploaded. When off, every question is answered
    from a clean slate regardless of what file is uploaded.

    A GENERATOR: yields (history, gallery_update, report_update) once per
    live agent step as the EDA runs (see agent_streaming.py), using
    gr.update() no-op placeholders for the gallery/report outputs during
    those intermediate yields so charts/report don't flicker to "empty"
    mid-run — then one final time with the real chart list + report file
    once the agent actually finishes. This is easily the longest-running
    single call in the app (a full EDA — load, chart, correlate, write a
    report), so live progress matters here more than almost anywhere else.
    """
    history = history or []

    paths = save_data_files(files)
    if not paths:
        history.append({"role": "user", "content": question or "(no file)"})
        history.append({"role": "assistant", "content": "⚠️ Please upload a CSV or XLSX file first."})
        yield history, None, None
        return

    question = (question or "").strip() or (
        "Perform a full exploratory data analysis (EDA) on this dataset and "
        "generate a thorough Markdown report with multiple charts."
    )
    model_id = mr.MODEL_OPTIONS.get(model_label, mr.DEFAULT_LLM_MODEL)
    history.append({"role": "user", "content": f"📎 {', '.join(Path(p).name for p in paths)}\n\n{question}"})

    try:
        out_dir = Path(mr.DATA_OUTPUT_DIR)
        out_dir.mkdir(parents=True, exist_ok=True)
        # Now that a run can produce many charts (full EDA, not just one),
        # clear out PNGs left over from a previous analysis first — otherwise
        # they'd pile up and get mixed into this run's gallery below.
        for stale_png in out_dir.glob("*.png"):
            try:
                stale_png.unlink()
            except OSError:
                pass
        agent = get_data_agent(model_id, max_steps=max_steps, execution_timeout=execution_timeout)
        # New/changed dataset → old agent memory (referencing whatever the
        # previous file's columns/stats were) is no longer relevant, so
        # drop it even though the model itself hasn't changed. Only
        # relevant when memory is on — when it's off, reset=True below
        # already makes every run stateless regardless of dataset.
        # Clears agent.memory.steps directly on the SAME agent object —
        # see agent_memory.reset_if_context_changed()/reset_memory()'s
        # docstrings for why this (rather than tearing down and rebuilding
        # the agent, as an earlier version of this file did) is required
        # for the reset to actually stick.
        if use_memory:
            agent_memory.reset_if_context_changed(agent, _last_data_context, tuple(sorted(paths)))
        file_list_str = "\n".join(f"- {p}" for p in paths)
        report_path = str(Path(mr.DATA_OUTPUT_DIR) / "report.md")

        lang_instruction = "Answer in Khmer.\n\n" if lang_key == "kh" else ""

        task = f"""{lang_instruction}You are a data analysis assistant working in a local Python sandbox
with pandas, matplotlib, and common data-science libraries.

Data file(s) provided by the user:
{file_list_str}

User request: {question}

Your job is to fulfil the user's request as written — whether that is an
exploratory analysis, a payroll calculation, a data cleaning task, a specific
computation, or anything else. Follow these principles:

A. FOLLOW THE USER REQUEST FIRST
   - Read the user's request carefully and do exactly what was asked.
   - If the user asks a specific question (e.g. "calculate total salary",
     "show me the top 10 rows", "filter by department"), answer that question
     directly and precisely. Do not force a full EDA if the user didn't ask
     for one.
   - If the user asks something open-ended or gives no specific instruction,
     default to a thorough exploratory data analysis (EDA) — load, profile,
     visualise, correlate, and report insights.

B. DERIVE BLANK BUT COMPUTABLE COLUMNS
   - Inspect every column. If any column is completely empty (all NaN/null)
     but its values CAN be calculated from other columns in the dataset,
     compute and populate it. For example:
       * "Total Compensation" = Salary + Bonus + Benefits
       * "Net Pay" = Gross Pay - Deductions - Tax
       * "Full Name" = First Name + " " + Last Name
       * "Age" = current year - Birth Year
   - After deriving, report which columns were empty and what formula you used.
   - If a column is empty and CANNOT be derived (no source data exists to
     compute it), note this clearly in the output.

C. TOOL USAGE & CODE EXECUTION
   - Load files with pandas (pd.read_csv for .csv, pd.read_excel for
     .xlsx/.xls — if a required package like 'openpyxl' is missing, call the
     install_package tool with its pip name first, then retry the import).
   - You can install any Python package you need with install_package().
   - Save EVERY chart as a PNG with a descriptive filename inside
     '{mr.DATA_OUTPUT_DIR}' (use plt.savefig(...); ALWAYS call plt.close()
     right after savefig; never call plt.show()).
   - To save your final report / answer text, call save_report(content=...).
     Do NOT use Python's raw open()/write() — the sandbox blocks it.
     (plt.savefig() is whitelisted separately and works fine.)

D. EXPLORATORY ANALYSIS (use when user gives no specific instruction)
   When doing a default EDA, work through these sections as applicable:

   1. LOAD & OVERVIEW — shape, columns, dtypes, missing values, duplicates.
   2. UNIVARIATE ANALYSIS — descriptive stats (mean, median, std, min/max,
      quartiles, skewness), histograms + boxplots for numeric columns, bar
      charts for categorical columns.
   3. BIVARIATE / RELATIONSHIP ANALYSIS — correlation matrix heatmap, scatter
      plots for top correlated pairs, grouped comparisons if a categorical
      grouping column exists.
   4. OUTLIERS — IQR method on key numeric columns.
   5. KEY INSIGHTS — 3-5 concrete observations, not just restated stats.

E. VISUALIZATION GUIDANCE
   | Data Type         | Best Chart       |
   |-------------------|------------------|
   | Trends over time  | Line chart       |
   | Part of whole     | Pie/Donut chart  |
   | Comparison        | Bar chart        |
   | Distribution      | Histogram        |
   | Correlation       | Scatter plot     |

F. PAYROLL / COMPENSATION GUIDANCE
   If the request involves payroll, compensation, or salary data:
   - Compute gross pay, total deductions, tax withholdings, net pay.
   - Validate that deductions never exceed gross pay; flag negative net pay.
   - Report totals: total gross, total deductions, total net, headcount,
     average cost per employee, and department-level aggregates.
   - Derive any empty compensation columns (e.g. Total Compensation,
     Net Pay) from available source columns.

G. REPORT STRUCTURE
   - Write a well-structured Markdown report with the actual numbers you
     computed (no placeholders).
   - Reference chart filenames you created so readers know which chart
     supports which point.
   - When doing a default EDA, use these templates:

     ## Dataset Overview
     **Rows**: N  **Columns**: M
     | Column | Type | Non-null | Unique | Sample Values |
     |--------|------|----------|--------|---------------|

     ## Statistical Summary
     - **Mean**: X  **Median**: Y  **Std Dev**: Z
     - **Key Findings**: ...

     ## Analysis Report: [Topic]
     ### Executive Summary
     ### Key Metrics | Value | Change
     ### Trends & Recommendations

H. As your FINAL ANSWER, return the full Markdown report or the direct answer
   to the user's question.
"""
        # See chat.py's chat_general_direct() matching comment — a no-op
        # unless the "🧠 Enable Model Reasoning" toggle (⚙️ Model Settings)
        # is off. Data Analysis's task prompt is already long, so a heavy
        # thinking-tuned model has even less MAX_NEW_TOKENS headroom left
        # for its actual code — this is one of the tabs most likely to
        # benefit from turning reasoning off.
        task = mr.apply_reasoning_toggle(task)
        t0 = time.time()
        # reset=False keeps this CodeAgent's memory across turns on the
        # SAME dataset (e.g. "now also break that down by region" after an
        # initial EDA) — see
        # https://huggingface.co/docs/smolagents/tutorials/memory. Capped
        # right after via agent_memory.cap_agent_memory(), and fully reset
        # above whenever the uploaded file(s) change. reset=True (memory
        # checkbox off) makes every question stateless instead.
        # Live step streaming — see agent_streaming.stream_agent_steps()'s
        # docstring / chat.py's matching usage in the other agentic tabs.
        result = None
        for step_msg, is_final, final_output in agent_streaming.stream_agent_steps(agent, task, reset=not use_memory):
            if not is_final:
                if step_msg is not None:
                    history.append(step_msg)
                    yield history, gr.update(), gr.update()
                continue
            result = final_output
        if use_memory:
            agent_memory.cap_agent_memory(agent, max_turns=DATA_AGENT_MEMORY_TURNS)
        elapsed = time.time() - t0

        report_text = str(result)
        response = (
            report_text +
            f"\n\n<hr><sub>⏱ {elapsed:.1f}s | model: <code>{model_id}</code> "
            f"({DEVICE.upper()}) | memory: {'on' if use_memory else 'off'}</sub>"
        )
        history.append({"role": "assistant", "content": response})

        chart_files = sorted(str(p) for p in Path(mr.DATA_OUTPUT_DIR).glob("*.png"))
        report_file = report_path if Path(report_path).exists() else None
        yield history, (chart_files or None), report_file
        return

    except Exception as e:
        import traceback
        history.append({"role": "assistant", "content": f"❌ {e}\n\n{traceback.format_exc()}"})
        yield history, None, None
        return
