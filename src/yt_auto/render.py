"""Stage 4: scene visual spec -> keyframe PNGs (one per reveal step), Ayu-dark theme."""

from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
from pygments import lex
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.token import Comment, Keyword, Name, Number, Operator, String, Token

# Ayu Dark
BG = (11, 14, 20)
PANEL = (19, 23, 33)
PANEL_EDGE = (39, 45, 56)
FG = (191, 189, 182)
HEAD = (230, 225, 207)
DIM = (98, 106, 115)
YELLOW = (230, 180, 80)
ORANGE = (255, 143, 64)
GREEN = (170, 217, 76)
BLUE = (57, 186, 230)
PURPLE = (210, 166, 255)
RED = (240, 113, 120)
ACCENTS = [YELLOW, BLUE, GREEN, PURPLE, ORANGE, RED]

CODE_COLORS = [
    (Comment, DIM), (Keyword, ORANGE), (String, GREEN), (Number, PURPLE),
    (Name.Function, (255, 180, 84)), (Name.Builtin, BLUE), (Name.Class, BLUE),
    (Keyword.Type, BLUE), (Operator, (242, 150, 102)), (Token, FG),
]


class Canvas:
    def __init__(self, size, cfg, popup=False):
        self.W, self.H = size
        self.popup = popup
        self.vertical = self.H > self.W
        self.s = min(self.W, self.H) / 1080  # scale unit
        self.font_dir = Path(cfg["render"]["font_dir"])
        self.mono = cfg["render"]["mono_font"]
        # content box: shorts leave the lower third for captions
        m = int(70 * self.s)
        self.box = (m, int(260 * self.s) if self.vertical else int(120 * self.s), self.W - m,
                    int(self.H * 0.70) if self.vertical else self.H - int(110 * self.s))
        if popup:  # floating card: content fills the card; phone-readable text
            self.s = self.W / 860
            p = int(48 * self.s)
            self.box = (p, p, self.W - p, self.H - p)

    def font(self, weight: str, px: float):
        return _font(str(self.font_dir / f"Inter-{weight}.ttf"), int(px * self.s))

    def mono_font(self, px: float):
        return _font(self.mono, int(px * self.s))


def _bg(c):
    if c.popup:  # transparent; render_popup() frames the content afterwards
        return Image.new("RGBA", (c.W, c.H), (0, 0, 0, 0))
    return _background(c.W, c.H).copy()


@lru_cache(maxsize=128)
def _font(path, size):
    return ImageFont.truetype(path, size)


@lru_cache(maxsize=4)
def _background(W, H):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    step = max(W, H) // 24
    for x in range(0, W, step):
        d.line([(x, 0), (x, H)], fill=(16, 20, 28), width=1)
    for y in range(0, H, step):
        d.line([(0, y), (W, y)], fill=(16, 20, 28), width=1)
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    r = max(W, H) // 2
    gd.ellipse([W * 0.75 - r, -r * 0.8, W * 0.75 + r, r * 1.2], fill=(28, 24, 14))
    glow = glow.filter(ImageFilter.GaussianBlur(r // 3))
    return ImageChops.add(img, glow)


def wrap(draw, text, font, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = f"{cur} {w}".strip()
        if draw.textlength(t, font=font) <= width or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit_text(draw, c, text, weight, px, width, max_lines, min_px=28):
    while px > min_px:
        f = c.font(weight, px)
        lines = wrap(draw, text, f, width)
        if len(lines) <= max_lines and all(draw.textlength(l, font=f) <= width for l in lines):
            return f, lines
        px -= 4
    f = c.font(weight, min_px)
    return f, wrap(draw, text, f, width)


def draw_lines(draw, lines, font, x, y, fill, spacing=1.18, anchor="la"):
    lh = font.size * spacing
    for i, line in enumerate(lines):
        draw.text((x, y + i * lh), line, font=font, fill=fill, anchor=anchor)
    return y + len(lines) * lh


def panel(draw, xy, c, outline=PANEL_EDGE, fill=PANEL, accent=None):
    r = int(22 * c.s)
    draw.rounded_rectangle(xy, r, fill=fill, outline=outline, width=max(2, int(2 * c.s)))
    if accent:
        x0, y0, x1, _ = xy
        draw.rounded_rectangle([x0, y0, x1, y0 + int(8 * c.s)], r, fill=accent)


def heading(draw, c, text, y=None):
    x0, y0, x1, _ = c.box
    f, lines = fit_text(draw, c, text, "ExtraBold", 84 if c.vertical else 76, x1 - x0, 2)
    y = y0 if y is None else y
    end = draw_lines(draw, lines, f, x0, y, HEAD)
    draw.rectangle([x0, end + 14 * c.s, x0 + 120 * c.s, end + 22 * c.s], fill=YELLOW)
    return end + 60 * c.s


# ---------------- scene renderers: each returns list of PIL images (reveal steps) ----------------

def r_title(v, c):
    img = _bg(c)
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = c.box
    f, lines = fit_text(d, c, v.get("heading", ""), "Black", 132 if c.vertical else 120, x1 - x0, 4)
    lh = f.size * 1.12
    sub = v.get("sub", "")
    sf, slines = fit_text(d, c, sub, "Medium", 52, x1 - x0, 3) if sub else (None, [])
    total = len(lines) * lh + (len(slines) * sf.size * 1.25 + 50 * c.s if sub else 0)
    y = y0 + (y1 - y0 - total) / 2
    for i, line in enumerate(lines):
        d.text((c.W / 2, y + i * lh), line, font=f, fill=YELLOW if i == len(lines) - 1 else HEAD, anchor="ma")
    y += len(lines) * lh + 50 * c.s
    if sub:
        for i, line in enumerate(slines):
            d.text((c.W / 2, y + i * sf.size * 1.25), line, font=sf, fill=FG, anchor="ma")
    return [img]


def r_bullets(v, c):
    bullets = v.get("bullets", [])[:5]
    frames = []
    for k in range(1, len(bullets) + 1):
        img = _bg(c)
        d = ImageDraw.Draw(img)
        x0, _, x1, y1 = c.box
        y = heading(d, c, v.get("heading", ""))
        laid = []
        for b in bullets:
            f, lines = fit_text(d, c, b, "SemiBold", 74 if c.vertical else 58, x1 - x0 - 110 * c.s,
                                2, min_px=34)
            laid.append((f, lines, len(lines) * f.size * 1.2 + 48 * c.s))
        gap = 34 * c.s
        if not c.popup:
            y += max(0, (y1 - y - sum(h for *_, h in laid) - gap * (len(laid) - 1)) / 2 - 30 * c.s)
        for i, (f, lines, h) in enumerate(laid[:k]):
            col = ACCENTS[i % len(ACCENTS)]
            panel(d, [x0, y, x1, y + h], c)
            d.ellipse([x0 + 30 * c.s, y + h / 2 - 14 * c.s, x0 + 58 * c.s, y + h / 2 + 14 * c.s], fill=col)
            draw_lines(d, lines, f, x0 + 90 * c.s, y + 22 * c.s, HEAD if i == k - 1 else FG, 1.2)
            y += h + gap
        frames.append(img)
    return frames or r_title(v, c)


def r_code(v, c):
    img = _bg(c)
    d = ImageDraw.Draw(img)
    x0, _, x1, y1 = c.box
    y = heading(d, c, v.get("heading", "")) if v.get("heading") else c.box[1]
    code = v.get("code", "").expandtabs(4).rstrip("\n").split("\n")[:16]
    longest = max((len(l) for l in code), default=1)
    inner_w = x1 - x0 - 100 * c.s
    px = min(56 if c.vertical else 42, inner_w / (0.6 * c.s) / max(longest, 1),
             (y1 - y - 140 * c.s) / (1.45 * c.s) / max(len(code), 1))
    f = c.mono_font(px)
    lh = f.size * 1.45
    h = len(code) * lh + 130 * c.s
    if not c.popup:
        y += max(0, (y1 - y - h) / 2 - 30 * c.s)
    panel(d, [x0, y, x1, y + h], c)
    for j, col in enumerate([RED, YELLOW, GREEN]):
        cx = x0 + (40 + j * 36) * c.s
        d.ellipse([cx - 11 * c.s, y + 29 * c.s, cx + 11 * c.s, y + 51 * c.s], fill=col)
    lang = v.get("language", "text")
    d.text((x1 - 30 * c.s, y + 40 * c.s), lang, font=c.font("Medium", 30), fill=DIM, anchor="rm")
    try:
        lexer = get_lexer_by_name(lang)
    except Exception:
        lexer = TextLexer()
    cx, cy = x0 + 50 * c.s, y + 90 * c.s
    for ttype, val in lex("\n".join(code) + "\n", lexer):
        color = next(col for t, col in CODE_COLORS if ttype in t)
        for n, part in enumerate(val.split("\n")):
            if n:
                cx, cy = x0 + 50 * c.s, cy + lh
            if part:
                d.text((cx, cy), part, font=f, fill=color)
                cx += d.textlength(part, font=f)
    return [img]


def r_stat(v, c):
    img = _bg(c)
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = c.box
    vf, vlines = fit_text(d, c, v.get("value", ""), "Black", 230 if c.vertical else 220, x1 - x0, 2, 60)
    lf, llines = fit_text(d, c, v.get("label", ""), "SemiBold", 62, x1 - x0, 3)
    total = len(vlines) * vf.size * 1.05 + 50 * c.s + len(llines) * lf.size * 1.25
    y = y0 + (y1 - y0 - total) / 2
    for i, l in enumerate(vlines):
        d.text((c.W / 2, y + i * vf.size * 1.05), l, font=vf, fill=YELLOW, anchor="ma")
    y += len(vlines) * vf.size * 1.05 + 50 * c.s
    for i, l in enumerate(llines):
        d.text((c.W / 2, y + i * lf.size * 1.25), l, font=lf, fill=HEAD, anchor="ma")
    return [img]


def r_compare(v, c):
    frames = []
    sides = [v.get("left", {}), v.get("right", {})]
    for k in (1, 2):
        img = _bg(c)
        d = ImageDraw.Draw(img)
        x0, _, x1, y1 = c.box
        y = heading(d, c, v.get("heading", "")) if v.get("heading") else c.box[1]
        gap = 40 * c.s
        if c.vertical:  # stacked
            h = (y1 - y - gap) / 2
            rects = [[x0, y, x1, y + h], [x0, y + h + gap, x1, y1]]
        else:
            w = (x1 - x0 - gap) / 2
            yb = min(y1, y + 430 * c.s) if c.popup else y1
            rects = [[x0, y, x0 + w, yb], [x0 + w + gap, y, x1, yb]]
        for i in range(k):
            side, r, col = sides[i], rects[i], (BLUE, YELLOW)[i]
            panel(d, r, c, accent=col)
            hf, hl = fit_text(d, c, side.get("heading", ""), "ExtraBold", 70 if c.vertical else 60, r[2] - r[0] - 80 * c.s, 1)
            yy = draw_lines(d, hl, hf, r[0] + 40 * c.s, r[1] + 44 * c.s, col) + 20 * c.s
            for p in side.get("points", [])[:4]:
                pf, pl = fit_text(d, c, "• " + p, "Medium", 58 if c.vertical else 46, r[2] - r[0] - 80 * c.s, 2, 30)
                yy = draw_lines(d, pl, pf, r[0] + 40 * c.s, yy, FG) + 14 * c.s
        frames.append(img)
    return frames


def _arrow(d, a, b, c, col):
    import math
    d.line([a, b], fill=col, width=max(3, int(6 * c.s)))
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    L = 26 * c.s
    p1 = (b[0] - L * math.cos(ang - 0.5), b[1] - L * math.sin(ang - 0.5))
    p2 = (b[0] - L * math.cos(ang + 0.5), b[1] - L * math.sin(ang + 0.5))
    d.polygon([b, p1, p2], fill=col)


def r_flow(v, c):
    nodes = v.get("nodes", [])[:5]
    frames = []
    for k in range(1, len(nodes) + 1):
        img = _bg(c)
        d = ImageDraw.Draw(img)
        x0, _, x1, y1 = c.box
        y = heading(d, c, v.get("heading", "")) if v.get("heading") else c.box[1]
        n = len(nodes)
        gap = 90 * c.s
        rects = []
        if c.vertical:
            h = min(170 * c.s, (y1 - y - gap * (n - 1)) / n)
            top = y if c.popup else y + (y1 - y - (n * h + (n - 1) * gap)) / 2
            for i in range(n):
                yy = top + i * (h + gap)
                rects.append([x0 + 60 * c.s, yy, x1 - 60 * c.s, yy + h])
        else:
            w = (x1 - x0 - gap * (n - 1)) / n
            h = min(260 * c.s, (y1 - y))
            yy = y if c.popup else y + (y1 - y - h) / 2
            for i in range(n):
                rects.append([x0 + i * (w + gap), yy, x0 + i * (w + gap) + w, yy + h])
        for i in range(k):
            r = rects[i]
            col = ACCENTS[i % len(ACCENTS)]
            panel(d, r, c, outline=col if i == k - 1 else PANEL_EDGE, accent=col)
            f, lines = fit_text(d, c, nodes[i], "Bold", 58, r[2] - r[0] - 40 * c.s, 2, 30)
            th = len(lines) * f.size * 1.15
            for j, l in enumerate(lines):
                d.text(((r[0] + r[2]) / 2, (r[1] + r[3]) / 2 - th / 2 + j * f.size * 1.15 + 4 * c.s),
                       l, font=f, fill=HEAD, anchor="ma")
            if i:
                p = rects[i - 1]
                if c.vertical:
                    _arrow(d, ((p[0] + p[2]) / 2, p[3] + 12 * c.s), ((r[0] + r[2]) / 2, r[1] - 12 * c.s), c, DIM)
                else:
                    _arrow(d, (p[2] + 12 * c.s, (p[1] + p[3]) / 2), (r[0] - 12 * c.s, (r[1] + r[3]) / 2), c, DIM)
        frames.append(img)
    return frames or r_title(v, c)


RENDERERS = {"title": r_title, "bullets": r_bullets, "code": r_code,
             "stat": r_stat, "compare": r_compare, "flow": r_flow}


def render_scene(visual: dict, size, cfg, outdir: Path, idx: int) -> list[Path]:
    c = Canvas(size, cfg)
    fn = RENDERERS.get(visual.get("type"), r_title)
    paths = []
    for k, img in enumerate(fn(visual, c)):
        p = outdir / f"scene_{idx:02d}_{k}.png"
        img.save(p)
        paths.append(p)
    return paths


def render_popup(visual: dict, cfg, out: Path, width=980, max_h=900) -> Path:
    """Floating RGBA card sized to its content (final reveal state), for overlaying on gameplay."""
    c = Canvas((width, max_h), cfg, popup=True)
    fn = RENDERERS.get(visual.get("type"), r_title)
    content = fn(visual, c)[-1]
    _, top, _, bottom = content.getchannel("A").getbbox() or (0, 0, 0, max_h)
    pad = int(48 * c.s)
    h = bottom - top + 2 * pad
    card = Image.new("RGBA", (width, h + 10), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    r = int(40 * c.s)
    d.rounded_rectangle([6, 10, width - 1, h + 9], r, fill=(0, 0, 0, 120))           # drop shadow
    d.rounded_rectangle([0, 0, width - 7, h - 1], r, fill=BG + (242,), outline=YELLOW,
                        width=max(4, int(6 * c.s)))
    card.alpha_composite(content.crop((0, top, width, bottom)), (0, pad))
    card.save(out)
    return out
