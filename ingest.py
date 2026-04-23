"""
ingest.py — Clean, chunk, and embed Lit Hum texts.
Run once to produce chunks.json and embeddings.npy.

Sources (all from Project Gutenberg):
  - Dante, Inferno                       (PG  8800, plain text)
  - Augustine, Confessions               (local HTML)
  - Austen, Pride and Prejudice          (PG  1342)
  - Shakespeare, King Lear (modernized)  (PG   100, extracted from complete works)
  - Tolstoy, Anna Karenina (Garnett)     (PG  1399)
  - Montaigne, Essays (Cotton/Hazlitt)   (PG  3600, 8 selected essays)
"""

import json
import re
import unicodedata
import numpy as np
from pathlib import Path
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer

WORKS_DIR = Path(__file__).parent / "Works"
OUT_CHUNKS = Path(__file__).parent / "chunks.json"
OUT_EMBEDDINGS = Path(__file__).parent / "embeddings.npy"
CHUNK_WORDS = 150
MIN_CHUNK_WORDS = 20


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

GUTENBERG_END = re.compile(r"\*\*\*\s*END OF (?:THE |THIS )?PROJECT GUTENBERG", re.IGNORECASE)
GUTENBERG_START = re.compile(r"\*\*\*\s*START OF (?:THE |THIS )?PROJECT GUTENBERG.*?\*\*\*", re.IGNORECASE)


def strip_gutenberg(raw: str) -> str:
    """Strip Project Gutenberg header and footer if present."""
    start = GUTENBERG_START.search(raw)
    if start:
        raw = raw[start.end():]
    end = GUTENBERG_END.search(raw)
    if end:
        raw = raw[:end.start()]
    return raw


def normalize(text: str) -> str:
    """Normalize unicode punctuation, collapse whitespace."""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2014", "--").replace("\u2013", "-")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def make_chunks(text: str, source: str, location: str):
    words = text.split()
    out = []
    for i in range(0, len(words), CHUNK_WORDS):
        segment = " ".join(words[i : i + CHUNK_WORDS])
        if len(segment.split()) < MIN_CHUNK_WORDS:
            continue
        out.append({"text": segment, "source": source, "location": location})
    return out


# ---------------------------------------------------------------------------
# Dante — Inferno (unchanged, plain-text Gutenberg)
# ---------------------------------------------------------------------------

def load_dante():
    raw = (WORKS_DIR / "DanteInferno.txt").read_text(encoding="utf-8")
    start = raw.find("THE INFERNO.")
    if start == -1:
        start = raw.find("CANTO I.")
    # Cut before the index section (appears at the end after Canto XXXIV).
    index_marker = raw.find("INDEX OF PROPER NAMES")
    end_marker = "*** END OF THE PROJECT GUTENBERG"
    end_candidates = [i for i in (index_marker, raw.find(end_marker)) if i != -1]
    end = min(end_candidates) if end_candidates else len(raw)
    poem = raw[start:end]

    canto_pattern = re.compile(r"^\s*CANTO\s+([\w]+)\.", re.MULTILINE)
    splits = list(canto_pattern.finditer(poem))

    chunks = []
    for i, match in enumerate(splits):
        canto_name = match.group(1)
        body_start = match.end()
        body_end = splits[i + 1].start() if i + 1 < len(splits) else len(poem)
        canto_text = poem[body_start:body_end]

        # Trim the per-canto FOOTNOTES: section (scholarly apparatus, not verse).
        fn_cut = canto_text.find("FOOTNOTES:")
        if fn_cut != -1:
            canto_text = canto_text[:fn_cut]

        clean_lines = []
        for line in canto_text.splitlines():
            stripped = line.strip()
            if re.match(r"^\[\d+\]", stripped) or stripped.startswith("[Illustration"):
                continue
            clean_lines.append(stripped)

        canto_text = " ".join(clean_lines)
        canto_text = re.sub(r"\[\d+\]", "", canto_text)
        canto_text = re.sub(r"\s{2,}\d+\s{2,}", " ", canto_text)
        canto_text = normalize(canto_text)

        location = f"Canto {canto_name}"
        chunks.extend(make_chunks(canto_text, "Inferno", location))

    print(f"Dante (Inferno):              {len(chunks)} chunks")
    return chunks


# ---------------------------------------------------------------------------
# Augustine — Confessions (unchanged, local HTML)
# ---------------------------------------------------------------------------

def load_augustine():
    html = (WORKS_DIR / "AustinesConfessions.html").read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()

    chunks = []
    for h2 in soup.find_all("h2"):
        book_text = h2.get_text(strip=True)
        if not re.match(r"BOOK\s+[IVXLC]+", book_text, re.IGNORECASE):
            continue
        book_label = book_text.title()

        paragraphs = []
        sibling = h2.find_next_sibling()
        while sibling and sibling.name != "h2":
            if sibling.name == "p":
                text = sibling.get_text(separator=" ", strip=True)
                if text:
                    paragraphs.append(text)
            sibling = sibling.find_next_sibling()

        body = normalize(" ".join(paragraphs))
        chunks.extend(make_chunks(body, "Confessions", book_label))

    print(f"Augustine (Confessions):      {len(chunks)} chunks")
    return chunks


# ---------------------------------------------------------------------------
# Austen — Pride and Prejudice
# ---------------------------------------------------------------------------

ROMAN_RE = r"[IVXLCDM]+"

def load_austen():
    raw = (WORKS_DIR / "PrideAndPrejudice.txt").read_text(encoding="utf-8")
    body = strip_gutenberg(raw)

    # Strip all [Illustration: ...] blocks (single-line and multi-line).
    # This also removes the "Chapter I.]" marker embedded inside an illustration.
    body = re.sub(r"\[Illustration[^\]]*\]", "", body, flags=re.DOTALL)

    # Skip preface / list-of-illustrations / dedication. The novel proper opens
    # with Austen's famous first line.
    opener = body.find("It is a truth universally acknowledged")
    if opener == -1:
        raise RuntimeError("Could not locate Pride and Prejudice opening line")
    body = body[opener:]

    # Split on "CHAPTER <roman>." markers (we already ate Chapter I above).
    splits = list(re.finditer(rf"^CHAPTER\s+({ROMAN_RE})\.?\s*$", body, re.MULTILINE))

    chunks = []
    # Chapter I content: from start of body to first CHAPTER match (or end).
    if splits:
        ch1_body = body[: splits[0].start()]
        chunks.extend(make_chunks(normalize(ch1_body), "Pride and Prejudice", "Chapter 1"))
    else:
        chunks.extend(make_chunks(normalize(body), "Pride and Prejudice", "Chapter 1"))

    for i, m in enumerate(splits):
        roman = m.group(1)
        num = roman_to_int(roman)
        body_start = m.end()
        body_end = splits[i + 1].start() if i + 1 < len(splits) else len(body)
        chapter_text = normalize(body[body_start:body_end])
        chunks.extend(make_chunks(chapter_text, "Pride and Prejudice", f"Chapter {num}"))

    print(f"Austen (Pride and Prejudice): {len(chunks)} chunks")
    return chunks


def roman_to_int(s: str) -> int:
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total, prev = 0, 0
    for ch in reversed(s.upper()):
        v = vals.get(ch, 0)
        total += -v if v < prev else v
        prev = max(prev, v)
    return total


# ---------------------------------------------------------------------------
# Shakespeare — King Lear (modernized, extracted from PG 100)
# ---------------------------------------------------------------------------

def load_king_lear():
    raw = (WORKS_DIR / "KingLear.txt").read_text(encoding="utf-8")

    # Drop the table of contents and Dramatis Personae preamble.
    # The actual play begins after "Dramatis Personae" block, at "ACT I".
    m = re.search(r"^ACT\s+I\b", raw, re.MULTILINE)
    if m:
        # Skip the ACT I table-of-contents entry and find the SECOND occurrence,
        # which is the real act opener (preceded by "Dramatis Personae").
        play_start = re.search(r"Dramatis Person\w+", raw)
        if play_start:
            raw = raw[play_start.end():]
        m = re.search(r"^ACT\s+I\b", raw, re.MULTILINE)
        if m:
            raw = raw[m.start():]

    # Strip stage directions: [_..._] blocks (can span lines).
    raw = re.sub(r"\[_[^\]]*_\]", "", raw, flags=re.DOTALL)

    # Split on ACT markers.
    act_splits = list(re.finditer(rf"^ACT\s+({ROMAN_RE})\b.*$", raw, re.MULTILINE))

    chunks = []
    for i, am in enumerate(act_splits):
        act_roman = am.group(1)
        act_num = roman_to_int(act_roman)
        act_body_start = am.end()
        act_body_end = act_splits[i + 1].start() if i + 1 < len(act_splits) else len(raw)
        act_body = raw[act_body_start:act_body_end]

        # Split act by Scene. Body uses "SCENE I." (all caps); match case-insensitively
        # to be safe.
        scene_splits = list(re.finditer(
            rf"^SCENE\s+({ROMAN_RE})\b.*$", act_body, re.MULTILINE | re.IGNORECASE
        ))
        if not scene_splits:
            text = normalize(act_body)
            chunks.extend(make_chunks(text, "King Lear", f"Act {act_num}"))
            continue

        for j, sm in enumerate(scene_splits):
            scene_roman = sm.group(1)
            scene_num = roman_to_int(scene_roman)
            s_start = sm.end()
            s_end = scene_splits[j + 1].start() if j + 1 < len(scene_splits) else len(act_body)
            scene_text = normalize(act_body[s_start:s_end])
            loc = f"Act {act_num}, Scene {scene_num}"
            chunks.extend(make_chunks(scene_text, "King Lear", loc))

    print(f"Shakespeare (King Lear):      {len(chunks)} chunks")
    return chunks


# ---------------------------------------------------------------------------
# Tolstoy — Anna Karenina (Garnett translation)
# ---------------------------------------------------------------------------

PART_WORDS = ["ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT"]

def load_anna_karenina():
    raw = (WORKS_DIR / "AnnaKarenina.txt").read_text(encoding="utf-8")
    body = strip_gutenberg(raw)

    # Find part headings.
    part_pattern = re.compile(
        rf"^PART\s+({'|'.join(PART_WORDS)})\s*$", re.MULTILINE
    )
    part_splits = list(part_pattern.finditer(body))
    if not part_splits:
        raise RuntimeError("Could not find PART headings in Anna Karenina")

    chunks = []
    for i, pm in enumerate(part_splits):
        part_word = pm.group(1)
        part_num = PART_WORDS.index(part_word) + 1
        p_start = pm.end()
        p_end = part_splits[i + 1].start() if i + 1 < len(part_splits) else len(body)
        part_body = body[p_start:p_end]

        chap_splits = list(re.finditer(
            r"^Chapter\s+(\d+)\s*$", part_body, re.MULTILINE
        ))
        if not chap_splits:
            text = normalize(part_body)
            chunks.extend(make_chunks(text, "Anna Karenina", f"Part {part_num}"))
            continue

        for j, cm in enumerate(chap_splits):
            chap_num = int(cm.group(1))
            c_start = cm.end()
            c_end = chap_splits[j + 1].start() if j + 1 < len(chap_splits) else len(part_body)
            chapter_text = normalize(part_body[c_start:c_end])
            loc = f"Part {part_num}, Chapter {chap_num}"
            chunks.extend(make_chunks(chapter_text, "Anna Karenina", loc))

    print(f"Tolstoy (Anna Karenina):      {len(chunks)} chunks")
    return chunks


# ---------------------------------------------------------------------------
# Montaigne — Essays (Cotton/Hazlitt, PG 3600). Selected essays only.
# ---------------------------------------------------------------------------

# Map from the heading as it appears in PG 3600 (uppercase) to the display
# location label used in the UI. Order here is the reading order.
MONTAIGNE_ESSAYS = [
    ("THE AUTHOR TO THE READER",       "Epistle to the Reader"),
    ("OF IDLENESS",                    "Of Idleness"),
    ("OF THE FORCE OF IMAGINATION",    "Of the Power of the Imagination"),
    ("OF DEMOCRITUS AND HERACLITUS",   "Of Democritus and Heraclitus"),
    ("OF REPENTANCE",                  "Of Repentance"),
    ("OF CANNIBALS",                   "Of Cannibals"),
    ("OF COACHES",                     "Of Coaches"),
    ("OF EXPERIENCE",                  "Of Experience"),
]

# Lines that terminate an essay body: next chapter/book heading, or the
# signature block after the Epistle.
MONTAIGNE_STOP = re.compile(r"^(CHAPTER\s|BOOK\s+THE\s|From Montaigne,)")


def load_montaigne():
    raw = (WORKS_DIR / "MontaigneEssays.txt").read_text(encoding="utf-8")
    raw = strip_gutenberg(raw)
    lines = raw.splitlines()

    # Index every line that is exactly one of our target headings (allow
    # trailing editorial brackets like "--[Omitted by Cotton.]").
    wanted = {title: location for title, location in MONTAIGNE_ESSAYS}
    heading_idx: dict[str, int] = {}
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Drop trailing "--[...]" annotations and any trailing period for matching.
        head = re.sub(r"\s*--\[.*?\]\s*$", "", stripped).rstrip(".")
        if head in wanted and head not in heading_idx:
            heading_idx[head] = i

    missing = [t for t, _ in MONTAIGNE_ESSAYS if t not in heading_idx]
    if missing:
        raise RuntimeError(f"Montaigne: could not locate headings: {missing}")

    chunks = []
    for title, location in MONTAIGNE_ESSAYS:
        start = heading_idx[title] + 1  # skip the heading line itself
        end = len(lines)
        for j in range(start, len(lines)):
            if MONTAIGNE_STOP.match(lines[j].strip()):
                end = j
                break
        body = "\n".join(lines[start:end])

        # Drop indented scholarly bracket blocks like "     [See Bonnefon, ...]"
        # which are editorial apparatus, not Montaigne.
        body = re.sub(r"(?ms)^\s{4,}\[.*?\]\s*$", "", body)
        body = normalize(body)
        chunks.extend(make_chunks(body, "Montaigne Essays", location))

    print(f"Montaigne (Essays):           {len(chunks)} chunks")
    return chunks


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    all_chunks = []
    all_chunks.extend(load_dante())
    all_chunks.extend(load_augustine())
    all_chunks.extend(load_austen())
    all_chunks.extend(load_king_lear())
    all_chunks.extend(load_anna_karenina())
    all_chunks.extend(load_montaigne())

    print(f"\nTotal chunks: {len(all_chunks)}")

    print("\nLoading embedding model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    texts = [c["text"] for c in all_chunks]
    print("Computing embeddings...")
    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        convert_to_numpy=True,
        batch_size=64,
    )

    OUT_CHUNKS.write_text(json.dumps(all_chunks, indent=2, ensure_ascii=False))
    np.save(OUT_EMBEDDINGS, embeddings)

    print(f"\nSaved {len(all_chunks)} chunks -> {OUT_CHUNKS}")
    print(f"Saved embeddings shape {embeddings.shape} -> {OUT_EMBEDDINGS}")


if __name__ == "__main__":
    main()
