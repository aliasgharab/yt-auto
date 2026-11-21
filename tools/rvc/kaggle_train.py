# %% [markdown]
# # RVC character voices on Kaggle (free T4 / P100 GPU)
# Trains the Hiro + Baymax RVC models with Applio's CLI. See docs/rvc-kaggle.md.
# Settings -> Accelerator: GPU T4 x2 (or P100); Internet: ON.
# Input: a Kaggle dataset "yt-auto-voices" containing  clean/hiro/*.wav  and  clean/baymax/*.wav
#        (zip of assets/voices/clean/ from tools/clean_voice.py).
# Output: /kaggle/working/rvc/<character>.pth + <character>.index  -> download, put in assets/voices/rvc/.

# %%
import glob
import os
import shutil
import subprocess
import sys

CHARS = {"hiro": 300, "baymax": 500}   # character -> epochs (smaller dataset => more epochs)
BATCH = 8                               # T4 16 GB handles 8-16
SR = 40000
DATA = next(iter(sorted(glob.glob("/kaggle/input/**/clean", recursive=True))), "/kaggle/input/yt-auto-voices/clean")
WORK = "/kaggle/working"
APPLIO = f"{WORK}/Applio"
OUT = f"{WORK}/rvc"


def sh(cmd, cwd=APPLIO):
    print("+", cmd, flush=True)
    subprocess.run(cmd, shell=True, check=True, cwd=cwd)


# %% install Applio (CLI only; skip the Gradio UI deps)
if not os.path.isdir(APPLIO):
    sh(f"git clone --depth 1 https://github.com/IAHispano/Applio {APPLIO}", cwd=WORK)
    # Kaggle images already ship CUDA torch; keep it and install the rest of the engine deps.
    sh("grep -vE '^(torch|torchaudio)==' requirements-engine.txt > /tmp/req.txt && "
       f"{sys.executable} -m pip install -q -r /tmp/req.txt python-ffmpeg")
    sh(f"{sys.executable} core.py prerequisites --pretraineds-hifigan --models --no-exe")

# %% train each character
os.makedirs(OUT, exist_ok=True)
py = sys.executable
for char, epochs in CHARS.items():
    src = f"{DATA}/{char}"
    print(f"== {char}: {len(glob.glob(src + '/*.wav'))} clips", flush=True)
    sh(f"{py} core.py preprocess --model-name {char} --dataset-path {src} --sample-rate {SR} "
       f"--cpu-cores 4 --cut-preprocess Automatic --normalization-mode post")
    sh(f"{py} core.py extract --model-name {char} --f0-method rmvpe --cpu-cores 4 --gpu 0 "
       f"--sample-rate {SR} --embedder-model contentvec")
    sh(f"{py} core.py train --model-name {char} --vocoder HiFi-GAN --sample-rate {SR} --batch-size {BATCH} "
       f"--total-epoch {epochs} --save-every-epoch 50 --save-only-latest --pretrained --gpu 0 "
       f"--index-algorithm Auto")
    sh(f"{py} core.py index --model-name {char} --index-algorithm Auto")
    w = max(glob.glob(f"{APPLIO}/logs/{char}/{char}_*e_*s.pth"), key=os.path.getmtime)
    shutil.copy(w, f"{OUT}/{char}.pth")
    shutil.copy(f"{APPLIO}/logs/{char}/{char}.index", f"{OUT}/{char}.index")
    print(f"== {char} done: {w}", flush=True)

# %% bundle for download (Output tab -> rvc_models.zip)
shutil.make_archive(f"{WORK}/rvc_models", "zip", OUT)
print(os.listdir(OUT))
