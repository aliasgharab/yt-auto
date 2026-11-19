"""Build a clean ~15 s voice reference from a voice-line compilation: keep fluent spoken lines only."""
import sys
import numpy as np, soundfile as sf
from faster_whisper import WhisperModel

src, out, target = sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 15
audio, sr = sf.read(src, dtype="float32")
if audio.ndim > 1:
    audio = audio.mean(1)
a16 = np.interp(np.linspace(0, len(audio) - 1, int(len(audio) * 16000 / sr)), np.arange(len(audio)), audio).astype(np.float32)
m = WhisperModel("small.en", device="cpu", compute_type="int8")
segs, _ = m.transcribe(a16, vad_filter=True, word_timestamps=False)
good = []
for s in segs:
    words = len(s.text.split())
    dur = s.end - s.start
    if 1.8 <= dur <= 7 and words >= 5 and words / dur >= 1.6 and s.avg_logprob > -0.5 and s.no_speech_prob < 0.3:
        good.append(s)
good.sort(key=lambda s: s.avg_logprob, reverse=True)
picked, total = [], 0
for s in good:
    if total >= target:
        break
    picked.append(s); total += s.end - s.start
picked.sort(key=lambda s: s.start)
gap = np.zeros(int(sr * 0.3), dtype=np.float32)
parts = []
for s in picked:
    print(f"{s.start:7.1f}-{s.end:6.1f}  {s.text.strip()}")
    parts += [audio[int(s.start * sr):int(s.end * sr)], gap]
ref = np.concatenate(parts)
ref /= np.abs(ref).max() + 1e-6
sf.write(out, 0.9 * ref, sr)
print(f"-> {out}: {len(ref) / sr:.1f}s from {len(picked)} lines")
