from PIL import Image, ImageDraw, ImageFilter, ImageFont
from pathlib import Path

W, H = 1280, 640
OUT = Path("Visuals/social_preview.png")

def font(size, bold=False):
    candidates = [
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Georgia.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()

# Vertical gradient: deep navy -> burgundy
img = Image.new("RGB", (W, H), (20, 24, 48))
px = img.load()
top = (18, 22, 46)
bot = (78, 22, 38)
for y in range(H):
    t = y / (H - 1)
    r = int(top[0] * (1 - t) + bot[0] * t)
    g = int(top[1] * (1 - t) + bot[1] * t)
    b = int(top[2] * (1 - t) + bot[2] * t)
    for x in range(W):
        px[x, y] = (r, g, b)

# Soft gold radial glow center-left
glow = Image.new("RGB", (W, H), (0, 0, 0))
gd = ImageDraw.Draw(glow)
cx, cy = 360, 320
for r in range(420, 0, -8):
    a = int(60 * (1 - r / 420))
    gd.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(a, int(a*0.85), int(a*0.45)))
glow = glow.filter(ImageFilter.GaussianBlur(40))
img = Image.blend(img, Image.eval(glow, lambda v: min(255, v)), 0.6)
# Re-apply by adding glow
base = img.convert("RGB")
img = Image.new("RGB", (W, H))
bp = base.load()
gp = glow.load()
op = img.load()
for y in range(H):
    for x in range(W):
        br, bg, bb = bp[x, y]
        gr, gg, gbl = gp[x, y]
        op[x, y] = (min(255, br + gr), min(255, bg + gg), min(255, bb + gbl))

draw = ImageDraw.Draw(img)

# Decorative side bar (gold)
draw.rectangle((60, 80, 70, H - 80), fill=(212, 175, 55))

# Eyebrow
draw.text((100, 90), "COLUMBIA  ·  LITERATURE HUMANITIES", font=font(22, bold=True), fill=(212, 175, 55))

# Title
draw.text((100, 140), "Ask Lit Hum", font=font(120, bold=True), fill=(245, 240, 225))

# Subtitle
sub = "A retrieval-augmented literary conversation system."
draw.text((100, 290), sub, font=font(34), fill=(225, 220, 205))

# Tagline lines
draw.text((100, 350), "Ask a thematic question.", font=font(28), fill=(200, 195, 180))
draw.text((100, 388), "A speaker emerges from the text — and answers in character.", font=font(28), fill=(200, 195, 180))

# Stack chips
chips = ["MiniLM", "Mistral 7B", "IBM Granite", "Ollama", "RAG"]
x = 100
y = 470
for c in chips:
    tw = draw.textlength(c, font=font(24, bold=True))
    pad = 18
    draw.rounded_rectangle((x, y, x + tw + pad * 2, y + 48), radius=24, fill=(255, 255, 255, 30), outline=(212, 175, 55), width=2)
    draw.text((x + pad, y + 8), c, font=font(24, bold=True), fill=(245, 240, 225))
    x += tw + pad * 2 + 14

# Bottom-right attribution
url = "github.com/ddrisco11/AskLitHum"
tw = draw.textlength(url, font=font(24, bold=True))
draw.text((W - tw - 70, H - 60), url, font=font(24, bold=True), fill=(212, 175, 55))

# Decorative quote mark
draw.text((W - 280, 80), "“", font=font(360, bold=True), fill=(212, 175, 55, 80))

OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT, "PNG", optimize=True)
print(f"wrote {OUT} ({OUT.stat().st_size} bytes) {img.size}")
