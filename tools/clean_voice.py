"""Isolate character vocals from game voice-line compilations (runs in tools/demucs/.venv).

htdemucs two-stem separation (vocals vs. music/SFX) -> mono -> split on silence -> drop clips that are
too short or too quiet -> loudness-normalise each clip -> assets/voices/clean/<character>/<stem>_NNN.wav.

usage: clean_voice.py [--root REPO] [--device cpu|cuda] [--sr 40000]
Sources are listed in RAW below (raw file stem -> character); unknown files in raw/ are skipped.
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

RAW = {  # assets/voices/raw/<stem>.wav -> character folder
    "cMcEu4zuk7o": "baymax",   # Kingdom Hearts III Baymax voice lines
    "_DeY8Fw1U4Y": "hiro",     # Disney Infinity Hiro voice lines
}
MIN_CLIP, MAX_CLIP = 1.0, 12.0     # seconds kept per clip (RVC slices to ~3 s itself)
SIL_DB, SIL_LEN = -40, 0.35        # silence threshold / min silence length used to split
TARGET_RMS_DB = -20


def separate(src: Path, td: Path, device: str) -> Path:
    subprocess.run([sys.executable, "-m", "demucs", "-n", "htdemucs", "--two-stems", "vocals",
                    "-d", device, "-j", "4", "-o", str(td), str(src)], check=True)
    return td / "htdemucs" / src.stem / "vocals.wav"


def frames_db(a: np.ndarray, sr: int, hop: float = 0.01) -> np.ndarray:
    h = int(sr * hop)
    n = len(a) // h
    rms = np.sqrt((a[: n * h].reshape(n, h) ** 2).mean(1) + 1e-12)
    return 20 * np.log10(rms)


def split_on_silence(a: np.ndarray, sr: int):
    db = frames_db(a, sr)
    voiced = db > SIL_DB
    hop, min_sil = int(sr * 0.01), int(SIL_LEN / 0.01)
    segs, start, quiet = [], None, 0
    for i, v in enumerate(voiced):
        if v:
            if start is None:
                start = i
            quiet = 0
        elif start is not None:
            quiet += 1
            if quiet >= min_sil:
                segs.append((start, i - quiet + 1))
                start, quiet = None, 0
    if start is not None:
        segs.append((start, len(voiced)))
    pad = 5  # 50 ms of breathing room around each clip
    for s, e in segs:
        s, e = max(0, s - pad) * hop, min(len(voiced), e + pad) * hop
        clip = a[s:e]
        dur = len(clip) / sr
        if dur < MIN_CLIP:
            continue
        # cut overlong clips into <= MAX_CLIP pieces
        n = int(np.ceil(dur / MAX_CLIP))
        for k in range(n):
            yield clip[k * len(clip) // n:(k + 1) * len(clip) // n]


def normalise(c: np.ndarray) -> np.ndarray:
    rms = np.sqrt((c ** 2).mean() + 1e-12)
    c = c * (10 ** (TARGET_RMS_DB / 20) / rms)
    peak = np.abs(c).max()
    return c * (0.95 / peak) if peak > 0.95 else c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--sr", type=int, default=40000)
    args = ap.parse_args()
    root = Path(args.root)
    raw, clean = root / "assets/voices/raw", root / "assets/voices/clean"
    totals, counts = {}, {}
    for char in set(RAW.values()):
        for old in (clean / char).glob("*.wav"):
            old.unlink()
    for src in sorted(raw.glob("*.wav")):
        char = RAW.get(src.stem)
        if not char:
            print(f"skip {src.name}: not in RAW map")
            continue
        out = clean / char
        out.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as td:
            voc = separate(src, Path(td), args.device)
            rs = Path(td) / "vocals_mono.wav"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(voc), "-ac", "1",
                            "-ar", str(args.sr), "-af", "highpass=f=60", str(rs)], check=True)
            a, sr = sf.read(rs, dtype="float32")
        n, secs = counts.get(char, 0), 0.0
        for clip in split_on_silence(a, sr):
            # skip clips that are mostly residual noise (median frame level too low)
            if np.median(frames_db(clip, sr)) < SIL_DB + 6:
                continue
            sf.write(out / f"{src.stem}_{n:03d}.wav", normalise(clip), sr, subtype="PCM_16")
            n += 1
            secs += len(clip) / sr
        counts[char] = n
        totals[char] = totals.get(char, 0) + secs
        print(f"{src.name} -> {out}: {n} clips (cumulative), {secs / 60:.2f} min")
    for c, s in totals.items():
        print(f"TOTAL {c}: {s / 60:.2f} min")


if __name__ == "__main__":
    main()
