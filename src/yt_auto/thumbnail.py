"""Stage 9: 1280x720 thumbnail from script['thumbnail_text']."""

from pathlib import Path

from PIL import ImageDraw

from .render import BG, HEAD, PANEL_EDGE, YELLOW, Canvas, _background, fit_text


def make_thumbnail(script: dict, cfg: dict, out: Path):
    W, H = 1280, 720
    c = Canvas((W, H), cfg)
    img = _background(W, H).copy()
    d = ImageDraw.Draw(img)
    words = script.get("thumbnail_text", script["title"]).upper().split()
    split = max(1, len(words) // 2)
    top, bottom = " ".join(words[:split]), " ".join(words[split:])
    x0, x1 = 70, W - 70
    f1, l1 = fit_text(d, c, top, "Black", 190, x1 - x0, 1, 60)
    f2, l2 = fit_text(d, c, bottom, "Black", 190, x1 - x0, 1, 60) if bottom else (f1, [])
    total = f1.size * 1.05 + (f2.size * 1.05 if l2 else 0)
    y = (H - total) / 2
    for line in l1:
        d.text((x0 + 6, y + 6), line, font=f1, fill=(0, 0, 0))
        d.text((x0, y), line, font=f1, fill=HEAD)
    y += f1.size * 1.05
    for line in l2:
        tw = d.textlength(line, font=f2)
        d.rounded_rectangle([x0 - 20, y - 10, x0 + tw + 20, y + f2.size * 1.05], 18, fill=YELLOW)
        d.text((x0, y), line, font=f2, fill=BG)
    d.rectangle([0, H - 14, W, H], fill=PANEL_EDGE)
    img.save(out, quality=92)
