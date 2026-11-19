"""Shorts format: two characters talk over gameplay, with pop-up cards (code, diagrams, stats).

script (claude -p) -> per-line character voices (Kokoro + rubberband pitch) -> pop-up cards ->
word captions (whisper) -> ffmpeg composite over a random gameplay segment.
"""

import json
import random
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

from . import captions, render, script, tts
from .assemble import _encoder_args

SR = tts.SR
GAP = 0.10          # silence between lines: snappy pacing
CHAR_H = {"Hiro": 760, "Baymax": 700}


# ----------------------------------------------------------------------------- script
def _schema(names):
    visual = script.SCRIPT_SCHEMA["properties"]["scenes"]["items"]["properties"]["visual"]
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
                "properties": {"speaker": {"enum": names}, "text": {"type": "string"}, "popup": visual}}},
        },
    }


def write_script(cfg: dict, topic: str | None, past_titles: list[str]) -> dict:
    duo, f = cfg["duo"], cfg["formats"]["short"]
    A, B = duo["asker"], duo["explainer"]
    ca, cb = duo["characters"][A], duo["characters"][B]
    lo_w, hi_w = f["target_words"]
    lo_l, hi_l = f["lines"]
    topic_line = (f"TOPIC: {topic}" if topic else
                  "TOPIC: pick ONE specific everyday-tech question people are curious about "
                  "(e.g. why phones get slow, how wifi passwords work, what RAM actually does). "
                  "Not one of these already-made videos:\n" + "\n".join(f"- {t}" for t in past_titles[-60:]))
    prompt = f"""Write a funny, super easy-to-follow YouTube Short script: a conversation between two characters
explaining one tech idea.

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
- {lo_w}-{hi_w} words TOTAL, {lo_l}-{hi_l} lines. Each line <= 16 words. It must be 20-35 seconds spoken.
- ONE idea only. A 12-year-old must fully understand it. No jargon; if a tech word is unavoidable,
  explain it in five words or less. Prefer short words and short sentences.
- 100% technically correct, even though simple.
- Written for text-to-speech: no emoji, no parentheses, no symbols; write numbers as words.
- Give a "popup" visual to about half the lines, mostly {B}'s explanation lines, showing the idea.
  The first line's popup is a "title" card with the question in <= 6 words.
  Popup text is tiny: headings <= 4 words, bullets <= 4 words, code <= 6 lines of <= 30 chars,
  flow nodes <= 2 words. Use code only if it makes the idea clearer, not scarier.
- Title: the question, <= 60 chars. Description: one sentence + 3 hashtags including #shorts. 8-12 tags.

{script.VISUAL_GUIDE}"""
    schema = _schema([A, B])
    sc = script._call_claude(prompt, cfg, schema)
    check = f"""You are a strict editor for a kids-friendly tech Short. Review this script JSON.
Fix: any technical inaccuracy; any answer that does not logically match the line before it
(e.g. replying "Right" to a question whose true answer is no); anything a 12-year-old would not understand; jargon; lines over 16 words;
total over {hi_w} words; popup text that is too long; awkward phrasing for text-to-speech.
Keep it funny, keep the characters' voices, keep the structure. Return the full corrected JSON.

{json.dumps(sc, indent=1)}"""
    return script._call_claude(check, cfg, schema)


# ----------------------------------------------------------------------------- audio
def _pitch(audio: np.ndarray, ratio: float) -> np.ndarray:
    if abs(ratio - 1) < 1e-3:
        return audio
    with tempfile.TemporaryDirectory() as td:
        a, b = Path(td) / "a.wav", Path(td) / "b.wav"
        sf.write(a, audio, SR)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(a), "-af",
                        f"rubberband=pitch={ratio}:formant=preserved", str(b)], check=True)
        out, _ = sf.read(b, dtype="float32")
    return out


def _swoosh() -> np.ndarray:
    n = int(SR * 0.32)
    rng = np.random.default_rng(7)
    noise = rng.standard_normal(n).astype(np.float32)
    # crude band-sweep: smooth noise with a shrinking moving-average window -> rising pitch
    out = np.zeros(n, dtype=np.float32)
    for i, k in enumerate(np.linspace(24, 3, 8).astype(int)):
        seg = slice(i * n // 8, (i + 1) * n // 8)
        out[seg] = np.convolve(noise, np.ones(k) / k, mode="same")[seg]
    env = np.sin(np.linspace(0, np.pi, n)) ** 2
    return 0.35 * out * env / (np.abs(out).max() + 1e-6)


def voice_lines(sc: dict, cfg: dict, job: Path) -> list[dict]:
    """Synthesises each line in its character's voice; writes job/narration.wav (voices only) and
    job/mix.wav (voices + swooshes). Returns timing list [{speaker, start, end, popup?}]."""
    chars = cfg["duo"]["characters"]
    pieces, timing, t = [], [], 0.0
    gap = np.zeros(int(SR * GAP), dtype=np.float32)
    for ln in sc["lines"]:
        c = chars[ln["speaker"]]
        k = tts._kokoro_for(cfg)
        a, _ = k.create(ln["text"], voice=c["voice"], speed=c["speed"], lang="en-us")
        a = _pitch(a.astype(np.float32), c.get("pitch", 1.0))
        timing.append({"speaker": ln["speaker"], "start": t, "end": t + len(a) / SR, "popup": ln.get("popup")})
        pieces += [a, gap]
        t += (len(a) + len(gap)) / SR
    voice = np.concatenate(pieces)
    sf.write(job / "narration.wav", voice, SR)
    mix = voice.copy()
    sw = _swoosh()
    for tm in timing:
        if tm["popup"]:
            i = max(0, int((tm["start"] - 0.12) * SR))
            mix[i:i + len(sw)] += sw[:len(mix) - i]
    sf.write(job / "mix.wav", np.clip(mix, -1, 1), SR)
    return timing


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
    total = timing[-1]["end"] + 0.6
    clip, off = _pick_gameplay(root, total)
    (job / "gameplay.txt").write_text(f"{clip.name} @ {off:.1f}s\n")

    inputs = ["-ss", f"{off:.2f}", "-t", f"{total:.2f}", "-an", "-i", str(clip)]
    filters = [f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={fps},setsar=1[v0]"]
    idx, cur = 1, "v0"

    # speaking character: shown while talking, bottom corner, little "talking" bob
    for name, c in chars.items():
        spans = [(tm["start"], tm["end"] + GAP) for tm in timing if tm["speaker"] == name]
        if not spans:
            continue
        inputs += ["-loop", "1", "-framerate", str(fps), "-t", f"{total:.2f}", "-i", str(root / c["image"])]
        h = CHAR_H.get(name, 720)
        filters.append(f"[{idx}:v]scale=-1:{h},format=rgba[c{idx}]")
        x = "-30" if c["side"] == "left" else f"main_w-overlay_w+30"
        en = "+".join(f"between(t,{a:.2f},{b:.2f})" for a, b in spans)
        filters.append(f"[{cur}][c{idx}]overlay=x={x}:y='main_h-overlay_h+40-14*abs(sin(t*9))':"
                       f"enable='{en}'[v{idx}]")
        cur, idx = f"v{idx}", idx + 1

    # pop-up cards: from their line's start until the next pop-up (or the end)
    pops = [(i, tm) for i, tm in enumerate(timing) if tm["popup"]]
    for n, (i, tm) in enumerate(pops):
        png = render.render_popup(tm["popup"], cfg, job / f"popup_{i:02d}.png")
        start = tm["start"]
        end = pops[n + 1][1]["start"] if n + 1 < len(pops) else total
        inputs += ["-loop", "1", "-framerate", str(fps), "-t", f"{end - start:.2f}", "-i", str(png)]
        filters.append(f"[{idx}:v]format=rgba,fade=in:st=0:d=0.12:alpha=1,"
                       f"setpts=PTS-STARTPTS+{start:.3f}/TB[p{idx}]")
        filters.append(f"[{cur}][p{idx}]overlay=x=(main_w-overlay_w)/2:y=170:eof_action=pass:"
                       f"enable='between(t,{start:.2f},{end:.2f})'[v{idx}]")
        cur, idx = f"v{idx}", idx + 1

    esc = str(ass).replace("\\", "\\\\").replace(":", "\\:")
    filters.append(f"[{cur}]ass={esc}:fontsdir={cfg['render']['font_dir']},format=yuv420p[vout]")
    inputs += ["-i", str(job / "mix.wav")]
    filters.append(f"[{idx}:a]apad=pad_dur=0.6,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]")

    cmd = (["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + inputs +
           ["-filter_complex", ";".join(filters), "-map", "[vout]", "-map", "[aout]", "-t", f"{total:.2f}"] +
           _encoder_args(cfg) + ["-c:a", "aac", "-ac", "2", "-b:a", "192k", "-movflags", "+faststart",
                                 str(job / "video.mp4")])
    (job / "ffmpeg_cmd.txt").write_text(" ".join(cmd))
    subprocess.run(cmd, check=True)


def build_audio_and_video(sc: dict, cfg: dict, job: Path):
    timing = voice_lines(sc, cfg, job)
    (job / "timing.json").write_text(json.dumps(timing, indent=1))
    full = " ".join(ln["text"] for ln in sc["lines"])
    words = captions.word_timings(job / "narration.wav", full)
    captions.write_srt(words, job / "captions.srt")
    W, H = cfg["formats"]["short"]["size"]
    captions.write_ass(words, (W, H), job / "captions.ass", fs=104, margin_v=int(H * 0.40))
    composite(timing, cfg, job, job / "captions.ass")
    return timing
