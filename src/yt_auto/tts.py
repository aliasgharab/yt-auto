"""Stage 5: narration -> audio, one wav per scene (Kokoro, local, Apache-2.0)."""

from pathlib import Path

import numpy as np
import soundfile as sf

SR = 24000
_kokoro = None


def _tts(text: str, cfg: dict) -> np.ndarray:
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro
        root = cfg["_root"]
        _kokoro = Kokoro(str(root / "models/kokoro-v1.0.onnx"), str(root / "models/voices-v1.0.bin"))
    samples, sr = _kokoro.create(text, voice=cfg["tts"]["voice"], speed=cfg["tts"]["speed"], lang="en-us")
    assert sr == SR
    return samples.astype(np.float32)


def synth_scenes(scenes: list[dict], cfg: dict, outdir: Path, gap: float = 0.28) -> list[float]:
    """Writes outdir/narration.wav; returns per-scene durations in seconds (incl. trailing gap)."""
    outdir.mkdir(parents=True, exist_ok=True)
    silence = np.zeros(int(SR * gap), dtype=np.float32)
    pieces, durs = [], []
    for sc in scenes:
        audio = np.concatenate([_tts(sc["narration"], cfg), silence])
        pieces.append(audio)
        durs.append(len(audio) / SR)
    sf.write(outdir / "narration.wav", np.concatenate(pieces), SR)
    return durs
