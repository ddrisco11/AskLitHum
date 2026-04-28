from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

W, H = 1280, 640
OUT = Path("Visuals/social_preview.png")

BG = (13, 17, 23)          # GitHub dark
FG = (230, 237, 243)       # primary text
MUTED = (139, 148, 158)    # secondary text
ACCENT = (88, 166, 255)    # GitHub link blue

def font(size, weight="regular"):
    paths = {
        "bold": [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        ],
        "regular": [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
        ],
        "mono": [
            "/System/Library/Fonts/Menlo.ttc",
            "/System/Library/Fonts/Monaco.ttf",
        ],
    }
    idx = 1 if weight == "bold" else 0
    for p in paths[weight]:
        try:
            return ImageFont.truetype(p, size, index=idx if p.endswith(".ttc") else 0)
        except Exception:
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()

img = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(img)

PAD = 80

# Owner pill (top)
owner = "ddrisco11 / AskLitHum"
draw.text((PAD, PAD), owner, font=font(28, "mono"), fill=MUTED)

# Title
title = "Ask Lit Hum"
draw.text((PAD, PAD + 70), title, font=font(112, "bold"), fill=FG)

# Description (wrapped manually, two lines max)
desc_l1 = "A retrieval-augmented literary conversation system for"
desc_l2 = "Columbia's Literature Humanities core curriculum."
draw.text((PAD, PAD + 230), desc_l1, font=font(34, "regular"), fill=MUTED)
draw.text((PAD, PAD + 278), desc_l2, font=font(34, "regular"), fill=MUTED)

# Divider
draw.line((PAD, H - 170, W - PAD, H - 170), fill=(48, 54, 61), width=2)

# Stack labels (bottom row)
items = ["Python", "MiniLM + Mistral", "IBM Granite"]
y = H - 130
x = PAD
sep = "  ·  "
for i, it in enumerate(items):
    draw.text((x, y), it, font=font(26, "regular"), fill=FG)
    x += int(draw.textlength(it, font=font(26, "regular")))
    if i < len(items) - 1:
        draw.text((x, y), sep, font=font(26, "regular"), fill=MUTED)
        x += int(draw.textlength(sep, font=font(26, "regular")))

# URL bottom-right
url = "github.com/ddrisco11/AskLitHum"
url_f = font(24, "mono")
tw = draw.textlength(url, font=url_f)
draw.text((W - PAD - tw, y + 4), url, font=url_f, fill=ACCENT)

OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT, "PNG", optimize=True)
print(f"wrote {OUT} ({OUT.stat().st_size} bytes) {img.size}")
