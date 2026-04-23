"""
simulate.py — Retrieval-routing study for Ask Lit Hum.

Goal: understand, at scale, which speaker the pipeline tends to hand a question
to *before* generation. We only exercise the retrieval + dominant-source
routing stages; no Mistral calls.

Flow per query:
    query
      -> MiniLM encode
      -> cosine-sim over chunks.json / embeddings.npy
      -> top-RETRIEVE_N pool, keep top-TOP_K
      -> dominant source among top-K becomes the speaker

Query generation uses google/flan-t5-base (250M params) with few-shot seed
prompts per category. Each prompt gives the model three gold examples in the
target register, then asks for one new question. Temperature sampling with
repetition penalty keeps outputs diverse; we dedupe and resample until we have
QUERIES_PER_CATEGORY unique queries per category.
"""
from __future__ import annotations

import collections
import json
import random
import re
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from transformers import AutoTokenizer, T5ForConditionalGeneration

BASE = Path(__file__).parent
CHUNKS_PATH = BASE / "chunks.json"
EMBEDDINGS_PATH = BASE / "embeddings.npy"
OUT_JSON = BASE / "simulation_results.json"

RETRIEVE_N = 6
TOP_K = 3
QUERIES_PER_CATEGORY = 50
SEED = 17
GEN_MODEL_ID = "google/flan-t5-base"

# Source-key -> display figure (must match SOURCE_META in app.py).
FIGURE = {
    "Inferno": "Dante",
    "Confessions": "Augustine",
    "Pride and Prejudice": "Elizabeth Bennet",
    "King Lear": "King Lear",
    "Anna Karenina": "Anna Karenina",
    "Montaigne Essays": "Montaigne",
}

# Each category carries ~12 gold-standard example questions. We draw 3 at
# random per generation as few-shot anchors, which gives flan-t5-base enough
# form + topic signal to produce coherent literary questions.
CATEGORY_EXAMPLES: dict[str, list[str]] = {
    "Human condition & identity": [
        "What does it mean to truly know oneself?",
        "How does suffering shape the person we become?",
        "Is the self something we discover or something we invent?",
        "How does memory hold a life together?",
        "What is lost when a person grows old?",
        "Can a person change their fundamental nature?",
        "How do we live with the gap between who we seem to be and who we are?",
        "What does it mean to live an authentic life?",
        "How does solitude reveal the self?",
        "Is vanity an inescapable part of being human?",
        "What makes a human life feel whole?",
        "How does the body shape the mind?",
    ],
    "Social & cultural structures": [
        "How does class determine the course of a life?",
        "What does marriage reveal about a society?",
        "How does a community treat those who do not belong?",
        "What role do manners play in hiding true feeling?",
        "How do inherited customs constrain individual choice?",
        "What does wealth buy that it cannot buy?",
        "How are women expected to behave in polite society?",
        "What happens when public reputation collides with private truth?",
        "How does a society judge an unfaithful wife?",
        "What makes a social ritual meaningful or hollow?",
        "How is power passed down within a family?",
        "What does hospitality demand of a host?",
    ],
    "Existential / philosophical": [
        "Does life have meaning without God?",
        "What do we owe the dead?",
        "Is free will an illusion?",
        "How should we live knowing we will die?",
        "Can we know anything for certain?",
        "Is truth discovered or constructed?",
        "What is the shape of time within a single life?",
        "Does the soul exist apart from the body?",
        "Why is there suffering in a just universe?",
        "Can reason alone guide a good life?",
        "What is the nature of true happiness?",
        "Is the examined life truly worth more than the unexamined one?",
    ],
    "Interpersonal relationships": [
        "How does love survive disappointment?",
        "What does loyalty demand when a friend is wrong?",
        "How do parents wound the children they love?",
        "What makes a betrayal possible to forgive?",
        "How do first impressions mislead us about others?",
        "Can jealousy ever be a sign of love?",
        "What holds a marriage together when passion fades?",
        "How does pride keep people apart?",
        "Is true friendship possible between unequals?",
        "How do we recognize the person we should love?",
        "What does it mean to really listen to another person?",
        "How do small misunderstandings grow into lasting estrangements?",
    ],
    "Conflict & struggle": [
        "What is worth fighting for?",
        "How does a person endure exile?",
        "What is the cost of choosing duty over desire?",
        "How does a ruler's pride destroy what he rules?",
        "What does it take to resist temptation?",
        "How do families tear themselves apart?",
        "When does obedience to authority become wrong?",
        "What is the right response to injustice?",
        "How does war reshape the men who fight it?",
        "How do we fight a battle we know we will lose?",
        "What does it mean to struggle with oneself?",
        "How is a rebellion justified?",
    ],
    "Moral / ethical questions": [
        "What makes an act truly virtuous?",
        "How heavy is the weight of a guilty conscience?",
        "Can a sinner be genuinely reformed?",
        "When, if ever, is revenge justified?",
        "What do we owe strangers?",
        "How do we live honestly in a world that rewards deceit?",
        "What is the difference between pride and self-respect?",
        "How should mercy temper justice?",
        "Is it worse to harm the body or the soul?",
        "When does ambition become a vice?",
        "How do small compromises lead to moral ruin?",
        "What does true repentance actually require?",
    ],
}


def build_prompt(category: str, rng: random.Random) -> str:
    exemplars = rng.sample(CATEGORY_EXAMPLES[category], 3)
    examples_block = "\n".join(f"- {e}" for e in exemplars)
    return (
        f"Write one thoughtful, reflective question on the theme of {category.lower()}. "
        f"The question should be about life itself, not about books or characters. "
        f"Write in the style of these examples:\n{examples_block}\n"
        f"Now write one new question in the same spirit. It must end with a question mark. "
        f"Do not mention books, novels, plots, authors, or characters. "
        f"Do not repeat any example. Return only the question."
    )


def clean_query(text: str) -> str:
    text = text.strip().strip('"').strip("'")
    text = re.sub(r"\s+", " ", text)
    # If model emits multiple questions, keep only the first.
    m = re.search(r"[^?]*\?", text)
    if m:
        text = m.group(0).strip()
    if not text.endswith("?"):
        text = text.rstrip(".") + "?"
    # Drop leading list markers ("- ", "1. ").
    text = re.sub(r"^[-*\d.\s]+", "", text).strip()
    # Capitalize first letter.
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    return text


CATEGORY_STOPWORDS = {
    "Human condition & identity": ["human condition", "condition & identity", "condition and identity"],
    "Social & cultural structures": ["social & cultural", "social and cultural", "social structures", "cultural structures", "social structure"],
    "Existential / philosophical": ["existential philosophy", "existential / philosophical", "existential and philosophical"],
    "Interpersonal relationships": ["interpersonal relationships", "interpersonal relationship"],
    "Conflict & struggle": ["conflict & struggle", "conflict and struggle"],
    "Moral / ethical questions": ["moral / ethical", "moral and ethical", "moral/ethical", "ethical questions"],
}


def looks_usable(q: str, examples: list[str], category: str) -> bool:
    if len(q) < 20 or len(q) > 200:
        return False
    # Reject degenerate outputs.
    if q.lower().startswith("task:") or "examples of" in q.lower():
        return False
    # Reject meta-commentary about literature itself.
    meta_terms = (
        "novel", "book", "story", "character", "plot", "author", "writer",
        "literature", "literary", "poem", "text", "the story", "the book",
        "this text", "reader", "classic",
    )
    ql = q.lower()
    if any(t in ql for t in meta_terms):
        return False
    # Require at least one verb-like token; flan-t5 sometimes emits noun lists.
    if not re.search(r"\b(is|are|was|were|do|does|did|can|could|should|would|will|has|have|had|makes|make|means|mean|shape|shapes|change|changes|become|reveal|live|love|hold|grow|carry)\b", q.lower()):
        return False
    ex_lower = {e.lower() for e in examples}
    if q.lower() in ex_lower:
        return False
    # Reject queries that just parrot the category label.
    for bad in CATEGORY_STOPWORDS.get(category, []):
        if bad in ql:
            return False
    return True


def generate_queries(tok, gen_model) -> dict[str, list[str]]:
    rng = random.Random(SEED)
    out: dict[str, list[str]] = {}
    for cat, examples in CATEGORY_EXAMPLES.items():
        bag: list[str] = []
        seen: set[str] = set()
        attempts = 0
        while len(bag) < QUERIES_PER_CATEGORY and attempts < 1000:
            attempts += 1
            prompt = build_prompt(cat, rng)
            enc = tok(prompt, return_tensors="pt", truncation=True, max_length=512)
            out_ids = gen_model.generate(
                **enc,
                do_sample=True,
                top_p=0.92,
                temperature=0.95,
                repetition_penalty=1.25,
                max_new_tokens=60,
                num_return_sequences=1,
            )
            q = clean_query(tok.decode(out_ids[0], skip_special_tokens=True))
            key = q.lower()
            if key in seen or not looks_usable(q, examples, cat):
                continue
            seen.add(key)
            bag.append(q)
        out[cat] = bag
        print(f"  {cat}: {len(bag)} queries (attempts={attempts})")
    return out


def retrieve(query, embed_model, embeddings, chunks):
    vec = embed_model.encode([query], convert_to_numpy=True)
    sims = cosine_similarity(vec, embeddings)[0]
    top_idx = np.argsort(sims)[::-1][:RETRIEVE_N]
    pool = [
        {"id": int(i), "source": chunks[int(i)]["source"], "score": float(sims[int(i)])}
        for i in top_idx
    ]
    return pool[:TOP_K]


def dominant(passages):
    c = collections.Counter(p["source"] for p in passages)
    src, n = c.most_common(1)[0]
    return src, n


def main():
    print("[sim] loading retrieval assets...")
    chunks = json.loads(CHUNKS_PATH.read_text())
    embeddings = np.load(EMBEDDINGS_PATH)
    print(f"[sim] {len(chunks)} chunks, embeddings {embeddings.shape}")

    print("[sim] loading MiniLM embedder...")
    embed_model = SentenceTransformer("all-MiniLM-L6-v2")

    print(f"[sim] loading generator: {GEN_MODEL_ID}")
    tok = AutoTokenizer.from_pretrained(GEN_MODEL_ID)
    gen_model = T5ForConditionalGeneration.from_pretrained(GEN_MODEL_ID)
    gen_model.eval()

    print("[sim] generating queries...")
    queries_by_cat = generate_queries(tok, gen_model)

    print("[sim] running retrieval for every query...")
    results = []
    for cat, queries in queries_by_cat.items():
        for q in queries:
            top = retrieve(q, embed_model, embeddings, chunks)
            src, votes = dominant(top)
            results.append({
                "category": cat,
                "query": q,
                "top_sources": [p["source"] for p in top],
                "top_scores": [round(p["score"], 4) for p in top],
                "chosen_source": src,
                "chosen_figure": FIGURE[src],
                "dominance": votes,
            })

    overall = collections.Counter(r["chosen_figure"] for r in results)
    by_cat = {c: collections.Counter() for c in CATEGORY_EXAMPLES}
    no_majority = 0
    mean_top_score = 0.0
    for r in results:
        by_cat[r["category"]][r["chosen_figure"]] += 1
        if r["dominance"] == 1:
            no_majority += 1
        mean_top_score += r["top_scores"][0]
    mean_top_score /= len(results)

    stats = {
        "total_queries": len(results),
        "per_category": {c: dict(v) for c, v in by_cat.items()},
        "overall": dict(overall),
        "no_majority_top_k": no_majority,
        "mean_top1_cosine": round(mean_top_score, 4),
    }

    out_doc = {
        "config": {
            "retrieve_n": RETRIEVE_N,
            "top_k": TOP_K,
            "queries_per_category": QUERIES_PER_CATEGORY,
            "generator": GEN_MODEL_ID,
            "embedder": "all-MiniLM-L6-v2",
            "seed": SEED,
        },
        "figures": FIGURE,
        "stats": stats,
        "results": results,
    }
    OUT_JSON.write_text(json.dumps(out_doc, indent=2, ensure_ascii=False))
    print(f"[sim] wrote {OUT_JSON}")
    print("\n=== overall speaker distribution ===")
    for fig, n in overall.most_common():
        print(f"  {fig:<20} {n:>4}  ({n/len(results):.1%})")
    print(f"\nmean top-1 cosine: {mean_top_score:.3f}")
    print(f"top-K with no majority (3 different sources): {no_majority}")


if __name__ == "__main__":
    main()
