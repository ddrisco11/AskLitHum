"""
record_demo.py — Scripted Playwright recording of the Ask Lit Hum UI.

Drives the real app (backend + frontend + Ollama) through two canonical
questions, records a 1280x800 webm, and writes timing markers to
video_raw/timing.json so the ffmpeg editor can cut/speed/caption correctly.

Prereqs (all must be live before running):
    - Ollama serving mistral:7b-instruct-q4_0  (default :11434)
    - Flask backend                             (http://127.0.0.1:5001)
    - Vite dev server                           (auto-detected 3000 or 3001)
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

import requests
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).parent
OUT = HERE / "video_raw"
OUT.mkdir(exist_ok=True)

QUESTIONS = [
    "What does it mean to live an authentic life?",
    "How does love survive disappointment?",
]

VIEWPORT = {"width": 1280, "height": 800}


def find_frontend() -> str:
    for port in (3000, 3001, 5173, 8080):
        try:
            r = requests.get(f"http://127.0.0.1:{port}", timeout=2)
            if r.status_code == 200 and "lit hum" in r.text.lower() or r.status_code == 200:
                return f"http://127.0.0.1:{port}"
        except requests.RequestException:
            continue
    raise SystemExit("No frontend found on 3000/3001/5173/8080")


def main():
    front = find_frontend()
    print(f"[rec] frontend = {front}")

    # preflight
    h = requests.get("http://127.0.0.1:5001/health", timeout=5).json()
    print(f"[rec] backend: {h['chunks']} chunks, model {h['ollama_model']}")

    timing = {"viewport": VIEWPORT, "questions": QUESTIONS, "segments": []}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport=VIEWPORT,
            record_video_dir=str(OUT),
            record_video_size=VIEWPORT,
            device_scale_factor=2,  # sharp text
        )
        page = context.new_page()

        t0 = time.time()
        def mark(key):
            timing[key] = round(time.time() - t0, 3)

        page.goto(front)
        page.wait_for_selector("input[placeholder*='weighs']", timeout=30_000)
        time.sleep(2.0)  # hero establishing shot
        mark("hero_ready")

        for i, q in enumerate(QUESTIONS):
            seg = {"index": i, "question": q}
            seg["typing_start"] = round(time.time() - t0, 3)
            inp = page.locator("input[placeholder*='weighs']")
            inp.click()
            inp.fill("")
            inp.type(q, delay=45)
            time.sleep(0.8)
            seg["submit"] = round(time.time() - t0, 3)
            page.get_by_role("button", name="Consult the Canon").click()

            # wait for the responder/answer to render
            page.wait_for_selector("text=/Responding/i", timeout=300_000)
            seg["response_received"] = round(time.time() - t0, 3)
            time.sleep(2.5)  # let motion.div animations settle

            # slow scroll to reveal answer + evidence + citations
            for _ in range(6):
                page.mouse.wheel(0, 260)
                time.sleep(0.9)
            time.sleep(1.2)
            seg["scroll_done"] = round(time.time() - t0, 3)

            # reset
            try:
                page.get_by_text("Ask another question", exact=False).click(timeout=3000)
            except Exception:
                page.goto(front)
            page.wait_for_selector("input[placeholder*='weighs']", timeout=15_000)
            time.sleep(1.0)
            seg["next_ready"] = round(time.time() - t0, 3)
            timing["segments"].append(seg)

        time.sleep(1.5)
        mark("end")

        # capture video filename before closing
        video = page.video
        context.close()
        browser.close()

        if video:
            src = pathlib.Path(video.path())
            dst = OUT / "raw.webm"
            if src.exists():
                src.replace(dst)
                print(f"[rec] saved {dst}")
                timing["video_file"] = str(dst)

    (OUT / "timing.json").write_text(json.dumps(timing, indent=2))
    print(f"[rec] wrote {OUT/'timing.json'}")
    print(json.dumps(timing, indent=2))


if __name__ == "__main__":
    sys.exit(main())
