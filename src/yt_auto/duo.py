"""Shorts format: two characters talk over gameplay, with colourful animated pop-up cards.

script (claude -p) -> per-line cloned character voices (Chatterbox, sped up) -> animated cards ->
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
from .assemble import AUDIO_ARGS, _encoder_args

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


EDIT_CATEGORIES = ["accuracy", "clarity", "hook", "line_length", "popup_fit", "word_count", "voice"]


def _editor_schema(names):
    return {
        "type": "object", "required": ["problems", "script"],
        "properties": {
            "problems": {"type": "array", "items": {
                "type": "object", "required": ["category", "problem", "fix"],
                "properties": {"category": {"enum": EDIT_CATEGORIES},
                               "line": {"type": ["integer", "null"]},
                               "problem": {"type": "string"}, "fix": {"type": "string"}}}},
            "script": _schema(names),
        },
    }


def script_facts(sc: dict, cfg: dict) -> str:
    """Deterministic measurements handed to the editor (models are bad at counting words)."""
    f = cfg["formats"]["short"]
    lo_w, hi_w = f["target_words"]
    lo_l, hi_l = f["lines"]
    lines = sc.get("lines", [])
    counts = [len(ln.get("text", "").split()) for ln in lines]
    total = sum(counts)
    long_ = [f"line {i} ({c} words)" for i, c in enumerate(counts) if c > 16]
    cards_ = [ln["popup"] for ln in lines if ln.get("popup")]
    long_labels = []
    for i, ln in enumerate(lines):
        pu = ln.get("popup") or {}
        labels = [pu.get("label")] + [x.get("label") for k in ("steps", "items") for x in pu.get(k) or []] + \
                 [(pu.get(k) or {}).get("label") for k in ("left", "right")]
        long_labels += [f"line {i}: '{lb}'" for lb in labels if lb and len(lb.split()) > 3]
    return "\n".join([
        f"- total words: {total} (target {lo_w}-{hi_w}){'  <-- OUT OF RANGE' if not lo_w <= total <= hi_w else ''}",
        f"- lines: {len(lines)} (target {lo_l}-{hi_l}){'  <-- OUT OF RANGE' if not lo_l <= len(lines) <= hi_l else ''}",
        f"- lines over 16 words: {', '.join(long_) or 'none'}",
        f"- popup cards: {len(cards_)}; first card type: {(lines[0].get('popup') or {}).get('type') if lines else None}",
        f"- card labels over 3 words: {', '.join(long_labels) or 'none'}",
    ])


def _note(p: dict) -> str:
    where = f" line {p['line']}" if isinstance(p.get("line"), int) else ""
    return f"[{p.get('category', '?')}]{where}: {p.get('problem', '').strip()} -> {p.get('fix', '').strip()}"


def write_script(cfg: dict, topic: str | None, past_titles: list[str], guidance: str = "",
                 feedback: list[str] | None = None) -> dict:
    """Writer pass, then a separate critical-editor pass. Returns the edited script with
    "editor_notes" (the editor's list of problems it found and fixed)."""
    from .agents import load_prompt

    duo, f = cfg["duo"], cfg["formats"]["short"]
    A, B = duo["asker"], duo["explainer"]
    ca, cb = duo["characters"][A], duo["characters"][B]
    lo_w, hi_w = f["target_words"]
    lo_l, hi_l = f["lines"]
    topic_line = (f"TOPIC: {topic}" if topic else
                  "TOPIC: pick ONE specific embedded-systems or operating-system idea from this niche and "
                  f"frame it as an everyday question: {cfg['channel']['niche']}\n"
                  "Not one of these already-made videos:\n" + "\n".join(f"- {t}" for t in past_titles[-60:]))
    guidance_block = (f"\nWHAT WORKS ON THIS CHANNEL (from our analytics; follow it unless it conflicts with "
                      f"the rules above):\n{guidance.strip()}\n" if guidance and guidance.strip() else "")
    fb = [x.strip() for x in (feedback or []) if x and x.strip()][-10:]
    feedback_block = ("\nRECENT HUMAN REVIEWER REJECTIONS (do not repeat these mistakes):\n"
                      + "\n".join(f"- {x}" for x in fb) + "\n" if fb else "")
    common = dict(A=A, B=B, A_personality=ca["personality"], B_personality=cb["personality"],
                  A_lines="; ".join(f'"{x}"' for x in ca.get("famous_lines", [])) or "(none)",
                  B_lines="; ".join(f'"{x}"' for x in cb.get("famous_lines", [])) or "(none)",
                  lo_w=lo_w, hi_w=hi_w, lo_l=lo_l, hi_l=hi_l, popup_guide=cards.POPUP_GUIDE)

    # pass 1: writer
    draft = script._call_claude(
        load_prompt("duo_writer", topic_line=topic_line, guidance_block=guidance_block,
                    feedback_block=feedback_block, **common), cfg, _schema([A, B]))

    # pass 2: editor (separate call, critical persona, must enumerate problems before fixing)
    draft.pop("editor_notes", None)
    edited = script._call_claude(
        load_prompt("duo_editor", facts=script_facts(draft, cfg), draft=json.dumps(draft, indent=1, ensure_ascii=False),
                    guidance_block=(guidance_block + feedback_block).replace("the rules above", "the rules"),
                    **common), cfg, _editor_schema([A, B]))
    sc = edited.get("script") or draft
    sc["editor_notes"] = [_note(p) for p in edited.get("problems", [])]
    return sc


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
        res = subprocess.run([str(py), str(root / "tools/clone/clone_tts.py"), str(jf)],
                             stderr=subprocess.PIPE, text=True)
        if res.stderr:
            print(res.stderr[-3000:], flush=True)
        if res.returncode != 0:   # stderr tail in the message lets heal.is_transient spot HF/network errors
            raise RuntimeError(f"Chatterbox clone failed (rc {res.returncode}): {res.stderr[-1500:]}")
    res = []
    for o in outs:
        a, sr = sf.read(o, dtype="float32")
        res.append((a, sr))
    return res


def voice_lines(sc: dict, cfg: dict, job: Path) -> list[dict]:
    """Voices each line, applies tempo, writes job/narration.wav (voices) + job/mix.wav (+ swooshes).
    Returns timing [{speaker, start, end, popup}] in final (sped-up) seconds."""
    duo = cfg["duo"]
    chars = duo["characters"]
    tempo = duo.get("tempo", 1.0)
    if duo.get("voice_backend") == "clone":
        raw = _clone_lines(sc, cfg, job)
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
    cap = duo.get("max_seconds")
    if cap:   # hard length cap: speed every line up a bit more rather than ship a >30 s Short
        speech = sum(len(a) for a in lines) / SR
        room = cap - GAP * len(lines)
        if speech > room:
            extra = min(speech / room, 1.2)
            print(f"[duo] {speech + GAP * len(lines):.1f}s > {cap}s cap: extra tempo x{extra:.3f}")
            lines = [_ff_af(a, SR, f"atempo={extra:.4f}") for a in lines]
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
           _encoder_args(cfg) + AUDIO_ARGS + ["-movflags", "+faststart",
                                 str(job / "video.mp4")])
    (job / "ffmpeg_cmd.txt").write_text(" ".join(cmd))
    subprocess.run(cmd, check=True)


# Heavy local jobs that must not overlap a render (they fight for CPU/VRAM: both ran ~10x slower).
HEAVY_PATTERNS = ["Applio/core.py train", "rvc/train/train.py"]


def wait_for_heavy_jobs(cfg: dict, poll_s: int = 60) -> None:
    """Block until no voice-model training is running (no-op on CI). Max wait: duo.max_wait_hours."""
    import time
    max_h = cfg.get("duo", {}).get("max_wait_hours", 12)
    t0 = time.time()
    while True:
        busy = [p for p in HEAVY_PATTERNS
                if subprocess.run(["pgrep", "-f", p], capture_output=True).returncode == 0]
        if not busy:
            return
        waited = (time.time() - t0) / 3600
        if waited > max_h:
            raise RuntimeError(f"gave up after {max_h} h waiting for {busy} to finish")
        if int(time.time() - t0) % 600 < poll_s:
            print(f"[duo] waiting for {busy[0]} to finish before rendering ({waited:.1f} h so far)", flush=True)
        time.sleep(poll_s)


def build_audio_and_video(sc: dict, cfg: dict, job: Path):
    wait_for_heavy_jobs(cfg)
    timing = voice_lines(sc, cfg, job)
    (job / "timing.json").write_text(json.dumps(timing, indent=1, ensure_ascii=False))
    words = captions.line_word_timings(
        job / "narration.wav",
        [{"text": ln["text"], "start": t["start"], "end": t["end"]} for ln, t in zip(sc["lines"], timing)])
    captions.write_srt(words, job / "captions.srt")
    W, H = cfg["formats"]["short"]["size"]
    captions.write_ass(words, (W, H), job / "captions.ass", fs=100, margin_v=int(H * 0.37))
    composite(timing, cfg, job, job / "captions.ass")
    return timing
