"""
app.py — Flask RAG server for Ask Lit Hum.
"""

import json
import os
import re
from dotenv import load_dotenv
load_dotenv()
import numpy as np
from pathlib import Path
from flask import Flask, request, jsonify, render_template
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from openai import OpenAI

BASE = Path(__file__).parent
CHUNKS_PATH = BASE / "chunks.json"
EMBEDDINGS_PATH = BASE / "embeddings.npy"
TOP_K = 5

app = Flask(__name__)

# ---------------------------------------------------------------------------
# CORS — allow Vite dev server (port 8080) and any local origin
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
# Load data at startup
# ---------------------------------------------------------------------------

print("Loading chunks and embeddings...")
chunks = json.loads(CHUNKS_PATH.read_text())
embeddings = np.load(EMBEDDINGS_PATH)

print("Loading embedding model...")
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

print(f"Ready — {len(chunks)} chunks loaded.")

# ---------------------------------------------------------------------------
# Author metadata
# ---------------------------------------------------------------------------

SOURCE_META = {
    "Inferno": {
        "author": "Dante Alighieri",
        "responder_name": "Dante",
        "descriptor": "Responding through themes of journey, justice, and descent into the self",
        "era": "14th Century",
    },
    "Confessions": {
        "author": "Saint Augustine",
        "responder_name": "Augustine",
        "descriptor": "Responding through themes of memory, restlessness, and the seeking heart",
        "era": "4th Century",
    },
}


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def retrieve(query: str, top_k: int = TOP_K):
    query_vec = embed_model.encode([query], convert_to_numpy=True)
    sims = cosine_similarity(query_vec, embeddings)[0]
    top_indices = np.argsort(sims)[::-1][:top_k]
    results = []
    for idx in top_indices:
        results.append({
            "text": chunks[idx]["text"],
            "source": chunks[idx]["source"],
            "location": chunks[idx]["location"],
            "score": float(sims[idx]),
        })
    return results


# ---------------------------------------------------------------------------
# Generation — structured JSON response
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You answer questions by fully inhabiting the voice of the speaker identified in the passages \
(either Dante the pilgrim-poet, or Augustine the bishop and confessor).
Speak as that person — use their characteristic concerns, their diction, their way of seeing. \
Dante moves through image and moral geography; Augustine addresses God and wrestles inwardly. \
Do not speak as a scholar about them. Speak as them.
Use ONLY the provided passages as your source material — no outside knowledge.
You MUST respond with valid JSON matching this exact structure:
{
  "answer": "<the speaker's response, use \\n to separate paragraphs>",
  "themes": ["Theme1", "Theme2", "Theme3", "Theme4"],
  "evidence_relevance": ["<short tag for passage 1>", "<short tag for passage 2>", ...]
}
- answer: open immediately with a direct, substantive response in the speaker's own voice. \
  No preamble. 2 paragraphs maximum. Tight and literary.
- themes: 3-5 single-word or short-phrase thematic labels.
- evidence_relevance: one short relevance label (2-4 words) per passage, in order.
Do not include anything outside the JSON object."""


def build_user_prompt(question: str, passages: list) -> str:
    passage_block = "\n\n".join(
        f"[{i+1}] ({p['source']}, {p['location']})\n{p['text']}"
        for i, p in enumerate(passages)
    )
    return (
        f"Question: {question}\n\n"
        f"Passages:\n{passage_block}"
    )


def pick_responder(passages: list) -> dict:
    """Choose the dominant source from the top passages."""
    counts = {}
    for p in passages:
        counts[p["source"]] = counts.get(p["source"], 0) + 1
    dominant = max(counts, key=counts.get)
    meta = SOURCE_META[dominant]
    return {
        "name": meta["responder_name"],
        "work": dominant if dominant != "Inferno" else "The Inferno",
        "author": meta["author"],
        "descriptor": meta["descriptor"],
        "era": meta["era"],
    }


def generate(question: str, passages: list) -> dict:
    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        max_tokens=1500,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(question, passages)},
        ],
    )
    raw = response.choices[0].message.content.strip()

    # Extract JSON even if the model wraps it in markdown fences
    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if json_match:
        raw = json_match.group(0)

    llm_data = json.loads(raw)

    answer = llm_data.get("answer", "")
    themes = llm_data.get("themes", [])
    relevance_tags = llm_data.get("evidence_relevance", [])

    # Build evidence cards
    evidence = []
    for i, p in enumerate(passages):
        meta = SOURCE_META[p["source"]]
        tag = relevance_tags[i] if i < len(relevance_tags) else "Relevant Passage"
        # Trim excerpt to ~200 chars at a sentence boundary
        text = p["text"]
        if len(text) > 220:
            cut = text[:220]
            last_period = cut.rfind(".")
            text = cut[: last_period + 1] if last_period > 100 else cut + "…"
        evidence.append({
            "work": p["source"] if p["source"] != "Inferno" else "The Inferno",
            "author": meta["author"],
            "section": p["location"],
            "excerpt": text,
            "relevance": tag,
        })

    responder = pick_responder(passages)

    return {
        "responder": responder,
        "answer": answer,
        "themes": themes,
        "evidence": evidence,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(force=True)
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "No question provided."}), 400

    try:
        passages = retrieve(question)
        result = generate(question, passages)
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5001, host="127.0.0.1")
