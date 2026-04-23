"""
granite_adapters.py — Thin wrappers around IBM Granite RAG Library adapters
(via Mellea), exposing the six RAG intrinsics as plain Python functions.

Pipeline stage of each adapter:
    rewrite_query         pre-retrieval
    clarify_query         pre-retrieval / pre-generation
    score_relevance       pre-generation (per passage)
    check_answerability   pre-generation
    hallucination_score   post-generation
    find_citations        post-generation

The backend (granite-4.0-micro + adapters) is loaded lazily on first call.
If `GRANITE_DISABLED=1`, every wrapper returns a permissive default so the
pipeline can run adapter-less during development.
"""
from __future__ import annotations

import os
import threading
from typing import Any

from mellea.backends.huggingface import LocalHFBackend
from mellea.stdlib.components import Message
from mellea.stdlib.components.docs.document import Document
from mellea.stdlib.components.intrinsic import rag
from mellea.stdlib.context import ChatContext


BASE_MODEL = "ibm-granite/granite-4.0-micro"
DISABLED = os.environ.get("GRANITE_DISABLED") == "1"

_backend: LocalHFBackend | None = None
_lock = threading.Lock()


def _get_backend() -> LocalHFBackend:
    """Lazily instantiate the LocalHFBackend. First call downloads ~6GB."""
    global _backend
    if _backend is None:
        with _lock:
            if _backend is None:
                print(f"[granite] loading base model {BASE_MODEL} (first call is slow)...")
                _backend = LocalHFBackend(model_id=BASE_MODEL)
                print("[granite] backend ready.")
    return _backend


def _empty_context() -> ChatContext:
    """Single-turn context (no prior conversation)."""
    return ChatContext()


def _docs(passages: list[dict]) -> list[Document]:
    return [Document(doc_id=str(p["id"]), text=p["text"]) for p in passages]


# ---------------------------------------------------------------------------
# Pre-retrieval
# ---------------------------------------------------------------------------

def rewrite_query(question: str) -> str:
    """Rewrite the user question into a standalone form for retrieval.

    For a single-turn app the rewrite is usually a no-op, but the adapter
    still normalizes phrasing (spelling, pronouns) which can help retrieval.
    """
    if DISABLED:
        return question
    try:
        return rag.rewrite_question(question, _empty_context(), _get_backend())
    except Exception as e:
        print(f"[granite] rewrite_query failed: {e!r} — falling back to original")
        return question


# ---------------------------------------------------------------------------
# Pre-generation
# ---------------------------------------------------------------------------

def score_relevance(question: str, passage: dict) -> float:
    """Score a single passage's relevance to the query (0.0–1.0)."""
    if DISABLED:
        return 1.0
    try:
        doc = Document(doc_id=str(passage["id"]), text=passage["text"])
        return float(rag.check_context_relevance(question, doc, _empty_context(), _get_backend()))
    except Exception as e:
        print(f"[granite] score_relevance failed: {e!r}")
        return 1.0


def check_answerability(question: str, passages: list[dict]) -> float:
    """Overall answerability of the query given all retrieved passages (0.0–1.0)."""
    if DISABLED:
        return 1.0
    try:
        return float(rag.check_answerability(
            question, _docs(passages), _empty_context(), _get_backend()
        ))
    except Exception as e:
        print(f"[granite] check_answerability failed: {e!r}")
        return 1.0


# ---------------------------------------------------------------------------
# Post-generation
# ---------------------------------------------------------------------------

def hallucination_score(answer: str, passages: list[dict]) -> float:
    """Hallucination-risk score for the answer (0.0–1.0, higher = more risk)."""
    if DISABLED:
        return 0.0
    try:
        return float(rag.flag_hallucinated_content(
            answer, _docs(passages), _empty_context(), _get_backend()
        ))
    except Exception as e:
        print(f"[granite] hallucination_score failed: {e!r}")
        return 0.0


def find_citations(answer: str, passages: list[dict]) -> list[dict[str, Any]]:
    """Return a list of {response_begin, response_end, citation_doc_id, ...} dicts."""
    if DISABLED:
        return []
    try:
        return list(rag.find_citations(
            answer, _docs(passages), _empty_context(), _get_backend()
        ))
    except Exception as e:
        print(f"[granite] find_citations failed: {e!r}")
        return []


# ---------------------------------------------------------------------------
# Warmup entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Run this once to pre-download granite-4.0-micro and all 6 adapters,
    # so the Flask server's first request doesn't block on downloads.
    print("Warming up Granite RAG backend...")
    b = _get_backend()
    sample_q = "What does the text say about memory?"
    sample_passage = {"id": "warmup", "text": "Memory is a vast chamber of the mind."}
    print("  rewrite_query ...")
    print("    ->", rewrite_query(sample_q))
    print("  score_relevance ...")
    print("    ->", score_relevance(sample_q, sample_passage))
    print("  check_answerability ...")
    print("    ->", check_answerability(sample_q, [sample_passage]))
    print("  hallucination_score ...")
    print("    ->", hallucination_score("Memory is important.", [sample_passage]))
    print("  find_citations ...")
    print("    ->", find_citations("Memory is important.", [sample_passage]))
    print("Warmup complete.")
