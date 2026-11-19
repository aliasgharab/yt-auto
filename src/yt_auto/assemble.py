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


# YouTube recommended upload settings (support.google.com/youtube/answer/1722171):
# H.264 High, 2 B-frames, closed GOP of half the frame rate, 4:2:0, BT.709, >= 8 Mbps @1080p30,
# AAC-LC 48 kHz stereo 384 kbps, moov atom at the front (+faststart).
AUDIO_ARGS = ["-c:a", "aac", "-ac", "2", "-ar", "48000", "-b:a", "384k"]
COLOR_ARGS = ["-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709",
              "-color_trc", "bt709", "-color_range", "tv",
              # encoders don't all write the VUI colour tags; stamp BT.709 into the H.264 bitstream
              "-bsf:v", "h264_metadata=colour_primaries=1:transfer_characteristics=1:"
                        "matrix_coefficients=1:video_full_range_flag=0"]


def _works(enc: str) -> bool:
    probe = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                            "color=s=256x256:d=0.1", "-c:v", enc, "-f", "null", "-"], capture_output=True)
    return probe.returncode == 0


def _encoder_args(cfg):
    """Best available H.264 encoder: NVENC (laptop GPU) -> libx264 (CI/Ubuntu) -> libopenh264 (Fedora)."""
    gop = str(max(1, round(cfg["render"]["fps"] / 2)))
    pref = cfg["render"].get("encoder", "h264_nvenc")
    for enc in dict.fromkeys([pref, "h264_nvenc", "libx264", "libopenh264"]):
        if not _works(enc):
            continue
        if enc == "h264_nvenc":
            v = ["-c:v", "h264_nvenc", "-preset", "p6", "-profile:v", "high", "-rc", "vbr", "-cq", "19",
                 "-b:v", "10M", "-maxrate", "16M", "-bufsize", "20M", "-bf", "2", "-g", gop,
                 "-strict_gop", "1"]
        elif enc == "libx264":
            v = ["-c:v", "libx264", "-preset", "slow", "-profile:v", "high", "-crf", "18",
                 "-maxrate", "16M", "-bufsize", "20M", "-bf", "2", "-g", gop, "-keyint_min", gop,
                 "-sc_threshold", "0", "-flags", "+cgop"]
        else:
            v = ["-c:v", "libopenh264", "-profile:v", "high", "-b:v", "12M", "-g", gop]
        return v + COLOR_ARGS
    raise RuntimeError("no working H.264 encoder found in ffmpeg")


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
           _encoder_args(cfg) + AUDIO_ARGS + [
                                 "-movflags", "+faststart", "-shortest", str(out)])
    (out.parent / "ffmpeg_cmd.txt").write_text(" ".join(cmd))
    subprocess.run(cmd, check=True)
