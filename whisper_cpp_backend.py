"""
whisper_cpp_backend.py — Optional whisper.cpp server backend for
Speech-to-Text, alongside the local HuggingFace (transformers/Whisper)
pipeline used elsewhere in the app.

A single mode is supported:

  1. External process — the app launches (or reuses an already‑running)
     `whisper-server` executable (https://github.com/ggerganov/whisper.cpp)
     and talks to it over its OpenAI‑compatible HTTP API
     (`POST /v1/audio/transcriptions`).

The server process is started lazily on first use and kept alive across
turns until the model or a config change triggers a restart.
"""

import atexit
import os
import shlex
import socket
import subprocess
import time
from pathlib import Path
from typing import Optional

import user_config

try:
    WHISPER_CPP_AVAILABLE = True
except ImportError:
    WHISPER_CPP_AVAILABLE = False


# ──────────────────────────────────────────────────────────────────
# whisper-server executable path — NOT hardcoded.  Resolution order:
#   1. WHISPER_CPP_SERVER_EXE environment variable (per‑launch override)
#   2. Persisted setting from user_config.json
#   3. Empty (feature off) if neither is set
# ──────────────────────────────────────────────────────────────────
WHISPER_CPP_SERVER_EXE_PATH = (
    os.environ.get("WHISPER_CPP_SERVER_EXE", "").strip()
    or str(user_config.USER_CONFIG.get("whisper_cpp_server_exe", "")).strip()
)

WHISPER_CPP_SERVER_EXTRA_ARGS = str(
    user_config.USER_CONFIG.get("whisper_cpp_server_extra_args", "")
).strip()

WHISPER_SERVER_HOST = "127.0.0.1"
WHISPER_SERVER_DEFAULT_PORT = 8082

_MODEL_DIR = ""  # populated by set_whisper_model_dir() — reuses the same
                  # GGUF folder as llama_backend when available.

_whisper_server_proc = None
_whisper_server_config = {}  # {"model_path": ..., "port": ...}


def set_whisper_server_exe_path(path: str) -> None:
    global WHISPER_CPP_SERVER_EXE_PATH
    path = (path or "").strip()
    WHISPER_CPP_SERVER_EXE_PATH = path
    user_config.save_user_config({"whisper_cpp_server_exe": path})


def set_whisper_server_extra_args(args_str: str) -> None:
    global WHISPER_CPP_SERVER_EXTRA_ARGS
    WHISPER_CPP_SERVER_EXTRA_ARGS = (args_str or "").strip()
    user_config.save_user_config({"whisper_cpp_server_extra_args": WHISPER_CPP_SERVER_EXTRA_ARGS})


def set_whisper_model_dir(folder_path: str) -> None:
    global _MODEL_DIR
    _MODEL_DIR = (folder_path or "").strip()


def discover_whisper_models(folder: Optional[str] = None) -> dict:
    """Scan `folder` for whisper.cpp model files (.ggml or .bin) and
    return {label: path} entries.

    Falls back to the current _MODEL_DIR if `folder` is not given.
    """
    folder = folder if folder is not None else _MODEL_DIR
    if not folder:
        return {}
    p = Path(folder)
    if not p.exists():
        return {}
    found = {}
    for f in sorted(p.rglob("*")):
        if f.suffix.lower() in (".ggml", ".bin") and "whisper" in f.stem.lower():
            size_mb = f.stat().st_size / (1024 ** 2)
            label = f"🎤 {f.stem}  (~{size_mb:.0f} MB | whisper.cpp)"
            found[label] = str(f)
    return found


# ── Port / health helpers ─────────────────────────────────────────

def _find_free_port(start: int) -> int:
    p = start
    while p < start + 100:
        if _port_is_free(p):
            return p
        p += 1
    return start + 99


def _port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((WHISPER_SERVER_HOST, port))
            return True
        except OSError:
            return False


_PORT_CHECK_CACHE = {}  # (host, port) -> healthy | None


def _server_health_ok(port: int) -> bool:
    """Quick TCP connect check — whisper-server doesn't have a dedicated
    /health endpoint, so we just check the port is open."""
    key = (WHISPER_SERVER_HOST, port)
    cached = _PORT_CHECK_CACHE.get(key)
    if cached:
        return True
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(2)
        try:
            s.connect((WHISPER_SERVER_HOST, port))
            _PORT_CHECK_CACHE[key] = True
            return True
        except (OSError, ConnectionRefusedError):
            _PORT_CHECK_CACHE.pop(key, None)
            return False


# ── Server lifecycle ──────────────────────────────────────────────

def stop_whisper_server() -> None:
    """Terminate the managed whisper-server subprocess, if one is running."""
    global _whisper_server_proc, _whisper_server_config
    if _whisper_server_proc is not None:
        print("[whisper-server] Stopping subprocess …")
        try:
            _whisper_server_proc.terminate()
            try:
                _whisper_server_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                _whisper_server_proc.kill()
        except Exception:
            pass
    _whisper_server_proc = None
    _whisper_server_config = {}
    _PORT_CHECK_CACHE.clear()


atexit.register(stop_whisper_server)


def get_or_start_whisper_server(model_path: str,
                                 port: Optional[int] = None,
                                 startup_timeout: int = 60) -> str:
    """Ensure a whisper-server process is running with this exact model,
    launching/relaunching it if needed, and return its base URL."""
    global _whisper_server_proc, _whisper_server_config

    if not WHISPER_CPP_SERVER_EXE_PATH:
        raise RuntimeError(
            "No whisper-server executable is configured. Set its path in the "
            "'🖥️ whisper.cpp Server Path' box in the UI (or the "
            "WHISPER_CPP_SERVER_EXE environment variable)."
        )
    exe = Path(WHISPER_CPP_SERVER_EXE_PATH)
    if not exe.exists():
        raise RuntimeError(
            f"whisper-server executable not found at '{exe}'."
        )

    target_port = port or WHISPER_SERVER_DEFAULT_PORT
    wanted = {"model_path": model_path, "port": target_port}

    if (_whisper_server_proc is not None and _whisper_server_proc.poll() is None
            and _whisper_server_config.get("model_path") == wanted["model_path"]
            and _server_health_ok(_whisper_server_config.get("port", target_port))):
        return f"http://{WHISPER_SERVER_HOST}:{_whisper_server_config['port']}"

    stop_whisper_server()

    if not _port_is_free(target_port):
        target_port = _find_free_port(target_port)
        wanted["port"] = target_port

    cmd = [
        str(exe),
        "-m", model_path,
        "--host", WHISPER_SERVER_HOST,
        "--port", str(target_port),
    ]
    if WHISPER_CPP_SERVER_EXTRA_ARGS:
        cmd.extend(shlex.split(WHISPER_CPP_SERVER_EXTRA_ARGS))

    print(f"[whisper-server] Launching: {' '.join(cmd)}")
    _whisper_server_proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    _whisper_server_config = wanted

    deadline = time.time() + startup_timeout
    while time.time() < deadline:
        if _whisper_server_proc.poll() is not None:
            tail = ""
            if _whisper_server_proc.stdout:
                try:
                    tail = "".join(_whisper_server_proc.stdout.readlines()[-20:])
                except Exception:
                    pass
            _whisper_server_proc = None
            _whisper_server_config = {}
            raise RuntimeError(
                f"whisper-server exited immediately. Last output:\n{tail}"
            )
        if _server_health_ok(target_port):
            print(f"[whisper-server] Ready — http://{WHISPER_SERVER_HOST}:{target_port}")
            return f"http://{WHISPER_SERVER_HOST}:{target_port}"
        time.sleep(0.5)

    stop_whisper_server()
    raise RuntimeError(
        f"whisper-server did not become reachable within {startup_timeout}s."
    )


# ── WhisperServerModel ────────────────────────────────────────────

class WhisperServerModel:
    """Transcribes audio by POSTing to a running whisper-server's
    /v1/audio/transcriptions endpoint (OpenAI-compatible API)."""

    def __init__(self, base_url: str, model_path: str, timeout: int = 120):
        self.model_id = model_path
        self.model_path = model_path
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> str:
        import requests
        url = f"{self.base_url}/v1/audio/transcriptions"

        with open(audio_path, "rb") as f:
            files = {"file": (Path(audio_path).name, f, "audio/wav")}
            data = {"model": self.model_path}
            if language and language != "auto":
                data["language"] = language

            resp = requests.post(url, files=files, data=data, timeout=self.timeout)
            resp.raise_for_status()
            result = resp.json()
            return result.get("text", "")
