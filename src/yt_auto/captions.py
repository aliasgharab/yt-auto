"""Stage 7: word-timed captions via faster-whisper alignment -> ASS (burned) + SRT (uploaded)."""

from pathlib import Path

_model = None


def word_timings(wav: Path, script_text: str) -> list[tuple[float, float, str]]:
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel("small.en", device="cpu", compute_type="int8")
    import numpy as np
    import soundfile as sf
    audio, sr = sf.read(wav, dtype="float32")
    n16 = int(len(audio) * 16000 / sr)  # whisper wants 16 kHz mono
    audio = np.interp(np.linspace(0, len(audio) - 1, n16), np.arange(len(audio)), audio).astype(np.float32)
    segs, _ = _model.transcribe(audio, word_timestamps=True, beam_size=5,
                                initial_prompt=script_text[:800], vad_filter=False)
    return [(w.start, w.end, w.word.strip()) for s in segs for w in s.words if w.word.strip()]


def _load_16k(wav: Path):
    import numpy as np
    import soundfile as sf
    audio, sr = sf.read(wav, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    n16 = int(len(audio) * 16000 / sr)
    return np.interp(np.linspace(0, len(audio) - 1, n16), np.arange(len(audio)), audio).astype(np.float32)


def line_word_timings(wav: Path, lines: list[dict]) -> list[tuple[float, float, str]]:
    """Per-line alignment: each line's start/end is already known exactly (we synthesise lines one by one),
    so whisper only has to place words inside a short window. The words shown are always the SCRIPT's
    words, so a whisper miss can never drop or garble a caption -- worst case they're spread evenly.
    lines: [{"text", "start", "end"}] in seconds on the narration.wav timeline."""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel("small.en", device="cpu", compute_type="int8")
    audio = _load_16k(wav)
    out = []
    for ln in lines:
        words = ln["text"].split()
        if not words:
            continue
        a, b = ln["start"], ln["end"]
        seg = audio[int(a * 16000): int(b * 16000)]
        ww = []
        if len(seg) > 1600:
            segs, _ = _model.transcribe(seg, word_timestamps=True, beam_size=5, language="en",
                                        initial_prompt=ln["text"], vad_filter=False,
                                        condition_on_previous_text=False)
            ww = [(w.start, w.end) for sg in segs for w in sg.words if w.word.strip()]
        if len(ww) == len(words):
            times = [(a + s0, a + e0) for s0, e0 in ww]
        else:
            # spread script words over the detected speech span, weighted by length
            s0 = a + (ww[0][0] if ww else 0.0)
            e0 = a + (ww[-1][1] if ww else b - a)
            if e0 - s0 < 0.2 * len(words):
                s0, e0 = a, b
            wts = [len(w) + 2 for w in words]
            tot, t = sum(wts), s0
            times = []
            for w in wts:
                d = (e0 - s0) * w / tot
                times.append((t, t + d))
                t += d
        prev = a
        for (s1, e1), w in zip(times, words):
            s1 = min(max(s1, prev, a), b)
            e1 = min(max(e1, s1 + 0.05), b)
            out.append((s1, e1, w))
            prev = s1
    return out


def _chunks(words, max_words=3, max_chars=16):
    cur = []
    for w in words:
        if cur and (len(cur) >= max_words or len(" ".join(x[2] for x in cur + [w])) > max_chars
                    or cur[-1][2][-1:] in ".?!,:;"):
            yield cur
            cur = []
        cur.append(w)
    if cur:
        yield cur


def _ts_ass(t):
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _ts_srt(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_ass(words, size, out: Path, font="Inter ExtraBold", fs=None, margin_v=None, single=False):
    """single=True: one word at a time, big and yellow (story format); default: 3-word chunks with the
    spoken word highlighted."""
    W, H = size
    vertical = H > W
    fs = fs or (92 if vertical else 58)
    margin_v = margin_v if margin_v is not None else (int(H * 0.17) if vertical else 70)
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{font},{fs},&H00CFE1E6,&H00FFFFFF,&H00140E0B,&H96000000,-1,0,0,0,100,100,0,0,1,{7 if vertical else 4},2,2,60,60,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    if single:   # yellow fill (&HBBGGRR), thick black outline, pop-in scale
        head = head.replace("&H00CFE1E6,&H00FFFFFF,&H00140E0B", "&H0035E1FF,&H00FFFFFF,&H00000000")
    lines = []
    chunks = list(_chunks(words, max_words=1) if single else _chunks(words))
    for ci, ch in enumerate(chunks):
        next_start = chunks[ci + 1][0][0] if ci + 1 < len(chunks) else 1e9
        for i, (s, e, _) in enumerate(ch):
            end = ch[i + 1][0] if i + 1 < len(ch) else min(e + 0.15, next_start)
            if single:
                txt = r"{\fscx80\fscy80\t(0,80,\fscx100\fscy100)}" + ch[0][2].lower()
            else:
                txt = " ".join((r"{\c&H50B4E6&}" + w.upper() + r"{\c&HCFE1E6&}") if j == i else w.upper()
                               for j, (_, _, w) in enumerate(ch))
            lines.append(f"Dialogue: 0,{_ts_ass(s)},{_ts_ass(end)},Cap,,0,0,0,,{txt}")
    out.write_text(head + "\n".join(lines) + "\n")


def write_srt(words, out: Path):
    blocks = []
    for n, ch in enumerate(_chunks(words, max_words=8, max_chars=42), 1):
        blocks.append(f"{n}\n{_ts_srt(ch[0][0])} --> {_ts_srt(ch[-1][1])}\n{' '.join(w for _, _, w in ch)}\n")
    out.write_text("\n".join(blocks))
