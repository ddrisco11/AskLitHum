"""
edit_demo.py — Programmatic edit of the Playwright-recorded demo.

Reads video_raw/raw.webm + timing.json and produces a polished MP4 at
video_output/demo.mp4:

    [title card] -> hero -> typing Q1 -> generation (sped 5.5x) ->
    answer Q1 -> typing Q2 -> generation (sped 5x) -> answer Q2 -> [end card]

Captions are overlaid via ffmpeg drawtext. Each segment is rendered to its
own intermediate mp4 and then concatenated with the concat demuxer to avoid
filter-graph complexity.
"""
from __future__ import annotations

import json
import pathlib
import shlex
import subprocess

HERE = pathlib.Path(__file__).parent
RAW = HERE / "video_raw" / "raw.webm"
TIMING = json.loads((HERE / "video_raw" / "timing.json").read_text())
TMP = HERE / "video_tmp"
OUT = HERE / "video_output"
TMP.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)

FONT_SERIF = "/System/Library/Fonts/Supplemental/Georgia.ttf"
FONT_SANS = "/System/Library/Fonts/NewYork.ttf"
W, H = 1280, 800
BG = "0xEDE8E0"   # the app's cream bg, matched
INK = "0x2E2A24"
GOLD = "0xB89860"


def run(args: list) -> None:
    args = [str(a) for a in args]
    print("$", " ".join(shlex.quote(a) for a in args))
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        print("STDERR:", r.stderr[-2000:])
        raise SystemExit(r.returncode)


def ffesc(text: str) -> str:
    # ffmpeg drawtext needs special chars escaped.
    return (text.replace("\\", "\\\\")
                .replace(":", "\\:")
                .replace("'", "’")
                .replace(",", "\\,"))


def make_card(path: pathlib.Path, dur: float, title: str, subtitle: str, footer: str = ""):
    """Render a solid-color card with centered title + subtitle + optional footer."""
    drawtext_title = (
        f"drawtext=fontfile='{FONT_SERIF}':text='{ffesc(title)}':"
        f"fontcolor={INK}:fontsize=72:x=(w-text_w)/2:y=(h/2)-110"
    )
    drawtext_sub = (
        f"drawtext=fontfile='{FONT_SERIF}':text='{ffesc(subtitle)}':"
        f"fontcolor={INK}:fontsize=28:x=(w-text_w)/2:y=(h/2)+10"
    )
    filters = [drawtext_title, drawtext_sub]
    if footer:
        filters.append(
            f"drawtext=fontfile='{FONT_SERIF}':text='{ffesc(footer)}':"
            f"fontcolor={GOLD}:fontsize=22:x=(w-text_w)/2:y=(h/2)+80"
        )
    # Add a thin gold divider
    filters.append(
        f"drawbox=x=(iw-320)/2:y=(ih/2)-40:w=320:h=1:color={GOLD}:t=fill"
    )
    vf = ",".join(filters)
    run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c={BG}:s={W}x{H}:r=30:d={dur}",
        "-vf", vf,
        "-pix_fmt", "yuv420p",
        "-c:v", "libx264", "-crf", "20", "-preset", "medium",
        "-movflags", "+faststart",
        str(path),
    ])


def cut_segment(path: pathlib.Path, start: float, end: float, speed: float,
                caption: str | None, caption_style: str = "bottom"):
    """
    Trim raw.webm [start, end], apply speed, and overlay a caption if given.
    caption_style: 'bottom' = subtle strip near bottom, 'top' = band near top.
    """
    dur = end - start
    filters = []
    if speed != 1.0:
        # setpts scales presentation timestamps; higher speed -> smaller pts.
        filters.append(f"setpts=PTS/{speed}")
    if caption:
        if caption_style == "bottom":
            box_y = H - 96
            filters.append(
                f"drawbox=x=0:y={box_y}:w=iw:h=96:color={INK}@0.82:t=fill"
            )
            filters.append(
                f"drawtext=fontfile='{FONT_SERIF}':text='{ffesc(caption)}':"
                f"fontcolor=white:fontsize=28:x=(w-text_w)/2:y={box_y+34}"
            )
        elif caption_style == "banner":
            filters.append(
                f"drawbox=x=0:y=40:w=iw:h=80:color={INK}@0.82:t=fill"
            )
            filters.append(
                f"drawtext=fontfile='{FONT_SERIF}':text='{ffesc(caption)}':"
                f"fontcolor=white:fontsize=30:x=(w-text_w)/2:y=66"
            )
    vf = ",".join(filters) if filters else "null"
    run([
        "ffmpeg", "-y",
        "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
        "-i", str(RAW),
        "-vf", vf,
        "-an", "-r", "30", "-pix_fmt", "yuv420p",
        "-c:v", "libx264", "-crf", "20", "-preset", "medium",
        "-movflags", "+faststart",
        str(path),
    ])


def concat_demux(segments: list[pathlib.Path], out: pathlib.Path):
    listfile = TMP / "concat_list.txt"
    listfile.write_text("\n".join(f"file '{s.resolve()}'" for s in segments))
    run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(listfile),
        "-c:v", "libx264", "-crf", "20", "-preset", "medium",
        "-pix_fmt", "yuv420p", "-r", "30",
        "-movflags", "+faststart",
        str(out),
    ])


def main():
    segs = TIMING["segments"]
    s0, s1, s2 = segs[0], segs[1], segs[2]
    hero_end = TIMING["hero_ready"]

    # ---- 1. title card (3s) ----
    title = TMP / "01_title.mp4"
    make_card(
        title, 3.0,
        "Ask Lit Hum",
        "A retrieval-augmented dialogue with the Columbia Lit Hum canon",
        footer="Dante · Augustine · Austen · Shakespeare · Tolstoy · Montaigne",
    )

    # ---- 2. hero establishing (0 -> typing start) ----
    hero = TMP / "02_hero.mp4"
    cut_segment(hero, 0.0, s0["typing_start"], 1.0, None)

    # ---- 3. typing Q1 ----
    type1 = TMP / "03_type1.mp4"
    cut_segment(
        type1, s0["typing_start"], s0["submit"] + 0.3, 1.0,
        'I. "Should I skip LitHum class?"',
    )

    # ---- 4. generation Q1 sped up ----
    gen1 = TMP / "04_gen1.mp4"
    cut_segment(
        gen1, s0["submit"] + 0.3, s0["response_received"] - 0.2, 6.0,
        "Retrieving · scoring · generating...", caption_style="banner",
    )

    # ---- 5. Q1 answer reveal ----
    ans1 = TMP / "05_ans1.mp4"
    cut_segment(
        ans1, s0["response_received"] - 0.2, s0["scroll_done"] + 0.5, 0.9,
        "The canon responds",
    )

    # ---- 6. typing Q2 ----
    type2 = TMP / "06_type2.mp4"
    cut_segment(
        type2, s1["typing_start"] + 0.3, s1["submit"] + 0.3, 1.0,
        'II. "How do I make the most of my time in school?"',
    )

    # ---- 7. generation Q2 sped ----
    gen2 = TMP / "07_gen2.mp4"
    cut_segment(
        gen2, s1["submit"] + 0.3, s1["response_received"] - 0.2, 10.0,
        "Retrieving · scoring · generating...", caption_style="banner",
    )

    # ---- 8. Q2 answer reveal ----
    ans2 = TMP / "08_ans2.mp4"
    cut_segment(
        ans2, s1["response_received"] - 0.2, s1["scroll_done"] + 0.5, 0.9,
        "The canon responds",
    )

    # ---- 9. typing Q3 ----
    type3 = TMP / "09_type3.mp4"
    cut_segment(
        type3, s2["typing_start"] + 0.3, s2["submit"] + 0.3, 1.0,
        'III. "I took someone’s laundry out of the dryer, will I go to hell?"',
    )

    # ---- 10. generation Q3 sped ----
    gen3 = TMP / "10_gen3.mp4"
    cut_segment(
        gen3, s2["submit"] + 0.3, s2["response_received"] - 0.2, 9.0,
        "Retrieving · scoring · generating...", caption_style="banner",
    )

    # ---- 11. Q3 answer reveal ----
    ans3 = TMP / "11_ans3.mp4"
    cut_segment(
        ans3, s2["response_received"] - 0.2, s2["scroll_done"] + 0.5, 0.9,
        "The canon responds",
    )

    # ---- 12. end card ----
    end = TMP / "12_end.mp4"
    make_card(
        end, 3.5,
        "All answers grounded in text.",
        "Citations generated by IBM Granite.",
        footer="github.com/ddrisco11/AskLitHum",
    )

    segments = [title, hero, type1, gen1, ans1, type2, gen2, ans2, type3, gen3, ans3, end]
    final = OUT / "demo.mp4"
    concat_demux(segments, final)

    # sanity: report duration and size
    dur = subprocess.check_output([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1",
        str(final),
    ], text=True).strip()
    size = final.stat().st_size / 1024 / 1024
    print(f"\n[done] {final}")
    print(f"[done] duration = {dur}s, size = {size:.2f} MB")


if __name__ == "__main__":
    main()
