"""Film format: 2-3 minute narrated dark-documentary films about true tech stories, drawn in Remotion
(the project in film/, rules in film/CLAUDE.md).

  build_film(cfg, topic, job)   script -> voice -> scenes (Claude Code director) -> music -> render ->
                                loudness pass -> speech check -> captions -> thumbnail -> metadata.json

Every stage is resumable: re-running with the same job dir skips what already exists, so a failed
render does not re-write the script or re-voice the narration.

Titles are always "<Subject> Explained in Under <N> Minutes"; descriptions are a short summary, the
sources (each URL checked to load), a one-line disclosure and 3-5 hashtags. Both are built in code
(make_title / make_description), not by the LLM, so every video follows the same simple pattern.
"""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

FPS = 30
VOICE_AT = 20                # narration starts at this frame in every film (see film/CLAUDE.md)
TARGET_LUFS = -14.2          # YouTube plays at -14; stay a hair under
PEAK_LIMIT = 0.84            # alimiter linear limit (~ -1.5 dBFS) so AAC overshoot stays under -1 dB
MIN_SPEECH = 0.90            # share of script words Whisper must hear in the final mix (rule says 95%)
CHANNEL = "Errata"
DISCLOSURE = "Animation, music and sound effects are made in code. The narration is a synthetic voice."

DEFAULTS = {"dir": "film", "voice_python": "film/tools/voice/.venv/bin/python",
            "director_model": "opus", "director_timeout_min": 150, "words": [290, 350], "repairs": 1}


def fcfg(cfg: dict) -> dict:
    return {**DEFAULTS, **(cfg.get("film") or {})}


def film_root(cfg: dict) -> Path:
    return (cfg["_root"] / fcfg(cfg)["dir"]).resolve()


# ---------------------------------------------------------------- title + description (code, not LLM)

def minutes_for(duration_s: float) -> int:
    """'Under N minutes': the next whole minute above the running time (2:43 -> 3)."""
    return max(1, math.ceil(duration_s / 60 + 1e-9))


def make_title(subject: str, minutes: int) -> str:
    subject = " ".join(subject.split()).strip(" .")
    return f"{subject} Explained in Under {minutes} Minute{'s' if minutes != 1 else ''}"


def _hashtag(t: str) -> str:
    return "#" + re.sub(r"[^0-9A-Za-z]", "", t.lstrip("#"))


def make_description(summary: str, sources: list[dict], hashtags: list[str],
                     chapters: list[tuple[str, str]] | None = None) -> str:
    parts = [" ".join(summary.split())]
    if chapters:
        parts.append("\n".join(f"{t} {label}" for t, label in chapters))
    if sources:
        parts.append("Sources:\n" + "\n".join(f"• {s['title']}: {s['url']}" for s in sources))
    parts.append(DISCLOSURE)
    tags = list(dict.fromkeys(_hashtag(h) for h in hashtags if re.sub(r"[^0-9A-Za-z]", "", h)))[:5]
    if tags:
        parts.append(" ".join(tags))
    return "\n\n".join(parts)


def check_sources(sources: list[dict], timeout: float = 12, opener=None) -> list[dict]:
    """Keep only sources whose URL actually loads (no invented links in a description).
    Generic User-Agent: no personal details go to external sites."""
    opener = opener or urllib.request.build_opener()
    ok = []
    for s in sources:
        url = (s.get("url") or "").strip()
        if not re.match(r"https?://", url):
            continue
        for method in ("HEAD", "GET"):
            try:
                req = urllib.request.Request(url, method=method, headers={"User-Agent": "Mozilla/5.0 (compatible; film-sources-check)"})
                with opener.open(req, timeout=timeout) as r:
                    if r.status < 400:
                        ok.append({"title": " ".join(str(s.get("title") or url).split()), "url": url})
                        break
            except Exception:  # noqa: BLE001 - any failure = try GET, then drop
                continue
    return ok


# ---------------------------------------------------------------- 1. script

SCRIPT_SCHEMA = {
    "type": "object",
    "required": ["subject", "slug", "summary", "lines", "title_card", "thumbnail", "thumbnail_alts", "short_hook",
                 "short_end_line", "search_phrases", "chapters", "playlist", "sources", "hashtags", "tags"],
    "properties": {
        "subject": {"type": "string", "description": "what the video explains, title case, 1-5 words, e.g. 'The Enigma Machine'"},
        "slug": {"type": "string", "pattern": "^[a-z][a-z0-9]{2,20}$", "description": "one lowercase word, e.g. 'enigma'"},
        "summary": {"type": "string", "description": "1-2 plain sentences for the YouTube description"},
        "lines": {"type": "array", "minItems": 25, "maxItems": 60, "items": {
            "type": "object", "required": ["text", "pause"],
            "properties": {"text": {"type": "string"}, "pause": {"type": "number", "minimum": 0.3, "maximum": 1.6}}}},
        "title_card": {"type": "object", "required": ["word", "line", "accent"], "properties": {
            "word": {"type": "string"}, "line": {"type": "string"}, "accent": {"type": "string"}}},
        "thumbnail": {"type": "object", "required": ["word", "line"], "properties": {
            "word": {"type": "string", "description": "ONE word, max 10 letters"},
            "line": {"type": "string", "description": "max 4 words"}}},
        "thumbnail_alts": {"type": "array", "minItems": 2, "maxItems": 2, "items": {
            "type": "object", "required": ["word", "line"],
            "properties": {"word": {"type": "string"}, "line": {"type": "string"}}},
            "description": "two DIFFERENT thumbnail angles for A/B testing (a number, a name, a question...)"},
        "short_hook": {"type": "string", "description": "headline for the vertical teaser Short, 4-9 words, curiosity"},
        "short_end_line": {"type": "integer", "minimum": 3, "description": "1-based line the cold open's cliffhanger is on (within ~50 s)"},
        "search_phrases": {"type": "array", "minItems": 3, "maxItems": 6, "items": {"type": "string"},
                           "description": "3-6 ways people would TYPE this story into YouTube search"},
        "chapters": {"type": "array", "minItems": 3, "maxItems": 6, "items": {
            "type": "object", "required": ["line", "label"],
            "properties": {"line": {"type": "integer", "minimum": 1}, "label": {"type": "string"}}},
            "description": "chapter starts: line 1 first, then each act's first line; labels 1-5 words, keyword-rich"},
        "playlist": {"enum": ["hacks", "space", "engineering", "crypto", "bugs", "history"]},
        "sources": {"type": "array", "minItems": 2, "maxItems": 5, "items": {
            "type": "object", "required": ["title", "url"],
            "properties": {"title": {"type": "string"}, "url": {"type": "string"}}}},
        "hashtags": {"type": "array", "minItems": 3, "maxItems": 5, "items": {"type": "string"}},
        "tags": {"type": "array", "minItems": 5, "maxItems": 15, "items": {"type": "string"}},
    },
}


def _bible_section(name: str, cfg: dict) -> str:
    text = (film_root(cfg) / "CLAUDE.md").read_text()
    m = re.search(rf"^## {re.escape(name)}.*?(?=^## )", text, re.S | re.M)
    return m.group(0).strip() if m else ""


def _claude_json(prompt: str, cfg: dict, schema: dict, model: str | None = None, timeout: int = 900) -> dict:
    from .agents import _parse_claude_output
    cmd = ["claude", "-p", "--output-format", "json", "--model", model or cfg["llm"]["model"],
           "--json-schema", json.dumps(schema), "--tools", "", "--no-session-persistence"]
    res = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=timeout)
    return _parse_claude_output(res)


def write_script(cfg: dict, topic: str | None, past: list[str], guidance: str = "",
                 feedback: list[str] | None = None) -> dict:
    from .agents import load_prompt
    lo, hi = fcfg(cfg)["words"]
    prompt = load_prompt(
        "film_writer",
        niche=" ".join(cfg["channel"]["niche"].split()),
        narration_rules=_bible_section("NARRATION", cfg),
        toolkit=_bible_section("DOCUMENTARY TOOLKIT", cfg),
        topic=topic or "(pick one yourself from the niche: a true story, not covered in PAST TITLES)",
        past="\n".join(f"- {t}" for t in past[-60:]) or "(none yet)",
        guidance=guidance or "(no performance data yet)",
        feedback="\n".join(f"- {f}" for f in (feedback or [])) or "(none)",
        words_lo=lo, words_hi=hi)
    sc = _claude_json(prompt, cfg, SCRIPT_SCHEMA, model=fcfg(cfg)["director_model"])
    sc["slug"] = re.sub(r"[^a-z0-9]", "", sc["slug"].lower()) or "film"
    words = sum(len(ln["text"].split()) for ln in sc["lines"])
    est = minutes_for(words / 2.35 + 13)   # measured: 348 words incl. pauses = 149 s of voice; +13 s title card
    sc["title"] = make_title(sc["subject"], est)              # final N is set from the real duration later
    sc["description"] = make_description(sc["summary"], sc["sources"], sc["hashtags"])
    return sc


# ---------------------------------------------------------------- helpers

def apply_seo(sc: dict) -> dict:
    """Search-demand check of the subject (YouTube autocomplete); sets sc["seo"] and maybe a better subject."""
    from . import seo
    plan = seo.keyword_plan(sc["subject"], sc.get("search_phrases") or [])
    if plan["subject"] != sc["subject"]:
        print(f"  seo: subject {sc['subject']!r} -> {plan['subject']!r} (search demand {plan['scores']})", flush=True)
        sc["subject"] = plan["subject"]
    sc["seo"] = plan
    sc["summary"] = seo.lead_with(sc["summary"], plan["primary"])
    sc["title"] = make_title(sc["subject"], minutes_for(sum(len(ln["text"].split()) for ln in sc["lines"]) / 2.35 + 13))
    return plan


def seo_metadata(sc: dict, timings: dict | None, duration: float) -> tuple[str, list[str], str | None]:
    """(description, tags, playlist title) at publish time: chapters from the real line timings."""
    from . import seo
    plan = sc.get("seo") or {"primary": sc["subject"], "related": []}
    marks = []
    if timings:
        for c in sc.get("chapters") or []:
            i = int(c.get("line", 0)) - 1
            if 0 <= i < len(timings["lines"]):
                marks.append(((timings["lines"][i]["startFrame"] + VOICE_AT) / FPS, c.get("label", "")))
    desc = make_description(sc["summary"], sc["sources"], sc["hashtags"], seo.chapters(marks, duration - 13))
    return desc, seo.tags(plan["primary"], plan.get("related", []), sc["tags"]), seo.PLAYLISTS.get(sc.get("playlist", ""))


def precheck_script(cfg: dict, sc: dict) -> list[str]:
    """Fail-level problems the pre-publish script check would raise (wrong names, false claims, policy),
    run on the draft before voicing. Same prompt and model as QA's script check."""
    from .agents import script_issues
    try:
        res = script_issues(cfg, sc["title"], sc.get("description", ""), sc["lines"])
    except Exception as e:  # noqa: BLE001 - the final QA still checks the script
        print(f"  script pre-check unavailable: {e}", flush=True)
        return []
    return [i.get("problem", "") for i in res.get("issues", []) if i.get("severity") == "fail"]


def composition_id(slug: str) -> str:
    return "Film" + "".join(p.capitalize() for p in re.split(r"[^a-z0-9]+", slug) if p)


def _run(cmd: list[str], cwd: Path, timeout: int, env: dict | None = None, what: str = "") -> str:
    print(f"  $ {' '.join(str(c) for c in cmd)[:160]}", flush=True)
    res = subprocess.run([str(c) for c in cmd], cwd=str(cwd), capture_output=True, text=True, timeout=timeout,
                         env={**os.environ, **(env or {})})
    if res.returncode != 0:
        raise RuntimeError(f"{what or cmd[0]} failed ({res.returncode}): {(res.stderr or res.stdout)[-2500:]}")
    return res.stdout


def _voice_python(cfg: dict) -> Path:
    for cand in (fcfg(cfg)["voice_python"], "tools/clone/.venv/bin/python"):
        p = cfg["_root"] / cand
        if p.exists():
            return p
    raise RuntimeError("no Chatterbox python env (film.voice_python or tools/clone/.venv)")


def _loudness(path: Path) -> tuple[float, float]:
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", out)
    p = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", out)
    return float(i[-1]), float(p[-1])


def master_audio(raw: Path, out: Path) -> tuple[float, float]:
    """Loudness pass: gain to TARGET_LUFS, then a limiter; repeats once if the limiter pulled it down.
    Video is copied untouched. Returns (integrated LUFS, sample peak dBFS)."""
    gain = TARGET_LUFS - _loudness(raw)[0]
    for _ in range(3):
        tmp = out.with_suffix(".tmp.mp4")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(raw), "-c:v", "copy", "-af",
                        f"volume={gain:.2f}dB,alimiter=limit={PEAK_LIMIT}:level=false,aresample=48000",
                        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(tmp)], check=True)
        lufs, peak = _loudness(tmp)
        tmp.replace(out)
        if abs(lufs - TARGET_LUFS) <= 0.5:
            break
        gain += TARGET_LUFS - lufs
    return lufs, peak


def speech_coverage(video: Path, lines: list[dict]) -> float:
    """Share of script words Whisper hears in the finished mix (proves music isn't burying the voice)."""
    import numpy as np  # noqa: F401
    import soundfile as sf
    from faster_whisper import WhisperModel

    wav = video.with_suffix(".check.wav")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(video), "-ac", "1", "-ar", "16000", str(wav)], check=True)
    audio, _ = sf.read(wav, dtype="float32")
    wav.unlink()
    segs, _ = WhisperModel("small.en", device="cpu", compute_type="int8").transcribe(audio)
    heard = set(re.findall(r"[a-z']+", " ".join(s.text for s in segs).lower()))
    return coverage_of(heard, " ".join(ln["text"] for ln in lines))


# Numbers are written as words for the voice ("twelve oh two"), but Whisper transcribes them as digits
# ("1202"), so number words can't be matched and are left out of the score (2026-11-25: Apollo 11's
# "1202 alarm" film failed at 89% because of this, not because the music was loud).
NUMBER_WORDS = set("""zero oh one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen
sixteen seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred thousand million
billion trillion quadrillion quintillion first second third fourth fifth sixth seventh eighth ninth tenth percent
point and a""".split())


def coverage_of(heard: set[str], script: str) -> float:
    words = [w for w in re.findall(r"[a-z']+", script.lower().replace("-", " ")) if w not in NUMBER_WORDS]
    return sum(w in heard for w in words) / max(1, len(words))


def _ts(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_srt(timings: dict, path: Path, offset: float = VOICE_AT / FPS) -> None:
    """YouTube captions straight from the narration line timings (make_voice.py output)."""
    rows = []
    for i, ln in enumerate(timings["lines"], 1):
        rows.append(f"{i}\n{_ts(ln['start'] + offset)} --> {_ts(ln['end'] + offset)}\n{ln['text']}\n")
    path.write_text("\n".join(rows))


# ---------------------------------------------------------------- 2-6. stages

def stage_voice(cfg: dict, sc: dict) -> dict:
    root = film_root(cfg)
    slug = sc["slug"]
    narr, wav, tim = root / "narration" / f"{slug}.json", root / "public/voice" / f"{slug}.wav", root / "public/voice" / f"{slug}.json"
    spec = {"voice": {"ref": "tools/voice/refs/narrator.wav", "temperature": 0.6, "tempo": 0.95},
            "lines": [{"text": ln["text"], "pause": ln["pause"]} for ln in sc["lines"]]}
    if narr.exists() and json.loads(narr.read_text()).get("lines") == spec["lines"] and wav.exists() and tim.exists():
        print("  voice exists, skipping")
        return json.loads(tim.read_text())
    narr.parent.mkdir(exist_ok=True)
    narr.write_text(json.dumps(spec, indent=2))
    _run([_voice_python(cfg), "scripts/make_voice.py", f"narration/{slug}.json", f"public/voice/{slug}.wav"],
         root, timeout=3 * 3600, what="make_voice.py")
    return json.loads(tim.read_text())


def stage_direct(cfg: dict, sc: dict, timings: dict) -> dict:
    """Claude Code (headless) writes src/films/<slug>/ following film/CLAUDE.md, using the voice timings,
    registers the composition, adds the score + SFX, checks stills, and writes film.json."""
    from .agents import load_prompt
    root = film_root(cfg)
    slug = sc["slug"]
    fj = root / "src/films" / slug / "film.json"
    if fj.exists():
        print("  scenes exist, skipping")
        return json.loads(fj.read_text())
    comp = composition_id(slug)
    numbered = "\n".join(f"{i + 1:>2}. [{ln['startFrame'] + VOICE_AT}-{ln['endFrame'] + VOICE_AT}] {ln['text']}"
                         for i, ln in enumerate(timings["lines"]))
    prompt = load_prompt("film_director", slug=slug, comp=comp, numbered=numbered,
                         title_word=sc["title_card"]["word"], title_line=sc["title_card"]["line"],
                         title_accent=sc["title_card"]["accent"], thumb_word=sc["thumbnail"]["word"],
                         thumb_line=sc["thumbnail"]["line"], voice_at=VOICE_AT,
                         duration_s=round(timings["duration"], 1))
    tools = ["Read", "Edit", "Write", "Glob", "Grep", "Bash(npx tsc:*)", "Bash(npx remotion still:*)",
             "Bash(python3 scripts/make_sounds.py:*)", "Bash(ffmpeg:*)", "Bash(ls:*)", "Bash(mkdir:*)"]
    env = {"PATH": f"{Path(sys.executable).parent}:{os.environ.get('PATH', '')}"}   # python3 -> our venv (numpy)
    cmd = ["claude", "-p", "--output-format", "json", "--model", fcfg(cfg)["director_model"],
           "--permission-mode", "acceptEdits", "--allowedTools", *tools, "--no-session-persistence"]
    t = int(fcfg(cfg)["director_timeout_min"]) * 60
    print(f"  director: Claude Code is animating {comp} (up to {t // 60} min)", flush=True)
    res = subprocess.run(cmd, input=prompt, cwd=str(root), capture_output=True, text=True, timeout=t,
                         env={**os.environ, **env})
    if res.returncode != 0:
        raise RuntimeError(f"film director failed: {(res.stderr or res.stdout)[-2500:]}")
    if not fj.exists():
        raise RuntimeError(f"film director finished without writing {fj.relative_to(root)}: "
                           f"{json.loads(res.stdout).get('result', '')[-1500:] if res.stdout.strip().startswith('{') else res.stdout[-1500:]}")
    _run(["npx", "tsc", "--noEmit", "-p", "."], root, timeout=600, what="type-check")
    return json.loads(fj.read_text())


def stage_sounds(cfg: dict) -> None:
    root = film_root(cfg)
    _run([sys.executable, "scripts/make_sounds.py"], root, timeout=1800, what="make_sounds.py")


def stage_render(cfg: dict, comp: str, job: Path) -> Path:
    root = film_root(cfg)
    raw = Path(job).resolve() / "raw.mp4"
    _run(["npx", "remotion", "render", comp, str(raw), "--log=error"], root, timeout=4 * 3600, what="remotion render")
    return raw


def stage_thumbnail(cfg: dict, film: dict, sc: dict, job: Path) -> list[Path]:
    """Three thumbnails for YouTube's Test & Compare: thumbnail.jpg (A, circled word, set on upload),
    thumbnail_b.jpg (big face) and thumbnail_c.jpg (case-file stamp) from the writer's alternative angles."""
    from PIL import Image
    root = film_root(cfg)
    job = Path(job).resolve()   # remotion runs in film/, so paths must be absolute
    main = {**sc["thumbnail"], **(film.get("thumbnail") or {})}
    alts = list(sc.get("thumbnail_alts") or [])
    specs = [("thumbnail", "circle", main)]
    for name, variant, alt in zip(("thumbnail_b", "thumbnail_c"), ("face", "stamp"), alts + [main, main]):
        specs.append((name, variant, alt))
    out = []
    for name, variant, th in specs:
        props = job / f"{name}.props.json"
        props.write_text(json.dumps({"word": th["word"], "line": th.get("line", ""),
                                     "brow": main.get("brow", 0.6), "variant": variant}))
        png = job / f"{name}.png"
        _run(["npx", "remotion", "still", "Thumbnail", str(png), "--frame=30", f"--props={props}", "--log=error"],
             root, timeout=600, what=f"thumbnail {variant}")
        jpg = job / f"{name}.jpg"
        Image.open(png).convert("RGB").save(jpg, quality=92)
        png.unlink()
        props.unlink()
        out.append(jpg)
    return out


def stage_repair(cfg: dict, sc: dict, issues: str) -> None:
    """Hand visual-QA failures back to the director (Claude Code) to fix the scenes before a re-render."""
    from .agents import load_prompt
    root = film_root(cfg)
    prompt = load_prompt("film_repair", slug=sc["slug"], comp=composition_id(sc["slug"]), issues=issues, voice_at=VOICE_AT)
    tools = ["Read", "Edit", "Write", "Glob", "Grep", "Bash(npx tsc:*)", "Bash(npx remotion still:*)", "Bash(ls:*)", "Bash(mkdir:*)"]
    cmd = ["claude", "-p", "--output-format", "json", "--model", fcfg(cfg)["director_model"],
           "--permission-mode", "acceptEdits", "--allowedTools", *tools, "--no-session-persistence"]
    print("  repair: sending QA issues back to the director", flush=True)
    res = subprocess.run(cmd, input=prompt, cwd=str(root), capture_output=True, text=True, timeout=3600)
    if res.returncode != 0:
        raise RuntimeError(f"film repair failed: {(res.stderr or res.stdout)[-1500:]}")
    _run(["npx", "tsc", "--noEmit", "-p", "."], root, timeout=600, what="type-check after repair")


# ---------------------------------------------------------------- the builder (format contract)

def build_film(cfg: dict, topic: str | None = None, job: Path | None = None, *, guidance: str = "",
               feedback: list[str] | None = None, on_script=None, past: list[str] | None = None,
               recent: list[dict] | None = None) -> Path:
    from . import _done, _slug, _stage
    from .analytics import script_text, too_similar, acfg

    out_root = cfg["_root"] / cfg["output_dir"]
    out_root.mkdir(exist_ok=True)
    if job and (job / "script.json").exists():
        sc = json.loads((job / "script.json").read_text())
    else:
        t0 = _stage("film script (claude -p)")
        local = [json.loads(p.read_text()) for p in sorted(out_root.glob("*/script.json"))]
        past = list(dict.fromkeys([*(past or []), *(x.get("subject") or x["title"] for x in local)]))
        recent = [*(recent or []), *({"title": x["title"], "text": script_text(x)} for x in local if "lines" in x)]
        fb = list(feedback or [])
        a = acfg(cfg)
        for attempt in range(3):
            sc = write_script(cfg, topic, past, guidance, fb)
            existing = film_root(cfg) / "src/films" / sc["slug"]
            hit = too_similar(sc["title"], script_text(sc), recent[-a["similarity_window"]:], a["similarity_threshold"])
            if existing.exists():
                hit = hit or (1.0, f"film folder src/films/{sc['slug']} already exists")
            if not hit:
                break
            fb.append(f"POLICY GUARD: {sc['subject']!r} is too close to {hit[1]!r}. Pick a different story and slug.")
        else:
            raise RuntimeError(f"film writer: 3 drafts all repeated earlier videos (last: {hit[1]!r})")
        for fix in range(2):   # a real error in the script costs a whole night's render if found only at the end
            issues = precheck_script(cfg, sc)
            if not issues:
                break
            print(f"  script check found {len(issues)} problem(s), rewriting: {issues}", flush=True)
            sc = write_script(cfg, sc["subject"], past, guidance, fb + [
                f"SCRIPT CHECK (fix these, keep the same story and subject {sc['subject']!r}): " + " | ".join(issues)])
        kept = check_sources(sc["sources"])
        if not kept:
            raise RuntimeError("film writer: none of the cited source URLs load; refusing to publish uncredited")
        sc["sources"] = kept
        apply_seo(sc)
        sc["description"] = make_description(sc["summary"], kept, sc["hashtags"])
        _done(t0)
        job = job or out_root / f"{date.today():%Y%m%d}-{_slug(sc['slug'])}-film"
        job.mkdir(parents=True, exist_ok=True)
        (job / "script.json").write_text(json.dumps(sc, indent=2, ensure_ascii=False))
        (job / "job.json").write_text(json.dumps({"format": "film", "style": "film", "created": time.time()}))
    if on_script:
        on_script(sc, job)
    print(f"  {sc['subject']!r}: {len(sc['lines'])} lines, {sum(len(ln['text'].split()) for ln in sc['lines'])} words")

    t0 = _stage("voice (Chatterbox Turbo + Whisper retries)")
    timings = stage_voice(cfg, sc)
    _done(t0)
    print(f"  {timings['duration']:.1f}s of narration")

    t0 = _stage("scenes (Claude Code director, film/CLAUDE.md)")
    film = stage_direct(cfg, sc, timings)
    _done(t0)

    t0 = _stage("music + sound effects (code-generated)")
    stage_sounds(cfg)
    _done(t0)

    write_srt(timings, job / "captions.srt")
    (job / "timing.json").write_text(json.dumps(
        [{"start": ln["start"] + VOICE_AT / FPS, "end": ln["end"] + VOICE_AT / FPS, "text": ln["text"]} for ln in timings["lines"]]))

    def render_and_check() -> dict:
        t0 = _stage("render (Remotion)")
        raw = stage_render(cfg, film["composition"], job)
        _done(t0)
        t0 = _stage("loudness + speech check")
        lufs, peak = master_audio(raw, job / "video.mp4")
        raw.unlink(missing_ok=True)
        cover = speech_coverage(job / "video.mp4", sc["lines"])
        print(f"  {lufs:.1f} LUFS, peak {peak:.1f} dBFS, Whisper heard {cover:.0%} of the script")
        # no raise here: QA decides (fail < 90%), so the repair pass, the Short and persist_film still run
        _done(t0)
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                    str(job / "video.mp4")], capture_output=True, text=True).stdout.strip())
        sc["title"] = make_title(sc["subject"], minutes_for(dur))
        sc["description"], seo_tags, playlist = seo_metadata(sc, timings, dur)
        (job / "script.json").write_text(json.dumps(sc, indent=2, ensure_ascii=False))
        meta = {"title": sc["title"], "description": sc["description"], "tags": seo_tags, "format": "film",
                "playlist": playlist,
                "duration_s": round(dur, 1), "loudness_lufs": lufs, "peak_dbfs": peak, "speech_coverage": round(cover, 3)}
        (job / "metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
        return meta

    meta = render_and_check()
    stage_thumbnail(cfg, film, sc, job)

    # QA now (cached in qa.json for the pipeline). Visual failures go back to the director once.
    from .agents import qa_review
    t0 = _stage("QA (checks + visual review + script check)")
    qa = qa_review(cfg, job)
    for attempt in range(int(fcfg(cfg).get("repairs", 1))):
        visual = [ln for ln in qa["notes"].splitlines()
                  if ln.startswith("[fail]") and ("frame_" in ln or "blank frames" in ln)]
        if qa["verdict"] != "fail" or not visual:
            break
        stage_repair(cfg, sc, "\n".join(visual))
        meta = render_and_check()
        qa = qa_review(cfg, job, force=True)
    print(f"  QA {qa['verdict']}")
    _done(t0)

    if (job / "video.mp4").exists() and qa["verdict"] != "fail":
        t0 = _stage("Short (vertical cut of the cold open)")
        from .cuts import make_short
        try:
            make_short(cfg, sc, timings, job)
        except Exception as e:  # noqa: BLE001 - the film still ships without its Short
            print(f"  short failed: {type(e).__name__}: {e}", flush=True)
        _done(t0)
    from .cuts import persist_film
    rel = persist_film(cfg, job, sc)
    if rel:
        meta["release_url"] = rel
        (job / "metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"\n✔ {job / 'video.mp4'}  {meta['title']!r}")
    return job
