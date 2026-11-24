"""Re-cuts of finished films, plus keeping films after an ephemeral CI run.

  make_short(cfg, sc, timings, film_job)    -> film_job/short/  (1080x1920 teaser of the cold open, <= 58 s)
  finish_short(short_job, film_url)         put the film's link into the Short's description
  persist_film(cfg, job, sc)                on GitHub Actions: commit the film's code back to the repo and
                                            attach video/script/thumbnails to the release `film-<slug>`
  build_compilation(cfg, films, job)        8-10 min long-form from 3-4 finished films (monthly)
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from datetime import date
from pathlib import Path

from .film import (FPS, VOICE_AT, _claude_json, _run, film_root, make_description, make_title, master_audio,
                   minutes_for, stage_sounds, stage_voice, write_srt)

SHORT_END = 75            # end-card frames (film/src/films/cuts/Cuts.tsx)
SHORT_MAX_S = 58.0        # whole Short incl. end card
TITLE_CARD = 360          # every film ends on a 12 s title card; compilations trim it
CHAPTER = 60
OUTRO = 360


def _ffprobe_s(p: Path) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                capture_output=True, text=True, check=True).stdout.strip())


def _public_copy(cfg: dict, src: Path, name: str) -> str:
    """Copy a video into film/public/cuts/ (gitignored) so Remotion can read it; returns its public path."""
    d = film_root(cfg) / "public/cuts"
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, d / name)
    return f"cuts/{name}"


def _render(cfg: dict, comp: str, out: Path, props: dict) -> None:
    out = Path(out).resolve()   # remotion runs in film/
    pf = out.with_suffix(".props.json")
    pf.write_text(json.dumps(props))
    _run(["npx", "remotion", "render", comp, str(out), f"--props={pf}", "--log=error"], film_root(cfg),
         timeout=4 * 3600, what=f"remotion render {comp}")


# ---------------------------------------------------------------- Short (cold-open teaser)

def short_end_line(sc: dict, timings: dict) -> int:
    """1-based index of the line the Short ends on: the writer's cliffhanger if it fits, else the last line
    that does (preferring one followed by a long pause, i.e. a beat)."""
    limit = (SHORT_MAX_S - SHORT_END / FPS) * FPS
    lines = timings["lines"]
    fits = [i for i, ln in enumerate(lines, 1)
            if ln["endFrame"] + VOICE_AT + int(sc["lines"][i - 1].get("pause", 0.5) * FPS) <= limit]
    want = int(sc.get("short_end_line") or 0)
    if want in fits:
        return want
    if not fits:
        return 1
    beats = [i for i in fits if sc["lines"][i - 1].get("pause", 0) >= 0.9]
    return (beats or fits)[-1]


def make_short(cfg: dict, sc: dict, timings: dict, film_job: Path) -> Path:
    film_job = Path(film_job).resolve()
    job = film_job / "short"
    if (job / "video.mp4").exists():
        return job
    job.mkdir(exist_ok=True)
    n = short_end_line(sc, timings)
    pause = sc["lines"][n - 1].get("pause", 0.8)
    to = timings["lines"][n - 1]["endFrame"] + VOICE_AT + int(min(pause, 1.2) * FPS)
    lines = [{"text": ln["text"], "start": ln["startFrame"] + VOICE_AT, "end": ln["endFrame"] + VOICE_AT}
             for ln in timings["lines"][:n]]
    src = _public_copy(cfg, film_job / "video.mp4", f"{sc['slug']}.mp4")
    raw = job / "raw.mp4"
    _render(cfg, "ShortCut", raw, {"src": src, "from": 0, "to": to, "hook": sc.get("short_hook") or sc["subject"],
                                   "lines": lines})
    master_audio(raw, job / "video.mp4")
    raw.unlink(missing_ok=True)
    write_srt({"lines": timings["lines"][:n]}, job / "captions.srt")
    (job / "timing.json").write_text(json.dumps(
        [{"start": ln["start"] + VOICE_AT / FPS, "end": ln["end"] + VOICE_AT / FPS, "text": ln["text"]}
         for ln in timings["lines"][:n]]))
    hook = " ".join((sc.get("short_hook") or sc["subject"]).split())
    title = hook[:1].upper() + hook[1:]
    tags = list(dict.fromkeys([*sc["hashtags"][:3]]))
    desc = (f"{' '.join(sc['summary'].split())}\n\nFull story: {{FILM_URL}}\n\n"
            + " ".join("#" + re.sub(r"[^0-9A-Za-z]", "", t) for t in tags) + " #shorts")
    (job / "script.json").write_text(json.dumps({"title": title, "lines": [{"text": ln["text"]} for ln in sc["lines"][:n]],
                                                 "parent_slug": sc["slug"]}, indent=2, ensure_ascii=False))
    (job / "job.json").write_text(json.dumps({"format": "short", "style": "film-cut", "created": time.time()}))
    (job / "metadata.json").write_text(json.dumps({"title": title, "description": desc, "tags": sc["tags"],
                                                   "format": "short", "duration_s": round(_ffprobe_s(job / "video.mp4"), 1)},
                                                  indent=2, ensure_ascii=False))
    print(f"  short: {title!r}, ends on line {n}, {_ffprobe_s(job / 'video.mp4'):.1f}s")
    return job


def finish_short(short_job: Path, film_url: str | None) -> None:
    meta = json.loads((short_job / "metadata.json").read_text())
    meta["description"] = meta["description"].replace(
        "{FILM_URL}", film_url or "on the channel (Errata, @ErrataStories)")
    (short_job / "metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------- keep films after a CI run

def _on_ci() -> bool:
    return os.environ.get("GITHUB_ACTIONS") == "true"


def persist_film(cfg: dict, job: Path, sc: dict) -> str | None:
    """GitHub Actions runners are wiped after each run. Commit the generated film code (scenes, score,
    narration + timings) back to the repo, and attach the render, script and thumbnails to the release
    `film-<slug>` (needed for compilations and thumbnail tests). Returns the release URL. No-op locally."""
    if not _on_ci():
        return None
    root = cfg["_root"]
    slug = sc["slug"]
    paths = [f"film/src/films/{slug}", "film/src/Root.tsx", "film/scripts/make_sounds.py",
             f"film/narration/{slug}.json", f"film/public/voice/{slug}.json"]
    try:
        subprocess.run(["git", "add", "--", *[p for p in paths if (root / p).exists()]], cwd=root, check=True)
        ident = ["-c", "user.name=yt-auto", "-c", "user.email=yt-auto@users.noreply.github.com"]
        if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=root).returncode != 0:
            subprocess.run(["git", *ident, "commit", "-m", f"film: {sc['subject']} ({slug}) [skip ci]"], cwd=root, check=True)
            # the runner has other uncommitted files (rendered audio etc.): autostash them around the rebase;
            # the rebase needs an identity too (2026-11-22: "empty ident name" lost the Mars Orbiter code)
            for _ in range(3):
                if subprocess.run(["git", *ident, "pull", "--rebase", "--autostash", "-q", "origin", "main"], cwd=root).returncode == 0 \
                        and subprocess.run(["git", "push", "-q", "origin", "HEAD:main"], cwd=root).returncode == 0:
                    break
                time.sleep(10)
            else:
                print("  persist: could not push the film code after 3 tries", flush=True)
    except Exception as e:  # noqa: BLE001 - never lose the video over a git hiccup
        print(f"  persist: git push failed: {e}", flush=True)
    tag = f"film-{slug}"
    assets = [str(job / f) for f in ("video.mp4", "script.json", "thumbnail.jpg", "thumbnail_b.jpg", "thumbnail_c.jpg")
              if (job / f).exists()]
    try:
        if subprocess.run(["gh", "release", "view", tag], cwd=root, capture_output=True).returncode != 0:
            subprocess.run(["gh", "release", "create", tag, "--title", sc["subject"], "--notes",
                            "Film render, script and thumbnail variants (yt-auto).", "--latest=false"],
                           cwd=root, check=True, capture_output=True)
        subprocess.run(["gh", "release", "upload", tag, *assets, "--clobber"], cwd=root, check=True, capture_output=True)
        repo = os.environ.get("GITHUB_REPOSITORY", "")
        return f"https://github.com/{repo}/releases/tag/{tag}"
    except Exception as e:  # noqa: BLE001
        print(f"  persist: release upload failed: {e}", flush=True)
        return None


def fetch_film(cfg: dict, slug: str, dest: Path) -> Path:
    """A finished film's job dir: the local out/ one, else video + script from the release film-<slug>."""
    out_root = cfg["_root"] / cfg["output_dir"]
    for j in sorted(out_root.glob("*-film"), reverse=True):
        sp = j / "script.json"
        if sp.exists() and (j / "video.mp4").exists() and json.loads(sp.read_text()).get("slug") == slug:
            return j
    dest.mkdir(parents=True, exist_ok=True)
    _run(["gh", "release", "download", f"film-{slug}", "-p", "video.mp4", "-p", "script.json", "-D", str(dest),
          "--clobber"], cfg["_root"], timeout=1800, what=f"download film-{slug}")
    return dest


# ---------------------------------------------------------------- monthly compilation

COMP_SCHEMA = {
    "type": "object",
    "required": ["subject", "order", "labels", "intro", "summary", "title_card", "thumbnail", "hashtags", "tags"],
    "properties": {
        "subject": {"type": "string", "description": "the theme as a viewer searches it, e.g. '4 Bugs That Cost Billions'"},
        "order": {"type": "array", "items": {"type": "string"}, "description": "the film slugs, best story last"},
        "labels": {"type": "array", "items": {"type": "string"}, "description": "chapter label per film in order, 1-3 words"},
        "intro": {"type": "array", "minItems": 3, "maxItems": 6, "items": {
            "type": "object", "required": ["text", "pause"],
            "properties": {"text": {"type": "string"}, "pause": {"type": "number"}}}},
        "summary": {"type": "string"},
        "title_card": {"type": "object", "required": ["word", "line", "accent"], "properties": {
            "word": {"type": "string"}, "line": {"type": "string"}, "accent": {"type": "string"}}},
        "thumbnail": {"type": "object", "required": ["word", "line"], "properties": {
            "word": {"type": "string"}, "line": {"type": "string"}}},
        "hashtags": {"type": "array", "minItems": 3, "maxItems": 5, "items": {"type": "string"}},
        "tags": {"type": "array", "minItems": 5, "maxItems": 15, "items": {"type": "string"}},
    },
}


def _ts(s: float) -> str:
    s = int(s)
    return f"{s // 60}:{s % 60:02d}" if s < 3600 else f"{s // 3600}:{s // 60 % 60:02d}:{s % 60:02d}"


def build_compilation(cfg: dict, films: list[dict], job: Path | None = None) -> Path:
    """films: [{"slug", "subject"}] (3-4 finished films). Voiced intro + chapter cards + the films without
    their title cards + one outro title card; chapters in the description."""
    from . import _done, _stage
    from .agents import load_prompt
    from .film import stage_thumbnail

    out_root = cfg["_root"] / cfg["output_dir"]
    stamp = f"{date.today():%Y%m}"
    job = job or out_root / f"{date.today():%Y%m%d}-compilation-{stamp}"
    job.mkdir(parents=True, exist_ok=True)
    if (job / "script.json").exists():
        sc = json.loads((job / "script.json").read_text())
    else:
        t0 = _stage("compilation plan (claude -p)")
        listing = "\n".join(f"- {f['slug']}: {f['subject']}" for f in films)
        prompt = load_prompt("compilation_writer", films=listing, n=len(films))
        known = {f["slug"] for f in films}
        # free helper model first; its plan is only used if it orders every film exactly once and the
        # labels line up, otherwise Claude plans it (quality never drops below Claude's)
        from . import helper
        sc = helper.call_json(prompt, COMP_SCHEMA, cfg, "compilation")
        if not sc or sorted(sc.get("order", [])) != sorted(known) or len(sc.get("labels", [])) != len(known):
            sc = _claude_json(prompt, cfg, COMP_SCHEMA)
        sc["order"] = [s for s in sc["order"] if s in known] or [f["slug"] for f in films]
        sc["slug"] = f"comp{stamp}"
        sc["lines"] = sc["intro"]
        _done(t0)
        (job / "script.json").write_text(json.dumps(sc, indent=2, ensure_ascii=False))
        (job / "job.json").write_text(json.dumps({"format": "compilation", "style": "compilation", "created": time.time()}))

    t0 = _stage("films + intro voice")
    parts, all_sources, caps = [], [], []
    for i, slug in enumerate(sc["order"]):
        fj = fetch_film(cfg, slug, job / "films" / slug)
        fsc = json.loads((fj / "script.json").read_text())
        frames = int(round(_ffprobe_s(fj / "video.mp4") * FPS)) - TITLE_CARD
        parts.append({"src": _public_copy(cfg, fj / "video.mp4", f"{slug}.mp4"),
                      "label": (sc["labels"][i] if i < len(sc["labels"]) else fsc["subject"]), "frames": frames,
                      "subject": fsc["subject"], "slug": slug})
        all_sources += fsc.get("sources", [])
        tim = film_root(cfg) / "public/voice" / f"{slug}.json"
        caps.append(json.loads(tim.read_text()) if tim.exists() else None)
    timings = stage_voice(cfg, {"slug": sc["slug"], "lines": sc["intro"]})
    intro_frames = int(round(timings["duration"] * FPS)) + 2 * VOICE_AT + 30
    _done(t0)

    t0 = _stage("render (Remotion Compilation)")
    stage_sounds(cfg)
    raw = job / "raw.mp4"
    _render(cfg, "Compilation", raw, {
        "title": sc["subject"], "introVoice": f"voice/{sc['slug']}.wav", "introFrames": intro_frames,
        "introLines": [{"text": ln["text"], "start": ln["startFrame"] + VOICE_AT, "end": ln["endFrame"] + VOICE_AT}
                       for ln in timings["lines"]],
        "segments": [{"src": p["src"], "label": p["label"], "frames": p["frames"]} for p in parts],
        "card": sc["title_card"]})
    lufs, peak = master_audio(raw, job / "video.mp4")
    raw.unlink(missing_ok=True)
    _done(t0)

    # captions + chapters: intro, then each film's own line timings shifted to where it plays
    rows, chapters, at = [], [("0:00", "Intro")], intro_frames
    for ln in timings["lines"]:
        rows.append({"text": ln["text"], "start": ln["start"] + VOICE_AT / FPS, "end": ln["end"] + VOICE_AT / FPS})
    for p, cap in zip(parts, caps):
        chapters.append((_ts(at / FPS), f"{p['label']}: {p['subject']}"))
        vstart = (at + CHAPTER) / FPS
        for ln in (cap or {}).get("lines", []):
            if (ln["start"] + VOICE_AT / FPS) * FPS < p["frames"]:
                rows.append({"text": ln["text"], "start": vstart + ln["start"] + VOICE_AT / FPS,
                             "end": vstart + ln["end"] + VOICE_AT / FPS})
        at += CHAPTER + p["frames"]
    write_srt({"lines": rows}, job / "captions.srt", offset=0)
    (job / "timing.json").write_text(json.dumps(rows))
    stage_thumbnail(cfg, {}, {"thumbnail": sc["thumbnail"], "thumbnail_alts": []}, job)

    dur = _ffprobe_s(job / "video.mp4")
    uniq = list({s["url"]: s for s in all_sources}.values())[:8]
    desc = make_description(sc["summary"], uniq, sc["hashtags"])
    head, _, rest = desc.partition("\n\n")
    desc = head + "\n\n" + "\n".join(f"{t} {name}" for t, name in chapters) + "\n\n" + rest
    sc["title"] = make_title(sc["subject"], minutes_for(dur))
    sc["description"] = desc
    (job / "script.json").write_text(json.dumps(sc, indent=2, ensure_ascii=False))
    (job / "metadata.json").write_text(json.dumps({
        "title": sc["title"], "description": desc, "tags": sc["tags"], "format": "compilation",
        "duration_s": round(dur, 1), "loudness_lufs": lufs, "speech_coverage": None,
        "films": sc["order"]}, indent=2, ensure_ascii=False))
    print(f"\n✔ {job / 'video.mp4'}  {sc['title']!r} ({dur / 60:.1f} min)")
    return job
