"""
ingest.py — Clean, chunk, and embed Lit Hum texts.
Run once to produce chunks.json and embeddings.npy.
"""

import json
import re
import numpy as np
from pathlib import Path
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer

WORKS_DIR = Path(__file__).parent / "Works"
OUT_CHUNKS = Path(__file__).parent / "chunks.json"
OUT_EMBEDDINGS = Path(__file__).parent / "embeddings.npy"
CHUNK_WORDS = 150  # target chunk size


# ---------------------------------------------------------------------------
# Dante Inferno — plain text
# ---------------------------------------------------------------------------

def load_dante():
    raw = (WORKS_DIR / "DanteInferno.txt").read_text(encoding="utf-8")

    # Keep only the poem: starts at "THE INFERNO." before CANTO I
    start = raw.find("THE INFERNO.")
    if start == -1:
        start = raw.find("CANTO I.")
    # End at Gutenberg footer
    end_marker = "*** END OF THE PROJECT GUTENBERG"
    end = raw.find(end_marker)
    poem = raw[start:end] if end != -1 else raw[start:]

    # Split into cantos
    canto_pattern = re.compile(r"^\s*CANTO\s+([\w]+)\.", re.MULTILINE)
    splits = list(canto_pattern.finditer(poem))

    chunks = []
    for i, match in enumerate(splits):
        canto_name = match.group(1)
        body_start = match.end()
        body_end = splits[i + 1].start() if i + 1 < len(splits) else len(poem)
        canto_text = poem[body_start:body_end]

        # Strip full footnote/illustration lines
        lines = canto_text.splitlines()
        clean_lines = []
        for line in lines:
            stripped = line.strip()
            if re.match(r"^\[\d+\]", stripped):
                continue
            if stripped.startswith("[Illustration"):
                continue
            clean_lines.append(stripped)

        canto_text = " ".join(clean_lines)
        # Remove inline footnote references: [160], [NNN]
        canto_text = re.sub(r"\[\d+\]", "", canto_text)
        # Remove standalone line numbers (e.g. "  10  " between verse lines)
        canto_text = re.sub(r"\s{2,}\d+\s{2,}", " ", canto_text)
        canto_text = re.sub(r"\s+", " ", canto_text).strip()

        # Convert Roman numeral to integer label
        location = f"Canto {canto_name}"
        for chunk in make_chunks(canto_text, "Inferno", location):
            chunks.append(chunk)

    print(f"Dante: {len(chunks)} chunks")
    return chunks


# ---------------------------------------------------------------------------
# Augustine's Confessions — HTML
# ---------------------------------------------------------------------------

def load_augustine():
    html = (WORKS_DIR / "AustinesConfessions.html").read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    # Remove script/style
    for tag in soup(["script", "style"]):
        tag.decompose()

    chunks = []
    current_book = "Book I"

    # Walk h2 elements (BOOK I … BOOK XIII) and collect text between them
    h2s = soup.find_all("h2")
    for i, h2 in enumerate(h2s):
        book_text = h2.get_text(strip=True)
        # Only process BOOK headings
        if not re.match(r"BOOK\s+[IVXLC]+", book_text, re.IGNORECASE):
            continue

        # Normalise: "BOOK I" → "Book I"
        book_label = book_text.title()
        current_book = book_label

        # Collect all <p> tags between this h2 and the next h2
        sibling = h2.find_next_sibling()
        paragraphs = []
        while sibling and sibling.name != "h2":
            if sibling.name == "p":
                text = sibling.get_text(separator=" ", strip=True)
                if text:
                    paragraphs.append(text)
            sibling = sibling.find_next_sibling()

        body = " ".join(paragraphs)
        body = re.sub(r"\s+", " ", body).strip()

        for chunk in make_chunks(body, "Confessions", current_book):
            chunks.append(chunk)

    print(f"Augustine: {len(chunks)} chunks")
    return chunks


# ---------------------------------------------------------------------------
# Chunking helper
# ---------------------------------------------------------------------------

def make_chunks(text, source, location):
    words = text.split()
    chunks = []
    for i in range(0, len(words), CHUNK_WORDS):
        segment = " ".join(words[i : i + CHUNK_WORDS])
        if len(segment.split()) < 20:  # skip tiny trailing fragments
            continue
        chunks.append({"text": segment, "source": source, "location": location})
    return chunks


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    all_chunks = []
    all_chunks.extend(load_dante())
    all_chunks.extend(load_augustine())

    print(f"Total chunks: {len(all_chunks)}")

    print("Loading embedding model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    texts = [c["text"] for c in all_chunks]
    print("Computing embeddings...")
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)

    OUT_CHUNKS.write_text(json.dumps(all_chunks, indent=2, ensure_ascii=False))
    np.save(OUT_EMBEDDINGS, embeddings)

    print(f"Saved {len(all_chunks)} chunks → {OUT_CHUNKS}")
    print(f"Saved embeddings shape {embeddings.shape} → {OUT_EMBEDDINGS}")


if __name__ == "__main__":
    main()
