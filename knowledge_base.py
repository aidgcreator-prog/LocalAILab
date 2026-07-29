"""
knowledge_base.py — Document indexing (PDF/TXT/MD/DOCX + HuggingFace
datasets) into ChromaDB, the optional visual (image-based PDF) index via
byaldi, and retrieval helpers used by the chat tabs.
"""

import base64
import time
from collections import defaultdict
from io import BytesIO
from pathlib import Path
from typing import Optional

from PIL import Image
from byaldi import RAGMultiModalModel

from smolagents import Tool

import model_registry as mr
import models
from hardware import DEVICE
from i18n import LANGUAGES

import os
import sys

_visual_retriever    = None
_visual_retriever_id = None


def _add_poppler_to_path():
    if sys.platform != "win32":
        return
    poppler_dir = Path.cwd() / "poppler"
    if poppler_dir.exists():
        for pdfinfo_file in poppler_dir.rglob("pdfinfo.exe"):
            bin_dir = pdfinfo_file.parent
            bin_str = str(bin_dir)
            if bin_str not in os.environ["PATH"]:
                os.environ["PATH"] = bin_str + os.pathsep + os.environ["PATH"]
                print(f"[Poppler] Found local Poppler at: {bin_str}")
            return

    possible_paths = [
        Path(sys.prefix) / "Library" / "bin",
        Path(sys.prefix) / "bin",
        Path(os.environ.get("LOCALAPPDATA", "")) / "scoop" / "apps" / "poppler" / "current" / "bin",
        Path(os.environ.get("USERPROFILE", "")) / "scoop" / "apps" / "poppler" / "current" / "bin",
        Path(r"C:\poppler\Library\bin"),
        Path(r"C:\poppler\bin"),
        Path(r"C:\Program Files\poppler\Library\bin"),
        Path(r"C:\Program Files\poppler\bin"),
    ]
    for p in possible_paths:
        if p.exists() and (p / "pdfinfo.exe").exists():
            p_str = str(p)
            if p_str not in os.environ["PATH"]:
                os.environ["PATH"] = p_str + os.pathsep + os.environ["PATH"]
                print(f"[Poppler] Auto-detected Poppler at: {p_str}")
            break

_add_poppler_to_path()


def get_file_path(f) -> Optional[str]:
    if f is None:          return None
    if isinstance(f, str): return f
    if isinstance(f, dict):return f.get("path") or f.get("name") or f.get("tmp_path")
    if hasattr(f, "path"): return f.path
    if hasattr(f, "name"): return f.name
    return None


def _chunk_text(text: str):
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start: start + mr.CHUNK_SIZE])
        start += mr.CHUNK_SIZE - mr.CHUNK_OVERLAP
    return chunks


def _safe_meta(meta: dict, chunk_index: int) -> dict:
    safe = {k: v if isinstance(v, (str, int, float, bool)) else str(v)
            for k, v in meta.items()}
    safe["chunk_index"] = chunk_index
    return safe


_DIMENSION_MISMATCH_HINT = (
    "The current embedding model doesn't match the one this knowledge "
    "base was indexed with (vector dimension mismatch). Switch back to "
    "the original embedding model in the 📂 Knowledge Base tab's "
    "'🧩 Embedding Model' control, or clear the index (💥 Clear ALL) and "
    "re-index your documents with the new embedding model."
)


def get_collection_embedding_dim() -> Optional[int]:
    """Best-effort: return the vector dimension the CURRENT ChromaDB
    collection was actually built with, by peeking at one stored
    embedding. Returns None if the collection is empty — nothing to
    compare against yet, so any embedding model is safe to switch to.

    Used by the Knowledge Base tab's "🧩 Embedding Model" Load button to
    warn the user BEFORE they switch, rather than only finding out the
    hard way on the next query/index call.
    """
    col = models.get_chroma_collection()
    if col.count() == 0:
        return None
    try:
        peek = col.peek(limit=1)
        vecs = peek.get("embeddings")
        if vecs is not None and len(vecs) > 0:
            return len(vecs[0])
    except Exception:
        pass
    return None


def index_texts(texts: list, metadatas: list) -> int:
    invalidate_doc_table_cache()
    col = models.get_chroma_collection()
    all_chunks, all_metas, all_ids = [], [], []
    for text, meta in zip(texts, metadatas):
        for j, chunk in enumerate(_chunk_text(text)):
            uid = f"{meta.get('source','doc')}__{len(all_chunks)}"
            all_chunks.append(chunk)
            all_metas.append(_safe_meta(meta, j))
            all_ids.append(uid)
    if not all_chunks:
        return 0
    for i in range(0, len(all_chunks), 64):
        vecs = models.encode_texts(all_chunks[i:i+64])
        try:
            col.upsert(embeddings=vecs, documents=all_chunks[i:i+64],
                       metadatas=all_metas[i:i+64], ids=all_ids[i:i+64])
        except Exception as e:
            if "dimension" in str(e).lower():
                raise RuntimeError(f"{_DIMENSION_MISMATCH_HINT}\n\nOriginal error: {e}") from e
            raise
    return len(all_chunks)


def _load_byaldi_model(retriever_id: str):
    global _visual_retriever, _visual_retriever_id
    if _visual_retriever is not None and _visual_retriever_id == retriever_id:
        return _visual_retriever

    target = retriever_id or mr.DEFAULT_VISUAL_RETRIEVER
    try:
        _visual_retriever = RAGMultiModalModel.from_pretrained(
            target, index_root=mr.VISUAL_INDEX_DIR, verbose=0,
        )
        _visual_retriever_id = target
    except ValueError as e:
        if "only supports ColPali and ColQwen2" in str(e):
            fallback = "vidore/colqwen2-v1.0"
            print(f"[Vision] '{target}' not supported by this version of Byaldi. Falling back to: {fallback}")
            _visual_retriever = RAGMultiModalModel.from_pretrained(
                fallback, index_root=mr.VISUAL_INDEX_DIR, verbose=0,
            )
            _visual_retriever_id = fallback
        else:
            raise
    return _visual_retriever


def get_visual_retriever():
    return _load_byaldi_model(_visual_retriever_id or mr.DEFAULT_VISUAL_RETRIEVER)


def index_pdf_visual(filepath: str, retriever_id: str) -> str:
    try:
        global _visual_retriever, _visual_retriever_id
        index_path = Path(mr.VISUAL_INDEX_DIR) / "main"
        index_path.parent.mkdir(parents=True, exist_ok=True)
        
        _load_byaldi_model(retriever_id)

        if index_path.exists():
            try:
                retriever = RAGMultiModalModel.from_index(str(index_path))
                retriever.add_to_index(input_item=filepath,
                                       store_collection_with_index=True,
                                       doc_id=int(time.time()))
                _visual_retriever = retriever
            except Exception:
                _visual_retriever.index(input_path=filepath, index_name="main",
                                        store_collection_with_index=True, overwrite=True)
        else:
            _visual_retriever.index(input_path=filepath, index_name="main",
                                    store_collection_with_index=True, overwrite=False)
        return f"✅ Visual index updated: '{Path(filepath).name}'"
    except ImportError:
        return "⚠️ byaldi not installed — skipping visual index."
    except Exception as e:
        err_str = str(e)
        if "poppler" in err_str.lower() or "page count" in err_str.lower():
            return "⚠️ Poppler not installed/in PATH — skipped visual PDF rendering (text index succeeded)."
        return f"❌ {e}"


def visual_retrieve(query: str, top_k: int = 3) -> list:
    # Nothing has been indexed into the visual (image-based PDF) index yet —
    # skip entirely instead of loading the ~2-8 GB retriever model just to
    # hit "No passages provided". This is the normal state until the user
    # indexes at least one PDF from the Knowledge Base tab.
    if not (Path(mr.VISUAL_INDEX_DIR) / "main").exists():
        return []
    retriever = get_visual_retriever()
    if retriever is None:
        return []
    try:
        results = retriever.search(query, k=top_k)
        images  = []
        for r in results:
            if hasattr(r, "base64") and r.base64:
                images.append(Image.open(BytesIO(base64.b64decode(r.base64))).convert("RGB"))
        return images
    except Exception as e:
        print(f"[VIS] {e}")
        return []


def unload_visual_retriever_fn(lang_key: str = "kh") -> str:
    global _visual_retriever, _visual_retriever_id
    l = LANGUAGES.get(lang_key, LANGUAGES["kh"])
    if _visual_retriever is None:
        return l["btn_unload_none"]
    mid = _visual_retriever_id or mr.DEFAULT_VISUAL_RETRIEVER
    models._release_model(_visual_retriever)
    _visual_retriever = None
    _visual_retriever_id = None
    return l["msg_unloaded"].format(model=mid)


def index_pdf_file(filepath: str, visual_retriever_id: str = mr.DEFAULT_VISUAL_RETRIEVER,
                   theme: str = "", subtheme: str = "") -> str:
    msgs = []
    try:
        import fitz
        doc = fitz.open(filepath)
        texts, metas = [], []
        for n, page in enumerate(doc):
            t = page.get_text()
            if t.strip():
                texts.append(t)
                metas.append({"source": Path(filepath).name, "page": n+1, "type": "pdf",
                              "theme": theme, "subtheme": subtheme})
        doc.close()
        msgs.append(f"✅ Text: {index_texts(texts, metas)} chunks")
    except Exception as e:
        msgs.append(f"⚠️ Text failed: {e}")
    msgs.append(f"🖼️ {index_pdf_visual(filepath, visual_retriever_id)}")
    return "\n".join(msgs)


def index_txt_file(filepath: str, theme: str = "", subtheme: str = "") -> str:
    try:
        text = Path(filepath).read_text(encoding="utf-8", errors="replace")
        k    = index_texts([text], [{"source": Path(filepath).name, "type": "txt",
                                     "theme": theme, "subtheme": subtheme}])
        return f"✅ {k} chunks from '{Path(filepath).name}'"
    except Exception as e:
        return f"❌ {e}"


def index_docx_file(filepath: str, theme: str = "", subtheme: str = "") -> str:
    try:
        import docx  # python-docx
        document = docx.Document(filepath)

        parts = []
        for para in document.paragraphs:
            if para.text.strip():
                parts.append(para.text)

        for table in document.tables:
            for row in table.rows:
                cells = [c.text.strip() for c in row.cells if c.text.strip()]
                if cells:
                    parts.append(" | ".join(cells))

        text = "\n".join(parts)
        if not text.strip():
            return f"⚠️ No extractable text in '{Path(filepath).name}'"

        k = index_texts([text], [{"source": Path(filepath).name, "type": "docx",
                                 "theme": theme, "subtheme": subtheme}])
        return f"✅ {k} chunks from '{Path(filepath).name}'"
    except ImportError:
        return "⚠️ python-docx not installed — run 'pip install python-docx' to index .docx files."
    except Exception as e:
        return f"❌ {e}"


def index_uploaded_files(files, visual_retriever_label: str,
                        theme: str = "", subtheme: str = "") -> str:
    if not files:
        return "No files uploaded."
    retriever_id = mr.VISUAL_RETRIEVER_OPTIONS.get(visual_retriever_label, mr.DEFAULT_VISUAL_RETRIEVER)
    if not isinstance(files, list):
        files = [files]
    flat = []
    for item in files:
        flat.extend(item) if isinstance(item, list) else flat.append(item)
    msgs = []
    for f in flat:
        path = get_file_path(f)
        if not path:
            msgs.append(f"⚠️ Cannot resolve path: {f!r}")
            continue
        ext = Path(path).suffix.lower()
        if ext == ".pdf":
            msgs.append(index_pdf_file(path, retriever_id, theme, subtheme))
        elif ext in (".txt", ".md"):
            msgs.append(index_txt_file(path, theme, subtheme))
        elif ext == ".docx":
            msgs.append(index_docx_file(path, theme, subtheme))
        else:
            msgs.append(f"⚠️ Unsupported: {ext}")
    return "\n".join(msgs) or "Nothing indexed."


def index_hf_dataset(dataset_name: str, text_col: str, source_col: str = "",
                     theme: str = "", subtheme: str = ""):
    try:
        import datasets as ds
        dataset = ds.load_dataset(dataset_name, split="train")
        texts, metas = [], []
        for row in dataset:
            t = row.get(text_col, "")
            if not t:
                continue
            src = row.get(source_col, dataset_name) if source_col else dataset_name
            texts.append(str(t))
            metas.append({"source": str(src), "type": "hf_dataset",
                          "theme": theme, "subtheme": subtheme})
        k = index_texts(texts, metas)
        return f"✅ {k} chunks from '{dataset_name}'", get_doc_table()
    except Exception as e:
        return f"❌ {e}", get_doc_table()


_DOC_TABLE_CACHE = None
_DOC_TABLE_CACHE_COUNT = -1


def invalidate_doc_table_cache():
    global _DOC_TABLE_CACHE, _DOC_TABLE_CACHE_COUNT
    _DOC_TABLE_CACHE = None
    _DOC_TABLE_CACHE_COUNT = -1


def get_doc_table(force_refresh: bool = False) -> list:
    global _DOC_TABLE_CACHE, _DOC_TABLE_CACHE_COUNT
    try:
        col = models.get_chroma_collection()
        count = col.count()
    except Exception:
        return []

    if count == 0:
        _DOC_TABLE_CACHE = []
        _DOC_TABLE_CACHE_COUNT = 0
        return []

    if not force_refresh and _DOC_TABLE_CACHE is not None and _DOC_TABLE_CACHE_COUNT == count:
        return _DOC_TABLE_CACHE

    result = col.get(include=["metadatas"])
    agg = defaultdict(lambda: {"type": "", "pages": set(), "chunks": 0,
                               "theme": "", "subtheme": ""})
    for m in result["metadatas"]:
        src = m.get("source", "unknown")
        agg[src]["type"]   = m.get("type", "unknown")
        agg[src]["chunks"] += 1
        agg[src]["theme"]   = m.get("theme", "")
        agg[src]["subtheme"] = m.get("subtheme", "")
        if m.get("page"):
            agg[src]["pages"].add(m["page"])

    table = [[src, info["type"],
             str(len(info["pages"])) if info["pages"] else "—",
             info["chunks"],
             info["theme"],
             info["subtheme"]]
            for src, info in sorted(agg.items())]

    _DOC_TABLE_CACHE = table
    _DOC_TABLE_CACHE_COUNT = count
    return table


def delete_selected_sources(selected_rows: list, doc_table_data: list) -> tuple:
    invalidate_doc_table_cache()
    if not selected_rows:
        return get_doc_table(force_refresh=True), "⚠️ No rows selected."
    
    current_table = get_doc_table(force_refresh=True)
    rows_to_use = doc_table_data if (doc_table_data and len(doc_table_data) > 0) else current_table

    col, deleted = models.get_chroma_collection(), []
    for row_idx in selected_rows:
        if row_idx >= len(rows_to_use):
            continue
        src = rows_to_use[row_idx][0]
        result = col.get(where={"source": src}, include=["metadatas"])
        if result["ids"]:
            col.delete(ids=result["ids"])
            deleted.append(f"'{src}' ({len(result['ids'])} chunks)")

    invalidate_doc_table_cache()
    msg = ("🗑️ Deleted: " + ", ".join(deleted)) if deleted else "⚠️ Nothing deleted."
    return get_doc_table(force_refresh=True), msg


def clear_index() -> tuple:
    import shutil
    import chromadb
    invalidate_doc_table_cache()
    
    # 1. Delete ChromaDB collections
    try:
        client = chromadb.PersistentClient(path=mr.CHROMA_PERSIST_DIR)
        for col in client.list_collections():
            try:
                client.delete_collection(col.name)
            except Exception:
                pass
    except Exception:
        pass
        
    models.reset_chroma_collection()
    models.get_chroma_collection()

    # 2. Delete visual index if present
    if Path(mr.VISUAL_INDEX_DIR).exists():
        try:
            shutil.rmtree(mr.VISUAL_INDEX_DIR)
        except Exception:
            pass

    return [], "🗑️ All documents cleared."


def get_index_stats(lang_key: str = "en") -> tuple[str, str]:
    l = LANGUAGES[lang_key]
    n       = models.get_chroma_collection().count()
    vis_str = l["err_visual_ready"] if (Path(mr.VISUAL_INDEX_DIR) / "main").exists() else l["err_empty_visual"]
    msg = l["err_status_bar"].format(n=n, vis=vis_str, dev=DEVICE.upper())
    return msg, msg


def retrieve_context(query: str, theme: str = "", subtheme: str = "") -> tuple[str, list[str]]:
    col = models.get_chroma_collection()
    if col.count() == 0:
        return "", []
    where_filter = {}
    if theme and subtheme:
        where_filter = {"$and": [{"theme": {"$eq": theme}}, {"subtheme": {"$eq": subtheme}}]}
    elif theme:
        where_filter = {"theme": {"$eq": theme}}
    elif subtheme:
        where_filter = {"subtheme": {"$eq": subtheme}}
    try:
        results = col.query(query_embeddings=models.encode_texts([query]),
                            n_results=min(mr.TOP_K, col.count()),
                            where=where_filter or None)
    except Exception as e:
        if "dimension" in str(e).lower():
            raise RuntimeError(f"{_DIMENSION_MISMATCH_HINT}\n\nOriginal error: {e}") from e
        raise
    docs  = results["documents"][0]
    metas = results["metadatas"][0]
    if not docs:
        return "", []
    context = "\n\n".join(f"[{m.get('source','?')}]\n{d}"
                          for d, m in zip(docs, metas))
    sources = list({m.get("source", "?") for m in metas})
    return context, sources


class RetrieverTool(Tool):
    """smolagents Tool wrapper around retrieve_context(), for agentic RAG
    (see rag_agent.py). Unlike the plain RAG Chat path, which always
    retrieves context before calling the LLM, this lets a CodeAgent decide
    for itself whether/when to search the knowledge base, and call it more
    than once (e.g. to refine a search) before giving a final answer.
    """
    name = "retriever"
    description = (
        "Uses semantic search over the indexed knowledge base (ChromaDB) to "
        "retrieve the document chunks most relevant to a query. This is the "
        "ONLY source of information you are permitted to use to answer the "
        "user — never supplement it with your own general knowledge. Call "
        "this before answering any question. It returns a clear 'no relevant "
        "documents found' message if the knowledge base is empty or has "
        "nothing relevant — treat that as a real answer (there is nothing to "
        "report), not as a reason to fall back on what you already know. "
        "Every returned chunk is tagged with its source filename in "
        "brackets, e.g. '[report.pdf]' — cite that exact tag in-text "
        "immediately after any claim you draw from it."
    )
    inputs = {
        "query": {
            "type": "string",
            "description": (
                "The search query. Prefer an affirmative statement close to "
                "the target content (e.g. 'steps to push a model to the "
                "Hub') rather than a literal question."
            ),
        }
    }
    output_type = "string"

    def __init__(self, theme: str = "", subtheme: str = "", **kwargs):
        super().__init__(**kwargs)
        self._theme = theme
        self._subtheme = subtheme
        # Self-tracked usage stats — used by rag_agent.py to verify (after
        # agent.run() returns) that the model actually searched the
        # knowledge base and actually found something, rather than trying
        # to introspect smolagents' internal step/memory structure, which
        # varies across versions and previously caused false negatives
        # (blocking correctly-grounded answers because the introspection
        # didn't match this installed version's real internals).
        self.call_count  = 0
        self.found_count = 0
        # Every unique source name actually returned by a successful
        # retrieval this run — lets chat.py print a guaranteed-accurate
        # References list after the agent answers, independent of whether
        # the model remembered to write its own in-text citations (same
        # "track it ourselves, don't just trust the model" reasoning as
        # call_count/found_count above).
        self.sources_used = set()

    def reset_stats(self):
        self.call_count  = 0
        self.found_count = 0
        self.sources_used = set()

    def forward(self, query: str) -> str:
        assert isinstance(query, str), "Your search query must be a string"
        self.call_count += 1
        context, sources = retrieve_context(query, self._theme, self._subtheme)
        if not context:
            return "No relevant documents found — the knowledge base may be empty."
        self.found_count += 1
        self.sources_used.update(sources)
        return f"Retrieved documents (sources: {', '.join(sources)}):\n\n{context}"
