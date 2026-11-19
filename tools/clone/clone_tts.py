"""Batch zero-shot voice cloning with Chatterbox (runs in tools/clone/.venv).
usage: clone_tts.py jobs.json   where jobs = [{"text", "ref", "out", "exaggeration"?, "cfg_weight"?}]"""
import json, os, sys, time
import torch, torchaudio
from chatterbox.tts import ChatterboxTTS

torch.set_num_threads(int(os.environ.get("CLONE_THREADS") or os.cpu_count() or 4))
jobs = json.load(open(sys.argv[1]))
model = ChatterboxTTS.from_pretrained(device="cpu")
for j in jobs:
    t0 = time.time()
    wav = model.generate(j["text"], audio_prompt_path=j["ref"],
                         exaggeration=j.get("exaggeration", 0.5), cfg_weight=j.get("cfg_weight", 0.5))
    torchaudio.save(j["out"], wav, model.sr)
    print(f"{time.time() - t0:5.1f}s  {wav.shape[-1] / model.sr:4.1f}s audio  {j['out']}", flush=True)
