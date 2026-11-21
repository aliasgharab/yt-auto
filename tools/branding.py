"""Kernel Kids channel branding: avatar + banner images, channel description and keywords.

  .venv/bin/python tools/branding.py            # render assets/branding/{avatar,banner}.png
  .venv/bin/python tools/branding.py --apply    # ...and set banner + description + keywords on YouTube
                                                #   (~150 quota units). The profile picture has no API:
                                                #   upload assets/branding/avatar.png in YouTube Studio ->
                                                #   Customization -> Branding.
"""
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets/branding"
FONTS = Path.home() / ".local/share/fonts/Inter"

BG, BG2 = (11, 18, 38), (20, 33, 66)          # deep navy
CYAN, AMBER, WHITE = (34, 211, 238), (251, 191, 36), (240, 246, 255)
TRACE = (40, 70, 120)

DESCRIPTION = (
    "How does a computer actually work? Kernel Kids explains one tech idea in under 30 seconds: "
    "CPUs, RAM, interrupts, watchdog timers, deadlocks, Arduino, operating systems, chips and more.\n\n"
    "Real tech terms, explained simply, for curious students (13-18) and new programmers. "
    "Hiro asks, Baymax explains.\n\n"
    "New Shorts every day."
)
KEYWORDS = ('"Kernel Kids" "how computers work" "computer science" "embedded systems" "operating systems" '
            'Arduino "tech explained" CPU microcontroller "programming for beginners" STEM "computer science for kids"')


def font(weight: str, size: int):
    return ImageFont.truetype(str(FONTS / f"Inter-{weight}.ttf"), size)


def gradient(w, h):
    im = Image.new("RGB", (w, h), BG)
    px = ImageDraw.Draw(im)
    for y in range(h):
        t = y / h
        px.line([(0, y), (w, y)], fill=tuple(int(BG[i] + (BG2[i] - BG[i]) * t) for i in range(3)))
    return im


def circuit(im, n, seed, keep_out=None, color=TRACE):
    """Random right-angle PCB traces with pads; skips a keep-out box (x0, y0, x1, y1)."""
    rnd = random.Random(seed)
    d = ImageDraw.Draw(im)
    w, h = im.size
    step = max(w, h) // 40
    for _ in range(n):
        x, y = rnd.randrange(0, w, step), rnd.randrange(0, h, step)
        pts = [(x, y)]
        for _ in range(rnd.randint(2, 4)):
            if rnd.random() < 0.5:
                x += rnd.choice([-1, 1]) * step * rnd.randint(2, 6)
            else:
                y += rnd.choice([-1, 1]) * step * rnd.randint(2, 6)
            pts.append((x, y))
        if keep_out and any(keep_out[0] < px < keep_out[2] and keep_out[1] < py < keep_out[3] for px, py in pts):
            continue
        d.line(pts, fill=color, width=max(2, step // 8), joint="curve")
        r = max(4, step // 4)
        for px, py in (pts[0], pts[-1]):
            d.ellipse([px - r, py - r, px + r, py + r], outline=color, width=max(2, step // 10))


def chip(d, cx, cy, size, label, lfont):
    """A microchip: rounded body, pins on all four sides, label in the middle."""
    s = size // 2
    pin_len, pins = size // 7, 5
    gap = size / (pins + 1)
    pw = max(4, size // 22)
    for i in range(1, pins + 1):
        o = -s + i * gap
        for (x0, y0, x1, y1) in [(cx + o - pw, cy - s - pin_len, cx + o + pw, cy - s),
                                 (cx + o - pw, cy + s, cx + o + pw, cy + s + pin_len),
                                 (cx - s - pin_len, cy + o - pw, cx - s, cy + o + pw),
                                 (cx + s, cy + o - pw, cx + s + pin_len, cy + o + pw)]:
            d.rounded_rectangle([x0, y0, x1, y1], radius=pw // 2, fill=AMBER)
    d.rounded_rectangle([cx - s, cy - s, cx + s, cy + s], radius=size // 9, fill=(16, 26, 52),
                        outline=CYAN, width=max(6, size // 40))
    d.ellipse([cx - s + size // 12, cy - s + size // 12, cx - s + size // 12 + size // 18,
               cy - s + size // 12 + size // 18], fill=CYAN)
    d.text((cx, cy + size // 40), label, font=lfont, fill=WHITE, anchor="mm")


def glow(im, box, color, radius):
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse(box, fill=color + (90,))
    im.paste(layer.filter(ImageFilter.GaussianBlur(radius)), (0, 0), layer.filter(ImageFilter.GaussianBlur(radius)))


def avatar(path):
    S = 800
    im = gradient(S, S)
    circuit(im, 40, 3, keep_out=(140, 140, 660, 660))
    glow(im, (170, 170, 630, 630), CYAN, 60)
    chip(ImageDraw.Draw(im), S // 2, S // 2, 400, "KK", font("Black", 190))
    im.save(path)


def banner(path):
    W, H = 2560, 1440
    im = gradient(W, H)
    sx0, sy0, sx1, sy1 = (W - 1546) // 2, (H - 423) // 2, (W + 1546) // 2, (H + 423) // 2   # safe area (all devices)
    circuit(im, 90, 7, keep_out=(sx0 - 40, sy0 - 40, sx1 + 40, sy1 + 40), color=(30, 52, 92))
    glow(im, (sx0 - 60, sy0 - 40, sx0 + 400, sy1 + 40), CYAN, 70)
    d = ImageDraw.Draw(im)
    chip(d, sx0 + 190, H // 2, 270, "KK", font("Black", 125))
    tx = sx0 + 400
    d.text((tx, H // 2 - 80), "Kernel Kids", font=font("Black", 150), fill=WHITE, anchor="lm")
    d.text((tx + 4, H // 2 + 45), "How computers really work, in 30 seconds", font=font("SemiBold", 56),
           fill=CYAN, anchor="lm")
    d.text((tx + 4, H // 2 + 125), "CPUs  •  RAM  •  Arduino  •  Operating systems  •  New Shorts daily",
           font=font("Medium", 38), fill=AMBER, anchor="lm")
    im.save(path)


def apply():
    sys.path.insert(0, str(ROOT / "src"))
    from googleapiclient.http import MediaFileUpload
    from yt_auto.youtube import _youtube

    yt = _youtube(manage=True)
    banner_url = yt.channelBanners().insert(
        media_body=MediaFileUpload(str(OUT / "banner.png"), mimetype="image/png")).execute()["url"]
    ch = yt.channels().list(part="brandingSettings", mine=True).execute()["items"][0]
    bs = ch.get("brandingSettings", {})
    bs.setdefault("channel", {}).update({"description": DESCRIPTION, "keywords": KEYWORDS,
                                          "defaultLanguage": "en", "country": "CA"})
    bs.setdefault("image", {})["bannerExternalUrl"] = banner_url
    yt.channels().update(part="brandingSettings", body={"id": ch["id"], "brandingSettings": bs}).execute()
    print(f"channel {ch['id']}: banner, description and keywords set")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    avatar(OUT / "avatar.png")
    banner(OUT / "banner.png")
    print(f"wrote {OUT}/avatar.png, {OUT}/banner.png")
    if "--apply" in sys.argv:
        apply()
