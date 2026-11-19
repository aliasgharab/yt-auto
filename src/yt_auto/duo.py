"""Shorts format: two characters talk over gameplay, with colourful animated pop-up cards.

script (claude -p) -> per-line character voices (Chatterbox clone, or Kokoro + RVC; sped up) -> animated cards ->
word captions (whisper) -> ffmpeg composite over a random gameplay segment.
"""

import json
import random
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

from . import captions, cards, script, tts
from .assemble import _encoder_args

SR = tts.SR
GAP = 0.08          # silence between lines (before tempo): snappy pacing
CARD_Y = 150


# ----------------------------------------------------------------------------- script
POPUP_SCHEMA = {
    "type": "object", "required": ["type"],
    "properties": {
        "type": {"enum": list(cards.RENDER)},
        "emoji": {"type": "string"}, "text": {"type": "string"}, "label": {"type": "string"},
        "value": {"type": "number"}, "language": {"type": "string"}, "code": {"type": "string"},
        "steps": {"type": "array", "items": {"type": "object", "properties": {
            "emoji": {"type": "string"}, "label": {"type": "string"}}}},
        "items": {"type": "array", "items": {"type": "object", "properties": {
            "emoji": {"type": "string"}, "label": {"type": "string"}}}},
        "left": {"type": "object", "properties": {"emoji": {"type": "string"}, "label": {"type": "string"}}},
        "right": {"type": "object", "properties": {"emoji": {"type": "string"}, "label": {"type": "string"}}},
    },
}


def _schema(names):
    return {
        "type": "object",
        "required": ["topic", "title", "description", "tags", "lines"],
        "properties": {
            "topic": {"type": "string"},
            "title": {"type": "string", "maxLength": 90},
            "description": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
            "lines": {"type": "array", "items": {
                "type": "object", "required": ["speaker", "text"],
                "properties": {"speaker": {"enum": names}, "text": {"type": "string"}, "popup": POPUP_SCHEMA}}},
        },
    }


def write_script(cfg: dict, topic: str | None, past_titles: list[str]) -> dict:
    duo, f = cfg["duo"], cfg["formats"]["short"]
    A, B = duo["asker"], duo["explainer"]
    ca, cb = duo["characters"][A], duo["characters"][B]
    lo_w, hi_w = f["target_words"]
    lo_l, hi_l = f["lines"]
    topic_line = (f"TOPIC: {topic}" if topic else
                  "TOPIC: pick ONE specific embedded-systems or operating-system idea from this niche and "
                  f"frame it as an everyday question: {cfg['channel']['niche']}\n"
                  "Not one of these already-made videos:\n" + "\n".join(f"- {t}" for t in past_titles[-60:]))
    prompt = f"""Write a funny, super easy-to-follow YouTube Short script: a conversation between two characters
explaining one embedded-systems / operating-systems idea.

CHARACTERS
- {A}: {ca['personality']}. Asks the question, reacts, pushes back.
- {B}: {cb['personality']}. Answers. Explains with one everyday analogy.

{topic_line}

STRUCTURE (like a meme Short)
1. {A} asks the question as a hook, starting with "{B}, ..." This question is also the video title.
2. {B} gives a short, blunt or absurdly literal answer.
3. {A} reacts ("Wait, what?", "That can't be right") so {B} explains.
4. {B} explains the real idea in the SIMPLEST way, using one everyday analogy.
5. End on a quick punchline from {B} (deadpan, literal humor) that loops nicely back to the start.

RULES
- {lo_w}-{hi_w} words TOTAL, {lo_l}-{hi_l} lines. Each line <= 16 words.
- ONE idea only. A 12-year-old must fully understand it. No jargon; if a tech word is unavoidable,
  explain it in five words or less. Prefer short words and short sentences.
- 100% technically correct, even though simple. Every answer must logically match the line before it.
- Written for text-to-speech: no emoji in spoken text, no parentheses, no symbols; numbers as words.
- Give a "popup" card to most lines (at least 5). The first line's popup is a "title" card.
  Cards should SHOW the idea with pictures: choose emojis that literally depict the analogy.
- Title: the question, <= 60 chars. Description: one sentence + 3 hashtags including #shorts. 8-12 tags.

{cards.POPUP_GUIDE}"""
    schema = _schema([A, B])
    sc = script._call_claude(prompt, cfg, schema)
    check = f"""You are a strict editor for a kids-friendly tech Short. Review this script JSON.
Fix: any technical inaccuracy; any answer that does not logically match the line before it
(e.g. replying "Right" to a question whose true answer is no); anything a 12-year-old would not understand;
jargon; lines over 16 words; total over {hi_w} words; card labels over 3 words; emojis that don't
clearly picture the idea; awkward phrasing for text-to-speech.
Keep it funny, keep the characters' voices, keep the structure. Return the full corrected JSON.

{json.dumps(sc, indent=1, ensure_ascii=False)}"""
    return script._call_claude(check, cfg, schema)


# ----------------------------------------------------------------------------- audio
def _ff_af(audio: np.ndarray, sr_in: int, af: str) -> np.ndarray:
    with tempfile.TemporaryDirectory() as td:
        a, b = Path(td) / "a.wav", Path(td) / "b.wav"
        sf.write(a, audio, sr_in)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(a), "-af", af, "-ar", str(SR),
                        "-ac", "1", str(b)], check=True)
        out, _ = sf.read(b, dtype="float32")
    return out


def _clone_lines(sc, cfg, job: Path) -> list[np.ndarray]:
    root = cfg["_root"]
    chars = cfg["duo"]["characters"]
    vdir = job / "voice"
    vdir.mkdir(exist_ok=True)
    jobs, outs = [], []
    for i, ln in enumerate(sc["lines"]):
        c = chars[ln["speaker"]]
        out = vdir / f"line_{i:02d}.wav"
        outs.append(out)
        if not out.exists():  # cached: cloning is the slow step
            jobs.append({"text": ln["text"], "ref": str(root / c["ref"]), "out": str(out),
                         "exaggeration": c.get("exaggeration", 0.5), "cfg_weight": c.get("cfg_weight", 0.5)})
    if jobs:
        jf = vdir / "jobs.json"
        jf.write_text(json.dumps(jobs))
        py = root / "tools/clone/.venv/bin/python"
        subprocess.run([str(py), str(root / "tools/clone/clone_tts.py"), str(jf)], check=True)
    res = []
    for o in outs:
        a, sr = sf.read(o, dtype="float32")
        res.append((a, sr))
    return res


def _rvc_ready(cfg) -> bool:
    """True if every character has an existing rvc_model (else the rvc backend falls back to clone)."""
    root = cfg["_root"]
    missing = [n for n, c in cfg["duo"]["characters"].items()
               if not c.get("rvc_model") or not (root / c["rvc_model"]).exists()]
    if missing:
        print(f"[duo] rvc model missing for {', '.join(missing)}: falling back to clone voices")
    return not missing


def _rvc_lines(sc, cfg, job: Path) -> list[tuple[np.ndarray, int]]:
    """Kokoro speaks each line (fast), then one Applio subprocess converts them all to the character voices."""
    root = cfg["_root"]
    chars = cfg["duo"]["characters"]
    vdir = job / "voice"
    vdir.mkdir(exist_ok=True)
    k = tts._kokoro_for(cfg)
    jobs, outs = [], []
    for i, ln in enumerate(sc["lines"]):
        c = chars[ln["speaker"]]
        out = vdir / f"rvc_{i:02d}.wav"
        outs.append(out)
        if out.exists():
            continue
        src = vdir / f"kokoro_{i:02d}.wav"
        a, sr = k.create(ln["text"], voice=c["voice"], speed=c["speed"], lang="en-us")
        sf.write(src, a.astype(np.float32), sr)
        jobs.append({"in": str(src), "out": str(out), "model": str(root / c["rvc_model"]),
                     "index": str(root / c["rvc_index"]) if c.get("rvc_index") else "",
                     "pitch": c.get("rvc_pitch", 0), "index_rate": c.get("rvc_index_rate", 0.5),
                     "protect": c.get("rvc_protect", 0.33)})
    if jobs:
        jf = vdir / "rvc_jobs.json"
        jf.write_text(json.dumps(jobs))
        py = root / "tools/rvc/Applio/.venv/bin/python"
        subprocess.run([str(py), str(root / "tools/rvc/rvc_convert.py"), str(jf)], check=True)
    return [sf.read(o, dtype="float32") for o in outs]


def voice_lines(sc: dict, cfg: dict, job: Path) -> list[dict]:
    """Voices each line, applies tempo, writes job/narration.wav (voices) + job/mix.wav (+ swooshes).
    Returns timing [{speaker, start, end, popup}] in final (sped-up) seconds."""
    duo = cfg["duo"]
    chars = duo["characters"]
    tempo = duo.get("tempo", 1.0)
    backend = duo.get("voice_backend")
    if backend == "rvc" and not _rvc_ready(cfg):
        backend = "clone"
    if backend in ("clone", "rvc"):
        raw = (_rvc_lines if backend == "rvc" else _clone_lines)(sc, cfg, job)
        lines = [_ff_af(a, sr, f"silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
                               f"silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
                               f"atempo={tempo}") for a, sr in raw]
    else:
        k = tts._kokoro_for(cfg)
        lines = []
        for ln in sc["lines"]:
            c = chars[ln["speaker"]]
            a, _ = k.create(ln["text"], voice=c["voice"], speed=c["speed"], lang="en-us")
            lines.append(_ff_af(a.astype(np.float32), SR,
                                f"rubberband=pitch={c.get('pitch', 1)}:formant=preserved,atempo={tempo}"))
    gap = np.zeros(int(SR * GAP), dtype=np.float32)
    pieces, timing, t = [], [], 0.0
    for ln, a in zip(sc["lines"], lines):
        a = 0.9 * a / (np.abs(a).max() + 1e-6)
        timing.append({"speaker": ln["speaker"], "start": t, "end": t + len(a) / SR, "popup": ln.get("popup")})
        pieces += [a, gap]
        t += (len(a) + len(gap)) / SR
    voice = np.concatenate(pieces).astype(np.float32)
    sf.write(job / "narration.wav", voice, SR)
    mix = voice.copy()
    sw = _swoosh()
    for tm in timing:
        if tm["popup"]:
            i = max(0, int((tm["start"] - 0.1) * SR))
            mix[i:i + len(sw)] += sw[:len(mix) - i]
    sf.write(job / "mix.wav", np.clip(mix, -1, 1), SR)
    return timing


def _swoosh() -> np.ndarray:
    n = int(SR * 0.3)
    rng = np.random.default_rng(7)
    noise = rng.standard_normal(n).astype(np.float32)
    out = np.zeros(n, dtype=np.float32)
    for i, k in enumerate(np.linspace(24, 3, 8).astype(int)):
        seg = slice(i * n // 8, (i + 1) * n // 8)
        out[seg] = np.convolve(noise, np.ones(k) / k, mode="same")[seg]
    env = np.sin(np.linspace(0, np.pi, n)) ** 2
    return 0.3 * out * env / (np.abs(out).max() + 1e-6)


# ----------------------------------------------------------------------------- video
def _pick_gameplay(root: Path, total: float):
    clips = sorted((root / "assets" / "gameplay").glob("*.mp4"))
    if not clips:
        raise FileNotFoundError("no gameplay clips in assets/gameplay/")
    clip = random.choice(clips)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                "csv=p=0", str(clip)], capture_output=True, text=True).stdout)
    return clip, random.uniform(5, max(5, dur - total - 5))


def composite(timing, cfg, job: Path, ass: Path):
    root = cfg["_root"]
    W, H = cfg["formats"]["short"]["size"]
    fps = cfg["render"]["fps"]
    chars = cfg["duo"]["characters"]
    total = timing[-1]["end"] + 0.5
    clip, off = _pick_gameplay(root, total)
    (job / "gameplay.txt").write_text(f"{clip.name} @ {off:.1f}s\n")

    inputs = ["-ss", f"{off:.2f}", "-t", f"{total:.2f}", "-an", "-i", str(clip)]
    filters = [f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={fps},setsar=1[v0]"]
    idx, cur = 1, "v0"

    # both characters always on screen in their corner; the speaker bobs, the listener is dimmed
    for name, c in chars.items():
        spans = [(tm["start"], tm["end"] + GAP) for tm in timing if tm["speaker"] == name]
        talking = "+".join(f"between(t,{a:.2f},{b:.2f})" for a, b in spans) or "0"
        inputs += ["-loop", "1", "-framerate", str(fps), "-t", f"{total:.2f}", "-i", str(root / c["image"])]
        h = c.get("height", 560)
        filters.append(f"[{idx}:v]scale=-1:{h},format=rgba,split[ca{idx}][ci{idx}]")
        filters.append(f"[ci{idx}]colorchannelmixer=rr=0.6:gg=0.6:bb=0.6[cd{idx}]")
        x = "-20" if c["side"] == "left" else "main_w-overlay_w+20"
        filters.append(f"[{cur}][cd{idx}]overlay=x={x}:y=main_h-overlay_h+30:enable='not({talking})'[vi{idx}]")
        filters.append(f"[vi{idx}][ca{idx}]overlay=x={x}:y='main_h-overlay_h+30-16*abs(sin(t*9))':"
                       f"enable='{talking}'[v{idx}]")
        cur, idx = f"v{idx}", idx + 1

    # animated cards: from their line's start until the next card (or the end)
    pops = [(i, tm) for i, tm in enumerate(timing) if tm["popup"]]
    for n, (i, tm) in enumerate(pops):
        start = tm["start"]
        end = pops[n + 1][1]["start"] if n + 1 < len(pops) else total
        pattern = cards.render_card(tm["popup"], end - start, job / "cards" / f"{i:02d}", n)
        inputs += ["-framerate", str(fps), "-i", str(pattern)]
        filters.append(f"[{idx}:v]format=rgba,setpts=PTS-STARTPTS+{start:.3f}/TB[p{idx}]")
        filters.append(f"[{cur}][p{idx}]overlay=x=(main_w-overlay_w)/2:y={CARD_Y}:eof_action=pass:"
                       f"enable='between(t,{start:.2f},{end:.2f})'[v{idx}]")
        cur, idx = f"v{idx}", idx + 1

    esc = str(ass).replace("\\", "\\\\").replace(":", "\\:")
    filters.append(f"[{cur}]ass={esc}:fontsdir={cfg['render']['font_dir']},format=yuv420p[vout]")
    inputs += ["-i", str(job / "mix.wav")]
    filters.append(f"[{idx}:a]apad=pad_dur=0.5,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]")

    cmd = (["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + inputs +
           ["-filter_complex", ";".join(filters), "-map", "[vout]", "-map", "[aout]", "-t", f"{total:.2f}"] +
           _encoder_args(cfg) + ["-c:a", "aac", "-ac", "2", "-b:a", "192k", "-movflags", "+faststart",
                                 str(job / "video.mp4")])
    (job / "ffmpeg_cmd.txt").write_text(" ".join(cmd))
    subprocess.run(cmd, check=True)


def build_audio_and_video(sc: dict, cfg: dict, job: Path):
    timing = voice_lines(sc, cfg, job)
    (job / "timing.json").write_text(json.dumps(timing, indent=1, ensure_ascii=False))
    full = " ".join(ln["text"] for ln in sc["lines"])
    words = captions.word_timings(job / "narration.wav", full)
    captions.write_srt(words, job / "captions.srt")
    W, H = cfg["formats"]["short"]["size"]
    captions.write_ass(words, (W, H), job / "captions.ass", fs=100, margin_v=int(H * 0.37))
    composite(timing, cfg, job, job / "captions.ass")
    return timing
