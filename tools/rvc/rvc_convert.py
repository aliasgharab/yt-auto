"""Batch RVC voice conversion with Applio (runs in tools/rvc/Applio/.venv).

usage: rvc_convert.py jobs.json
  jobs = [{"in", "out", "model", "index"?, "pitch"?, "index_rate"?, "protect"?, "f0_method"?}]
Models (and the HuBERT embedder) are loaded once and reused across jobs; jobs are run grouped by model.
Set RVC_DEVICE=cpu to force CPU (default: CUDA if available, e.g. while the GPU is busy training).
"""
import json
import os
import sys
import time
from pathlib import Path

if os.environ.get("RVC_DEVICE") == "cpu":
    os.environ["CUDA_VISIBLE_DEVICES"] = ""

APPLIO = Path(__file__).resolve().parent / "Applio"
jobs = [dict(j, **{k: str(Path(j[k]).resolve()) for k in ("in", "out", "model") if j.get(k)})
        for j in json.load(open(sys.argv[1]))]
for j in jobs:
    if j.get("index"):
        j["index"] = str(Path(j["index"]).resolve())
os.chdir(APPLIO)                       # Applio resolves its bundled models relative to cwd
sys.path.insert(0, str(APPLIO))

import torch  # noqa: E402
from rvc.infer.infer import VoiceConverter  # noqa: E402

torch.set_num_threads(min(12, os.cpu_count() or 4))
vc = VoiceConverter()
vc.cleanup_model = lambda: None        # keep model + embedder resident between files
print(f"rvc device: {vc.config.device}", flush=True)
for j in sorted(jobs, key=lambda j: j["model"]):
    t0 = time.time()
    vc.convert_audio(
        audio_input_path=j["in"], audio_output_path=j["out"], model_path=j["model"],
        index_path=j.get("index") or "", pitch=int(j.get("pitch", 0)),
        f0_method=j.get("f0_method", "rmvpe"), index_rate=float(j.get("index_rate", 0.5)),
        volume_envelope=1.0, protect=float(j.get("protect", 0.33)), embedder_model="contentvec",
        export_format="WAV", formant_shifting=False,
    )
    print(f"{time.time() - t0:5.1f}s  {j['out']}", flush=True)
