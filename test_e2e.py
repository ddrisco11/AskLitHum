"""
test_e2e.py — Single-question end-to-end test, memory-friendly.

Runs ONE question through app.ask() with all Granite stages enabled.
Writes progress + the full response JSON to disk and exits.
"""
import json
import sys
import time
import traceback
from pathlib import Path

LOG = Path(__file__).parent / "test_e2e.log"


def log(msg: str) -> None:
    stamp = time.strftime("%H:%M:%S")
    line = f"[{stamp}] {msg}\n"
    with LOG.open("a") as f:
        f.write(line)
    sys.stdout.write(line)
    sys.stdout.flush()


def main() -> int:
    if LOG.exists():
        LOG.unlink()

    log("importing app")
    t0 = time.time()
    import app
    log(f"app imported in {time.time()-t0:.1f}s")

    log("warming Granite backend (loads 6GB base model)")
    t0 = time.time()
    import granite_adapters
    _ = granite_adapters.rewrite_query("warmup")
    log(f"Granite warm in {time.time()-t0:.1f}s")

    # Single thematic question — no concurrency, no loop.
    question = "How should I judge a person I don't yet understand?"

    log(f"=== Q: {question}")
    t0 = time.time()
    try:
        client = app.app.test_client()
        r = client.post("/ask", json={"question": question})
        dt = time.time() - t0
        log(f"[status {r.status_code}] in {dt:.1f}s")
        data = r.get_json()
        if r.status_code != 200 or "error" in data:
            log(f"error: {data}")
            return 1

        out = Path(__file__).parent / "test_e2e_q1.json"
        out.write_text(json.dumps(data, indent=2))
        log(f"response -> {out.name}")

        log(f"responder: {data['responder']['name']} ({data['responder']['work']})")
        log(f"themes: {data.get('themes')}")
        log(f"pipeline: {data.get('pipeline')}")
        log(f"citations: {len(data.get('citations', []))}")
        log(f"evidence: {len(data.get('evidence', []))} cards")
        answer = data.get("answer", "")
        log(f"answer preview: {answer[:200].replace(chr(10), ' ')}...")
    except Exception:
        log(f"EXC: {traceback.format_exc()}")
        return 1

    log("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
