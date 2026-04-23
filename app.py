"""
app.py — Ask Lit Hum (hybrid Mistral + Granite RAG)

Pipeline:
    user question
      |--> granite.rewrite_query          (QR, pre-retrieval)
      |--> cosine retrieve top-N chunks
      |--> granite.score_relevance         (CR, per passage, keep top-K)
      |--> granite.check_answerability     (AD, gate)
      |--> Mistral via Ollama              (in-character generation)
      |--> granite.hallucination_score     (HD)
      |--> granite.find_citations          (CG)
      |--> structured JSON to the frontend
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

import numpy as np
import ollama
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

import granite_adapters

load_dotenv()

BASE = Path(__file__).parent
CHUNKS_PATH = BASE / "chunks.json"
EMBEDDINGS_PATH = BASE / "embeddings.npy"

# Retrieval knobs
RETRIEVE_N = 6      # pre-filter pool (smaller = less Granite memory contention)
TOP_K = 3           # passages shown to the generator (smaller prompt = faster gen)
CR_KEEP_THRESHOLD = 0.05  # soft floor (unused; CR is display-only when enabled)

# Generation knobs
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "mistral:7b-instruct-q4_0")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_TIMEOUT = 120

# Adapter toggle (useful during dev): GRANITE_STAGES="QR,CR,AD,HD,CG"
# Default keeps only the post-generation signals that are informative for a
# thematic/interpretive app. QR rarely rewrites single-turn questions; CR and
# AD are factual-QA classifiers that score thematic matches near zero.
_default_stages = "CG"
ENABLED_STAGES = set(
    s.strip().upper() for s in os.environ.get("GRANITE_STAGES", _default_stages).split(",") if s.strip()
)

app = Flask(__name__)


# ---------------------------------------------------------------------------
# CORS — allow Vite dev server and any local origin
# ---------------------------------------------------------------------------

@app.after_request
def add_cors(response):
    origin = request.headers.get("Origin", "")
    if origin.startswith("http://localhost") or origin.startswith("http://127.0.0.1"):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.route("/ask", methods=["OPTIONS"])
def ask_preflight():
    return "", 204


# ---------------------------------------------------------------------------
# Startup: retrieval assets + Ollama client
# ---------------------------------------------------------------------------

print(f"[boot] loading chunks + embeddings from {BASE} ...")
chunks = json.loads(CHUNKS_PATH.read_text())
embeddings = np.load(EMBEDDINGS_PATH)
print(f"[boot] {len(chunks)} chunks, embeddings shape {embeddings.shape}")

print("[boot] loading MiniLM embedder ...")
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

print(f"[boot] Ollama host = {OLLAMA_HOST}, model = {OLLAMA_MODEL}")
ollama_client = ollama.Client(host=OLLAMA_HOST)

print(f"[boot] Granite stages enabled: {sorted(ENABLED_STAGES) or 'none'}")
print("[boot] ready.")


# ---------------------------------------------------------------------------
# Speaker / work metadata (drives responder cards + persona system prompt)
# ---------------------------------------------------------------------------

SOURCE_META: dict[str, dict] = {
    "Inferno": {
        "display": "The Inferno",
        "author": "Dante Alighieri",
        "responder_name": "Dante",
        "descriptor": "Responding through themes of journey, justice, and descent into the self",
        "era": "14th Century",
        "voice_guide": (
            "Dante the pilgrim-poet. Speak in the first person as one who has walked "
            "through Hell and returned. Use image and moral geography; reach for the "
            "particular — a face, a circle, a punishment — to illuminate the universal."
        ),
    },
    "Confessions": {
        "display": "Confessions",
        "author": "Saint Augustine",
        "responder_name": "Augustine",
        "descriptor": "Responding through themes of memory, restlessness, and the seeking heart",
        "era": "4th Century",
        "voice_guide": (
            "Augustine the bishop and confessor. Address God even when speaking to the asker. "
            "Turn questions inward; wrestle openly with your own disordered desires and "
            "return to the restless heart that finds no rest but in Him."
        ),
    },
    "Pride and Prejudice": {
        "display": "Pride and Prejudice",
        "author": "Jane Austen",
        "responder_name": "Elizabeth Bennet",
        "descriptor": "Responding through themes of wit, judgement, and the slow correction of first impressions",
        "era": "19th Century",
        "voice_guide": (
            "Elizabeth Bennet, observant and wry. Speak with Austen's poise — polite but "
            "ironic, fond of the neat turn of phrase and the gentle puncturing of vanity. "
            "Take seriously the work of re-examining one's own prejudices."
        ),
    },
    "King Lear": {
        "display": "King Lear",
        "author": "William Shakespeare",
        "responder_name": "King Lear",
        "descriptor": "Responding through themes of pride, loyalty, and the storm within",
        "era": "17th Century",
        "voice_guide": (
            "Lear, old and late-learning. Speak in the cadence of Shakespearean blank-verse "
            "prose — direct, elemental, self-accusing. Know the cost of your vanity; speak "
            "from the heath, not from the court."
        ),
    },
    "Montaigne Essays": {
        "display": "Essays",
        "author": "Michel de Montaigne",
        "responder_name": "Montaigne",
        "descriptor": "Responding through themes of self-inquiry, skepticism, and the examined ordinary life",
        "era": "16th Century",
        "voice_guide": (
            "Montaigne in his tower, in essai — to try, to weigh. Speak in the first person "
            "with digressive ease: circle the question, quote yourself against yourself, "
            "hold every certainty loosely under the standing question, 'Que sais-je?' "
            "Ground the argument in the body, in custom, in homely example."
        ),
    },
    "Anna Karenina": {
        "display": "Anna Karenina",
        "author": "Leo Tolstoy",
        "responder_name": "Anna Karenina",
        "descriptor": "Responding through themes of passion, society, and the search for meaning amid love and loss",
        "era": "19th Century",
        "voice_guide": (
            "Anna Karenina, luminous and divided. Speak as one who has loved too much and "
            "lived under the gaze of society, caught between desire and duty. Prefer feeling "
            "over argument; let contradiction and longing shadow every plain sentence."
        ),
    },
}


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def retrieve(query: str, n: int = RETRIEVE_N) -> list[dict]:
    vec = embed_model.encode([query], convert_to_numpy=True)
    sims = cosine_similarity(vec, embeddings)[0]
    top = np.argsort(sims)[::-1][:n]
    out = []
    for idx in top:
        c = chunks[int(idx)]
        out.append({
            "id": int(idx),
            "text": c["text"],
            "source": c["source"],
            "location": c["location"],
            "retrieval_score": float(sims[int(idx)]),
        })
    return out


# ---------------------------------------------------------------------------
# Generation (Mistral via Ollama)
# ---------------------------------------------------------------------------

def pick_responder(passages: list[dict]) -> dict:
    """Dominant work among the top passages becomes the speaker."""
    counts: dict[str, int] = {}
    for p in passages:
        counts[p["source"]] = counts.get(p["source"], 0) + 1
    dominant = max(counts, key=counts.get)
    meta = SOURCE_META[dominant]
    return {
        "name": meta["responder_name"],
        "work": meta["display"],
        "author": meta["author"],
        "descriptor": meta["descriptor"],
        "era": meta["era"],
        "_source_key": dominant,
    }


def build_system_prompt(responder: dict) -> str:
    meta = SOURCE_META[responder["_source_key"]]
    return (
        f"You are answering as {meta['responder_name']}. {meta['voice_guide']}\n\n"
        "Use ONLY the provided passages as source material; no outside knowledge. "
        "Do not speak as a scholar about the character — speak AS the character.\n\n"
        "You MUST respond with valid JSON matching exactly this schema:\n"
        "{\n"
        '  "answer": "<two paragraphs max, in the speaker\'s own voice, \\n between paragraphs>",\n'
        '  "themes": ["Theme1", "Theme2", "Theme3", "Theme4"],\n'
        '  "evidence_relevance": ["<2-4 word label for passage 1>", "..."]\n'
        "}\n"
        "- answer: open directly in character. No preamble. Tight and literary.\n"
        "- themes: 3-5 single-word or short thematic labels.\n"
        "- evidence_relevance: exactly one short tag per passage, in order.\n"
        "Return nothing outside the JSON object."
    )


def build_user_prompt(question: str, passages: list[dict]) -> str:
    block = "\n\n".join(
        f"[{i+1}] ({SOURCE_META[p['source']]['display']}, {p['location']})\n{p['text']}"
        for i, p in enumerate(passages)
    )
    return f"Question: {question}\n\nPassages:\n{block}"


def generate_with_mistral(question: str, passages: list[dict], responder: dict) -> dict:
    t0 = time.time()
    resp = ollama_client.chat(
        model=OLLAMA_MODEL,
        format="json",
        options={"temperature": 0.7, "num_predict": 600},
        keep_alive=0,  # unload Mistral right after; Granite post-processing needs the MPS back
        messages=[
            {"role": "system", "content": build_system_prompt(responder)},
            {"role": "user", "content": build_user_prompt(question, passages)},
        ],
    )
    print(f"[ollama] generation took {time.time()-t0:.1f}s")
    raw = resp["message"]["content"].strip()
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        raw = m.group(0)
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Response assembly
# ---------------------------------------------------------------------------

def trim_excerpt(text: str, limit: int = 220) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit]
    last = cut.rfind(".")
    return cut[: last + 1] if last > 100 else cut + "..."


def build_evidence(passages: list[dict], relevance_tags: list[str]) -> list[dict]:
    evidence = []
    for i, p in enumerate(passages):
        meta = SOURCE_META[p["source"]]
        tag = relevance_tags[i] if i < len(relevance_tags) else "Relevant Passage"
        evidence.append({
            "work": meta["display"],
            "author": meta["author"],
            "section": p["location"],
            "excerpt": trim_excerpt(p["text"]),
            "relevance": tag,
            "retrieval_score": round(p["retrieval_score"], 3),
            "relevance_score": round(p.get("relevance_score", 1.0), 3),
        })
    return evidence


# ---------------------------------------------------------------------------
# Main /ask endpoint
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({
        "chunks": len(chunks),
        "embedding_shape": list(embeddings.shape),
        "ollama_model": OLLAMA_MODEL,
        "granite_stages": sorted(ENABLED_STAGES),
    })


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(force=True)
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "No question provided."}), 400

    try:
        pipeline: dict = {"question": question}

        # 1. QR — pre-retrieval query rewrite
        if "QR" in ENABLED_STAGES:
            t = time.time()
            rewritten = granite_adapters.rewrite_query(question)
            pipeline["rewritten_query"] = rewritten
            print(f"[pipeline] QR {time.time()-t:.1f}s -> {rewritten!r}")
        else:
            rewritten = question

        # 2. Retrieval — cosine similarity picks the candidate pool.
        pool = retrieve(rewritten, RETRIEVE_N)
        if not pool:
            return jsonify({"error": "No passages retrieved."}), 200

        # Top-K by cosine is our generator input.
        passages = pool[:TOP_K]

        # 3. CR — score top-K passages for display (not as a filter: Granite's CR
        # treats "relevance" as factual QA match, which under-scores thematic
        # resonance. We keep CR as transparency in the UI, not as a gate.)
        if "CR" in ENABLED_STAGES:
            t = time.time()
            for p in passages:
                p["relevance_score"] = granite_adapters.score_relevance(rewritten, p)
            print(f"[pipeline] CR {time.time()-t:.1f}s")

        # 4. AD — answerability gate
        if "AD" in ENABLED_STAGES:
            t = time.time()
            ans_score = granite_adapters.check_answerability(rewritten, passages)
            pipeline["answerability_score"] = round(ans_score, 3)
            print(f"[pipeline] AD {time.time()-t:.1f}s -> {ans_score:.2f}")
        else:
            ans_score = 1.0

        # 5. Persona selection + Mistral generation
        responder = pick_responder(passages)
        llm_data = generate_with_mistral(rewritten, passages, responder)
        answer = llm_data.get("answer", "")
        themes = llm_data.get("themes", [])
        relevance_tags = llm_data.get("evidence_relevance", [])

        # 6. HD — hallucination check
        if "HD" in ENABLED_STAGES:
            t = time.time()
            hd = granite_adapters.hallucination_score(answer, passages)
            pipeline["hallucination_score"] = round(hd, 3)
            print(f"[pipeline] HD {time.time()-t:.1f}s -> {hd:.2f}")

        # 7. CG — citation generation
        citations: list[dict] = []
        if "CG" in ENABLED_STAGES:
            t = time.time()
            raw_citations = granite_adapters.find_citations(answer, passages)
            for c in raw_citations:
                doc_id = str(c.get("citation_doc_id", ""))
                try:
                    p = next(p for p in passages if str(p["id"]) == doc_id)
                    src_meta = SOURCE_META[p["source"]]
                    citations.append({
                        "response_text": c.get("response_text", ""),
                        "response_begin": c.get("response_begin"),
                        "response_end": c.get("response_end"),
                        "citation_text": c.get("citation_text", ""),
                        "work": src_meta["display"],
                        "section": p["location"],
                    })
                except StopIteration:
                    continue
            print(f"[pipeline] CG {time.time()-t:.1f}s -> {len(citations)} citations")

        # Drop the internal key before returning
        responder_public = {k: v for k, v in responder.items() if not k.startswith("_")}

        return jsonify({
            "responder": responder_public,
            "answer": answer,
            "themes": themes,
            "evidence": build_evidence(passages, relevance_tags),
            "citations": citations,
            "pipeline": pipeline,
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=False, port=5001, host="127.0.0.1")
