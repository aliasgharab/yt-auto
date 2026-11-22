"""Narration generator: Chatterbox Turbo (MIT licence, free, runs locally).

Run with the voice venv from the my-film folder:
    tools/voice/.venv/bin/python scripts/make_voice.py narration/<name>.json public/voice/<name>.wav

Script JSON:
{
  "voice": {"ref": "tools/voice/refs/narrator.wav", "temperature": 0.6, "tempo": 0.95},
  "lines": [
    {"text": "At midnight, the settings changed.", "pause": 0.5},
    {"text": "They were almost right.", "pause": 1.2}
  ]
}
- "pause" is the silence AFTER the line (seconds). Longer pauses before reveals.
- Writes <out>.wav (48 kHz mono, -16 LUFS) and <out>.json with each line's start/end in seconds
  and in frames at 30 fps, so scenes can be timed to the voice.
"""
import json
import os
import subprocess
import sys
import tempfile
import time

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
import re

import torch

SR_OUT = 48000
NUMBER_WORDS = set("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred thousand million billion quintillion and".split())
FPS = 30


def tempo(wav: np.ndarray, sr: int, factor: float) -> np.ndarray:
    """Slow down / speed up without changing pitch (ffmpeg atempo is clean for 0.9-1.1)."""
    if abs(factor - 1) < 1e-3:
        return wav
    with tempfile.TemporaryDirectory() as d:
        a, b = os.path.join(d, "a.wav"), os.path.join(d, "b.wav")
        sf.write(a, wav, sr)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", a, "-af", f"atempo={factor}", b], check=True)
        out, _ = sf.read(b, dtype="float32")
    return out


def trim(wav: np.ndarray, sr: int, thresh=0.01) -> np.ndarray:
    """Cut leading/trailing silence, keeping a few ms of air."""
    idx = np.where(np.abs(wav) > thresh)[0]
    if len(idx) == 0:
        return wav
    pad = int(0.03 * sr)
    return wav[max(0, idx[0] - pad): min(len(wav), idx[-1] + pad)]


def main(script_path: str, out_path: str):
    spec = json.load(open(script_path))
    voice = spec.get("voice", {})
    ref = voice.get("ref", "tools/voice/refs/narrator.wav")
    temp = voice.get("temperature", 0.6)
    tempo_f = voice.get("tempo", 0.95)

    from chatterbox.tts_turbo import ChatterboxTurboTTS

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cpu":
        torch.set_num_threads(int(os.environ.get("VOICE_THREADS") or os.cpu_count() or 4))
    model = ChatterboxTurboTTS.from_pretrained(device=device)
    sr = model.sr

    # Whisper check: every take is transcribed; takes that drop words are retried.
    from faster_whisper import WhisperModel

    asr = WhisperModel("small.en", device="cpu", compute_type="int8")
    norm = lambda x: re.sub(r"[^a-z0-9 ]", "", x.lower().replace("-", " ")).split()  # noqa: E731

    def coverage(text: str, wav: np.ndarray) -> float:
        with tempfile.TemporaryDirectory() as d:
            a, b = os.path.join(d, "a.wav"), os.path.join(d, "b.wav")
            sf.write(a, wav, sr)
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", a, "-ar", "16000", b], check=True)
            y16, _ = sf.read(b, dtype="float32")
        heard = norm(" ".join(seg.text for seg in asr.transcribe(y16, language="en")[0]))
        want = [w for w in norm(text) if not w.isdigit()]
        # numbers are spoken as words but transcribed as digits, so only check real words
        want = [w for w in want if w not in NUMBER_WORDS]
        return sum(w in heard for w in want) / max(1, len(want))

    pieces, timings, t = [], [], 0.0
    for i, line in enumerate(spec["lines"]):
        text = line["text"].strip()
        words = len(text.split())
        best, best_wps, best_score = None, 0.0, -1.0
        for attempt in range(6):
            torch.manual_seed(1000 + i * 17 + attempt + 101 * line.get("seed", 0))
            t0 = time.time()
            wav = model.generate(text, audio_prompt_path=ref, temperature=temp).squeeze(0).cpu().numpy()
            wav = trim(wav, sr)
            wps = words / max(0.1, len(wav) / sr)
            # natural narration is ~2.0-3.2 words/s; far outside means a garbled take
            cov = coverage(text, wav)
            pace_ok = 1.6 <= wps <= 3.4 or words <= 2
            ok = pace_ok and cov >= 0.85
            print(f"line {i + 1:2d} try {attempt + 1}: {len(wav) / sr:4.1f}s {wps:3.1f} w/s words heard {cov:4.0%} {'ok' if ok else 'retry'} ({time.time() - t0:.1f}s)", flush=True)
            # best take = all words present first, then closest to a calm pace (~2.6 words/s)
            score = cov * 10 - abs(wps - 2.6)
            if score > best_score:
                best, best_wps, best_score = wav, wps, score
            if ok:
                break
        if best_score < 8.5:
            print(f"WARNING line {i + 1}: no clean take, check it: {text}", flush=True)
        # still rushed? slow just this line a little (never below 0.85x)
        extra = max(0.85, min(1.0, 3.3 / best_wps)) if words > 2 else 1.0
        wav = tempo(best, sr, tempo_f * extra)
        start = t
        t += len(wav) / sr
        timings.append({"text": text, "start": round(start, 3), "end": round(t, 3),
                        "startFrame": round(start * FPS), "endFrame": round(t * FPS)})
        pause = float(line.get("pause", 0.45))
        pieces += [wav, np.zeros(int(pause * sr), dtype=np.float32)]
        t += pause

    audio = np.concatenate(pieces)
    # resample to 48 kHz for video, then loudness-normalise to -16 LUFS
    with tempfile.TemporaryDirectory() as d:
        a, b = os.path.join(d, "a.wav"), os.path.join(d, "b.wav")
        sf.write(a, audio, sr)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", a, "-ar", str(SR_OUT), b], check=True)
        audio, _ = sf.read(b, dtype="float32")
    meter = pyln.Meter(SR_OUT)
    audio = pyln.normalize.loudness(audio, meter.integrated_loudness(audio), -16.0)
    peak = np.max(np.abs(audio))
    if peak > 0.95:
        audio *= 0.95 / peak

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    sf.write(out_path, audio, SR_OUT)
    json.dump({"duration": round(len(audio) / SR_OUT, 3), "lines": timings}, open(out_path.rsplit(".", 1)[0] + ".json", "w"), indent=1)
    total_words = sum(len(l["text"].split()) for l in spec["lines"])
    print(f"wrote {out_path}: {len(audio) / SR_OUT:.1f}s, {total_words / (len(audio) / SR_OUT) * 60:.0f} words/min overall")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
