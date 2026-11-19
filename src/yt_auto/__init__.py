"""yt-auto: automated faceless tech-explainer pipeline.

  yt-auto make --format short [--topic "..."]   # full local build -> out/<slug>-<format>/
  yt-auto make --from out/<dir>                  # rebuild an existing job, reusing its script
"""

import argparse
import json
import re
import time
from datetime import date
from pathlib import Path

from .config import load_config


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:50]


def _stage(name: str):
    print(f"\n▶ {name}", flush=True)
    return time.time()


def _done(t0):
    print(f"  done in {time.time() - t0:.1f}s", flush=True)


def build(cfg: dict, fmt: str, topic: str | None = None, job: Path | None = None) -> Path:
    from . import assemble, captions, render, script, thumbnail, tts

    root = cfg["_root"]
    out_root = root / cfg["output_dir"]
    out_root.mkdir(exist_ok=True)

    # --- script (cached) ---
    if job and (job / "script.json").exists():
        sc = json.loads((job / "script.json").read_text())
        fmt = json.loads((job / "job.json").read_text())["format"]
    else:
        t0 = _stage("script + fact-check (claude -p)")
        past = [json.loads(p.read_text())["title"] for p in out_root.glob("*/script.json")]
        sc = script.write_script(cfg, fmt, topic, past)
        _done(t0)
        job = job or out_root / f"{date.today():%Y%m%d}-{_slug(sc['title'])}-{fmt}"
        job.mkdir(parents=True, exist_ok=True)
        (job / "script.json").write_text(json.dumps(sc, indent=2))
        (job / "job.json").write_text(json.dumps({"format": fmt, "created": time.time()}))
    size = tuple(cfg["formats"][fmt]["size"])
    words = sum(len(s["narration"].split()) for s in sc["scenes"])
    print(f"  {sc['title']!r}: {len(sc['scenes'])} scenes, {words} words")

    t0 = _stage("voice (kokoro)")
    durs = tts.synth_scenes(sc["scenes"], cfg, job)
    _done(t0)
    print(f"  {sum(durs):.1f}s of narration")

    t0 = _stage("visuals")
    frames_dir = job / "frames"
    frames_dir.mkdir(exist_ok=True)
    frames = [render.render_scene(s["visual"], size, cfg, frames_dir, i) for i, s in enumerate(sc["scenes"])]
    _done(t0)

    t0 = _stage("captions (faster-whisper alignment)")
    full_text = " ".join(s["narration"] for s in sc["scenes"])
    words_t = captions.word_timings(job / "narration.wav", full_text)
    captions.write_srt(words_t, job / "captions.srt")
    ass = None
    if fmt == "short":
        ass = job / "captions.ass"
        captions.write_ass(words_t, size, ass)
    _done(t0)

    t0 = _stage("assemble (ffmpeg)")
    assemble.assemble(frames, durs, job / "narration.wav", ass, size, cfg, job / "video.mp4",
                      music_dir=root / "assets" / "music")
    _done(t0)

    thumbnail.make_thumbnail(sc, cfg, job / "thumbnail.jpg")
    meta = {"title": sc["title"], "description": sc["description"], "tags": sc["tags"],
            "format": fmt, "duration_s": round(sum(durs), 1)}
    if fmt == "short" and "#shorts" not in meta["description"].lower():
        meta["description"] += "\n#shorts"
    (job / "metadata.json").write_text(json.dumps(meta, indent=2))
    print(f"\n✔ {job / 'video.mp4'}")
    return job


def main():
    ap = argparse.ArgumentParser(prog="yt-auto")
    sub = ap.add_subparsers(dest="cmd", required=True)
    mk = sub.add_parser("make", help="build one video locally")
    mk.add_argument("--format", choices=["short", "long"], default="short")
    mk.add_argument("--topic")
    mk.add_argument("--from", dest="job", type=Path, help="existing job dir to rebuild")
    a = ap.parse_args()
    cfg = load_config()
    if a.cmd == "make":
        build(cfg, a.format, a.topic, a.job.resolve() if a.job else None)
