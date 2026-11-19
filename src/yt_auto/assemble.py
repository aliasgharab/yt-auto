"""Stage 8: keyframes + narration + captions (+ optional music) -> final MP4, one ffmpeg pass."""

import random
import subprocess
from pathlib import Path

XFADE = 0.25


def _reveal_durations(n: int, d: float) -> list[float]:
    """Split scene duration d across n reveal steps; later steps get the remainder."""
    if n == 1:
        return [d]
    step = 0.8 * d / n
    return [step] * (n - 1) + [d - step * (n - 1)]


def _encoder_args(cfg):
    enc = cfg["render"].get("encoder", "h264_nvenc")
    probe = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                            "color=s=256x256:d=0.1", "-c:v", enc, "-f", "null", "-"], capture_output=True)
    if enc == "h264_nvenc" and probe.returncode == 0:
        return ["-c:v", "h264_nvenc", "-preset", "p6", "-rc", "vbr", "-cq", "20", "-b:v", "0"]
    return ["-c:v", "libopenh264", "-b:v", "10M"]


def assemble(scene_frames: list[list[Path]], durs: list[float], narration: Path, ass: Path | None,
             size, cfg, out: Path, music_dir: Path | None = None):
    W, H = size
    fps = cfg["render"]["fps"]
    inputs, filters, labels = [], [], []
    idx = 0
    for si, (frames, d) in enumerate(zip(scene_frames, durs)):
        total = d + (XFADE if si < len(durs) - 1 else 0)
        parts = []
        for f, fd in zip(frames, _reveal_durations(len(frames), total)):
            inputs += ["-loop", "1", "-framerate", str(fps), "-t", f"{fd:.3f}", "-i", str(f)]
            parts.append(f"[{idx}:v]")
            idx += 1
        filters.append(f"{''.join(parts)}concat=n={len(parts)}:v=1:a=0,"
                       f"scale={W}:{H},setsar=1,fps={fps},format=yuv420p[s{si}]")
        labels.append(f"s{si}")

    acc, acc_len = labels[0], durs[0] + XFADE
    for si in range(1, len(labels)):
        nxt = f"x{si}"
        filters.append(f"[{acc}][{labels[si]}]xfade=transition=fade:duration={XFADE}:"
                       f"offset={acc_len - XFADE:.3f}[{nxt}]")
        acc, acc_len = nxt, acc_len + durs[si]
    vchain = f"[{acc}]"
    if ass:
        esc = str(ass).replace("\\", "\\\\").replace(":", "\\:")
        fontsdir = cfg["render"]["font_dir"]
        filters.append(f"{vchain}ass={esc}:fontsdir={fontsdir}[vout]")
        vchain = "[vout]"

    a_idx = idx
    inputs += ["-i", str(narration)]
    achain = f"[{a_idx}:a]"
    tracks = sorted(music_dir.glob("*.mp3")) + sorted(music_dir.glob("*.ogg")) if music_dir and music_dir.exists() else []
    if tracks:
        inputs += ["-stream_loop", "-1", "-i", str(random.choice(tracks))]
        filters.append(f"[{a_idx + 1}:a]volume=0.10,afade=t=in:d=1[m];"
                       f"{achain}[m]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[amix]")
        achain = "[amix]"
    filters.append(f"{achain}loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]")

    cmd = (["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-stats"] + inputs +
           ["-filter_complex", ";".join(filters), "-map", vchain, "-map", "[aout]"] +
           _encoder_args(cfg) + ["-pix_fmt", "yuv420p", "-c:a", "aac", "-ac", "2", "-b:a", "192k",
                                 "-movflags", "+faststart", "-shortest", str(out)])
    (out.parent / "ffmpeg_cmd.txt").write_text(" ".join(cmd))
    subprocess.run(cmd, check=True)
