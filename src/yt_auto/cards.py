"""Friendly, colourful, animated pop-up cards: big (animated) emoji pictures, few words.

Each card renders to a PNG sequence (RGBA, 30 fps) that duo.composite() overlays on the gameplay.
Pictures: Google Noto emoji (Apache-2.0), animated WebP when available, else static PNG.
"""

import math
import urllib.request
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageSequence
from pygments import lex
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.token import Comment, Keyword, Name, Number, String, Token

# bright, friendly palette
WHITE = (255, 255, 255)
INK = (31, 41, 55)
SOFT = (107, 114, 128)
COLORS = [(255, 107, 107), (77, 150, 255), (107, 203, 119), (255, 184, 0), (155, 93, 229), (0, 187, 212)]
TINTS = [tuple(int(c + (255 - c) * 0.82) for c in col) for col in COLORS]

W = 980
FPS = 30
ROOT = Path(__file__).resolve().parents[2]
FONT_DIR = Path("/home/aaab/.local/share/fonts/Inter")
MONO = "/usr/share/fonts/cascadia-mono-nf-fonts/CascadiaMonoNF-SemiBold.otf"

POPUP_GUIDE = """Popup cards are PICTURES first, words last. Every "emoji" must be ONE real emoji character.
Labels <= 3 words. Pick the type that best shows the idea:
- title:  {"type":"title","emoji":"⏰","text":"Why does my chip reboot?"}         (<= 6 words)
- picture:{"type":"picture","emoji":"🐕","label":"Watchdog timer"}                  one big idea
- flow:   {"type":"flow","steps":[{"emoji":"🔘","label":"Button"},{"emoji":"⚡","label":"Interrupt"},{"emoji":"🧠","label":"CPU"}]}  2-4 steps, animated
- versus: {"type":"versus","left":{"emoji":"🐢","label":"Polling"},"right":{"emoji":"⚡","label":"Interrupts"}}
- stack:  {"type":"stack","label":"Stack","items":[{"emoji":"📦","label":"main()"},{"emoji":"📦","label":"read()"}]}  2-4 items drop in, bottom first
- count:  {"type":"count","emoji":"⏱️","value":1000,"label":"times per second"}   number counts up
- code:   {"type":"code","language":"c","code":"while (1) {\\n  kick_dog();\\n}"}   <= 5 short lines, typed out live
"""


# ----------------------------------------------------------------------------- helpers
@lru_cache(maxsize=64)
def font(weight: str, px: int):
    return ImageFont.truetype(str(FONT_DIR / f"Inter-{weight}.ttf"), px)


def ease_out_back(x):
    x = min(max(x, 0.0), 1.0)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def _cp(emoji: str) -> str:
    return "_".join(f"{ord(ch):x}" for ch in emoji if ord(ch) not in (0xFE0F,))


@lru_cache(maxsize=64)
def emoji_frames(emoji: str) -> tuple:
    """Returns (frames, frame_duration_s). Animated Noto emoji when the animation never 'vanishes',
    else the static picture."""
    cache = ROOT / "assets" / "emoji"
    cache.mkdir(parents=True, exist_ok=True)
    cp = _cp(emoji.strip())

    def get(ext):
        p = cache / f"{cp}.{ext}"
        if not p.exists():
            try:
                with urllib.request.urlopen(f"https://fonts.gstatic.com/s/e/notoemoji/latest/{cp}/512.{ext}",
                                            timeout=20) as r:
                    p.write_bytes(r.read())
            except Exception:
                return None
        return Image.open(p)

    anim = get("webp")
    if anim is not None and getattr(anim, "n_frames", 1) > 1:
        frames, durs = [], []
        for f in ImageSequence.Iterator(anim):
            frames.append(f.convert("RGBA").resize((256, 256), Image.LANCZOS))
            durs.append(f.info.get("duration", 40) / 1000)
        cover = [fr.getchannel("A").point(lambda v: 255 if v > 40 else 0).histogram()[255] for fr in frames]
        if min(cover) >= 0.6 * max(cover):
            step = max(1, len(frames) // 48)
            return tuple(frames[::step]), sum(durs) / len(durs) * step
    static = get("png")
    if static is not None:
        return (static.convert("RGBA"),), 1.0
    img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))   # fallback: coloured circle with "?"
    d = ImageDraw.Draw(img)
    d.ellipse([16, 16, 496, 496], fill=COLORS[1])
    d.text((256, 256), "?", font=font("Black", 300), fill=WHITE, anchor="mm")
    return (img,), 1.0


def paste_emoji(card, emoji, cx, cy, size, t, scale=1.0, rot=0.0):
    frames, fd = emoji_frames(emoji)
    fr = frames[int(t / fd) % len(frames)]
    s = max(1, int(size * scale))
    im = fr.resize((s, s), Image.LANCZOS)
    if rot:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    card.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


def text_c(d, xy, text, px, fill=INK, weight="ExtraBold", max_w=None):
    f = font(weight, px)
    while max_w and d.textlength(text, font=f) > max_w and px > 26:
        px -= 3
        f = font(weight, px)
    d.text(xy, text, font=f, fill=fill, anchor="mm")


def pill(d, cx, cy, text, color, px=44):
    f = font("ExtraBold", px)
    w = d.textlength(text, font=f) + 56
    d.rounded_rectangle([cx - w / 2, cy - px * 0.85, cx + w / 2, cy + px * 0.85], int(px * 0.85), fill=color)
    d.text((cx, cy), text, font=f, fill=WHITE, anchor="mm")


def card_base(h, accent):
    img = Image.new("RGBA", (W, h + 14), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([8, 14, W - 1, h + 13], 56, fill=(0, 0, 0, 70))          # soft shadow
    d.rounded_rectangle([0, 0, W - 9, h - 1], 56, fill=WHITE, outline=accent, width=10)
    return img, ImageDraw.Draw(img)


def arrow(d, a, b, color, width=12):
    d.line([a, b], fill=color, width=width)
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    L = 30
    p1 = (b[0] - L * math.cos(ang - 0.55), b[1] - L * math.sin(ang - 0.55))
    p2 = (b[0] - L * math.cos(ang + 0.55), b[1] - L * math.sin(ang + 0.55))
    d.polygon([b, p1, p2], fill=color)


# ----------------------------------------------------------------------------- card types
def c_title(v, t, dur, i):
    acc = COLORS[i % len(COLORS)]
    img, d = card_base(560, acc)
    s = ease_out_back(t / 0.45)
    paste_emoji(img, v.get("emoji", "❓"), W / 2, 220, 300, t, s, rot=6 * math.sin(t * 4))
    text_c(d, (W / 2 - 4, 470), v.get("text", ""), 64, INK, max_w=W - 90)
    return img


def c_picture(v, t, dur, i):
    acc = COLORS[i % len(COLORS)]
    img, d = card_base(600, acc)
    d.ellipse([W / 2 - 230, 60, W / 2 + 230, 520], fill=TINTS[i % len(TINTS)])
    s = ease_out_back(t / 0.45) * (1 + 0.04 * math.sin(t * 5))
    paste_emoji(img, v.get("emoji", "💡"), W / 2, 270, 340, t, s)
    if t > 0.25:
        pill(d, W / 2 - 4, 530, v.get("label", ""), acc, 50)
    return img


def c_flow(v, t, dur, i):
    steps = v.get("steps", [])[:4] or [{"emoji": "❓", "label": ""}]
    n = len(steps)
    img, d = card_base(520, COLORS[(i + 1) % len(COLORS)])
    xs = [W * (k + 0.5) / n for k in range(n)]
    size = 230 if n <= 3 else 180
    each = min(0.6, 0.55 * dur / n)
    for k, st in enumerate(steps):
        tk = t - k * each
        if tk <= 0:
            continue
        col = COLORS[(i + k) % len(COLORS)]
        if k:
            prog = ease_out(tk / 0.3)
            a, b = (xs[k - 1] + size * 0.55, 220), (xs[k] - size * 0.55, 220)
            arrow(d, a, (a[0] + (b[0] - a[0]) * prog, 220), (209, 213, 219))
        d.ellipse([xs[k] - size * 0.62, 220 - size * 0.62, xs[k] + size * 0.62, 220 + size * 0.62],
                  fill=TINTS[(i + k) % len(TINTS)])
        paste_emoji(img, st.get("emoji", "❓"), xs[k], 220, size, t, ease_out_back(tk / 0.4))
        text_c(d, (xs[k], 420), st.get("label", ""), 46 if n <= 3 else 38, col, max_w=W / n - 20)
    # travelling dot once all steps are in: shows "data moving"
    t_all = n * each
    if t > t_all and n > 1:
        ph = ((t - t_all) / 1.4) % 1
        x = xs[0] + (xs[-1] - xs[0]) * ph
        d.ellipse([x - 20, 200, x + 20, 240], fill=COLORS[3], outline=WHITE, width=5)
    return img


def c_versus(v, t, dur, i):
    img, d = card_base(560, COLORS[(i + 2) % len(COLORS)])
    sides = [v.get("left", {}), v.get("right", {})]
    for k, side in enumerate(sides):
        tk = t - k * 0.5
        if tk <= 0:
            continue
        cx = W * (0.25 + 0.5 * k)
        col = COLORS[(i + k * 3) % len(COLORS)]
        d.rounded_rectangle([cx - 210, 50, cx + 210, 500], 44, fill=TINTS[(i + k * 3) % len(TINTS)])
        paste_emoji(img, side.get("emoji", "❓"), cx, 230, 250, t, ease_out_back(tk / 0.4))
        text_c(d, (cx, 430), side.get("label", ""), 50, col, max_w=390)
    if t > 0.9:
        r = 62 * (1 + 0.08 * math.sin(t * 8))
        d.ellipse([W / 2 - r, 275 - r, W / 2 + r, 275 + r], fill=INK)
        text_c(d, (W / 2, 275), "VS", 50, WHITE, "Black")
    return img


def c_stack(v, t, dur, i):
    items = v.get("items", [])[:4]
    n = max(len(items), 1)
    bh, gap = 110, 16
    h = 140 + n * (bh + gap) + 40
    img, d = card_base(h, COLORS[(i + 4) % len(COLORS)])
    text_c(d, (W / 2, 70), v.get("label", ""), 56, INK, max_w=W - 80)
    floor = h - 40
    each = min(0.55, 0.6 * dur / n)
    for k, it in enumerate(items):  # k=0 is the bottom
        tk = t - k * each
        if tk <= 0:
            continue
        target = floor - (k + 1) * (bh + gap) + gap
        y = 120 + (target - 120) * ease_out_back(tk / 0.45) if tk < 0.45 else target
        col = COLORS[(i + k) % len(COLORS)]
        d.rounded_rectangle([170, y, W - 179, y + bh], 30, fill=col)
        paste_emoji(img, it.get("emoji", "📦"), 250, y + bh / 2, 86, t)
        text_c(d, (W / 2 + 40, y + bh / 2), it.get("label", ""), 50, WHITE, max_w=W - 480)
    return img


def c_count(v, t, dur, i):
    acc = COLORS[(i + 3) % len(COLORS)]
    img, d = card_base(560, acc)
    paste_emoji(img, v.get("emoji", "🔢"), W / 2, 150, 200, t, ease_out_back(t / 0.4))
    try:
        target = float(str(v.get("value", 0)).replace(",", ""))
    except ValueError:
        target = 0
    val = target * ease_out(t / max(1.2, dur * 0.5))
    s = f"{val:,.0f}" if target >= 10 or target == int(target) else f"{val:.1f}"
    text_c(d, (W / 2, 350), s, 140, acc, "Black", max_w=W - 80)
    text_c(d, (W / 2, 470), v.get("label", ""), 48, INK, max_w=W - 80)
    return img


CODE_COLORS = [(Comment, (156, 163, 175)), (Keyword, (219, 39, 119)), (String, (22, 163, 74)),
               (Number, (124, 58, 237)), (Name.Function, (37, 99, 235)), (Name.Builtin, (8, 145, 178)),
               (Keyword.Type, (8, 145, 178)), (Token, INK)]


def c_code(v, t, dur, i):
    lines = v.get("code", "").expandtabs(4).rstrip("\n").split("\n")[:6]
    f = ImageFont.truetype(MONO, 46)
    lh = 64
    h = 130 + len(lines) * lh + 40
    img, d = card_base(h, COLORS[(i + 1) % len(COLORS)])
    d.rounded_rectangle([24, 22, W - 33, 100], 30, fill=(243, 244, 246))
    for j, col in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([60 + j * 46 - 14, 61 - 14, 60 + j * 46 + 14, 61 + 14], fill=col)
    d.text((W - 70, 61), v.get("language", "c"), font=font("Bold", 32), fill=SOFT, anchor="rm")
    total = sum(len(l) + 1 for l in lines)
    shown = int(total * ease_out(t / max(0.8, dur * 0.55)))  # typewriter
    try:
        lexer = get_lexer_by_name(v.get("language", "c"))
    except Exception:
        lexer = TextLexer()
    x0, y = 60, 140
    x, k = x0, 0
    for ttype, val in lex("\n".join(lines) + "\n", lexer):
        color = next(c for tt, c in CODE_COLORS if ttype in tt)
        for ch in val:
            if k >= shown:
                break
            if ch == "\n":
                x, y = x0, y + lh
            else:
                d.text((x, y), ch, font=f, fill=color)
                x += d.textlength(ch, font=f)
            k += 1
    if int(t * 2.5) % 2 == 0:  # blinking cursor
        d.rectangle([x + 2, y + 4, x + 24, y + 54], fill=COLORS[1])
    return img


RENDER = {"title": c_title, "picture": c_picture, "flow": c_flow, "versus": c_versus,
          "stack": c_stack, "count": c_count, "code": c_code}


def render_card(v: dict, dur: float, outdir: Path, idx: int) -> Path:
    """Writes outdir/%04d.png for the card's whole on-screen time; returns the printf pattern."""
    outdir.mkdir(parents=True, exist_ok=True)
    fn = RENDER.get(v.get("type"), c_picture)
    n = max(1, int(dur * FPS))
    for k in range(n):
        t = k / FPS
        img = fn(v, t, dur, idx)
        # whole-card pop-in
        s = ease_out_back(t / 0.28) if t < 0.28 else 1.0
        if abs(s - 1) > 1e-3:
            s = min(s, 1.0)  # overshoot handled by the content's own bounce
            canvas = Image.new("RGBA", img.size, (0, 0, 0, 0))
            sm = img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.BILINEAR)
            canvas.alpha_composite(sm, ((img.width - sm.width) // 2, (img.height - sm.height) // 2))
            img = canvas
        img.save(outdir / f"{k:04d}.png", compress_level=1)
    return outdir / "%04d.png"
