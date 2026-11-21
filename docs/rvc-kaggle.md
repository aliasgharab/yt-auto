# Training the RVC voices on Kaggle (free GPU)

Local training on the old laptop's MX550 (2 GB VRAM) worked but was slow; the desktop's RTX 2060 (6 GB) is fine. Kaggle gives ~30 GPU-hours/week free
(T4 16 GB or P100), which trains both characters in roughly 1 hour.

## One-time
1. Create a free account at <https://www.kaggle.com> and verify your phone number
   (required for GPU + internet in notebooks).
2. Settings -> API -> **Create New Token**. New tokens are a single `KGAT_...` string: save it as
   `~/.kaggle/access_token` (chmod 600). Old-style `kaggle.json` files still work too.
3. `uv tool install kaggle --with six`

## Each training run, from the CLI (recommended)
`bash tools/rvc/kaggle_run.sh` uploads the cleaned clips as a private dataset, starts the GPU job, waits,
then downloads only `rvc_models.zip` (the full job output is 3+ GB) and installs it. `status` and `fetch`
check or collect a job started earlier. The Kaggle user comes from `$KAGGLE_USER`, else `kaggle.json`,
else `kernelkids`.

The first run (2026-11-20, hiro 300 / baymax 500 epochs on a T4) finished fine; its models are in the
private assets release as `assets-rvc.tar.zst`.

## Each training run, by hand in the browser
1. Clean the audio locally (if not already done):
   `tools/demucs/.venv/bin/python tools/clean_voice.py`
2. Zip the cleaned clips: `cd assets/voices && zip -r ~/yt-auto-voices.zip clean`
3. Kaggle -> Datasets -> **New Dataset** -> upload `yt-auto-voices.zip`, name it `yt-auto-voices`,
   keep it **Private**. Kaggle unzips it to `/kaggle/input/yt-auto-voices/clean/{hiro,baymax}/`.
4. Kaggle -> Code -> **New Notebook** -> File -> Import Notebook -> upload `tools/rvc/kaggle_train.py`
   (or paste its cells; `# %%` marks cell boundaries).
5. Right panel: **Add Input** -> your `yt-auto-voices` dataset; Settings -> Accelerator **GPU T4 x2**
   (or P100); Internet **On**.
6. **Save Version -> Save & Run All (Commit)** so it runs in the background (you can close the tab).
7. When it finishes, open the version's **Output** tab and download `rvc_models.zip`.

## Install the models
```bash
mkdir -p assets/voices/rvc && unzip ~/Downloads/rvc_models.zip -d assets/voices/rvc
# -> assets/voices/rvc/{hiro,baymax}.{pth,index}
```
Then in `config.yaml` set `duo.voice_backend: rvc`. Tune `rvc_pitch` (semitones) per character if the
voice sits too high/low; if any `rvc_model` file is missing the pipeline falls back to `clone`.

## CI (GitHub Actions, CPU only)
When `config.yaml` has `duo.voice_backend: rvc`, the nightly job:
1. sets `RVC=1`, and `deploy/ci/fetch_assets.sh` also unpacks `assets-rvc.tar.zst` from the assets release;
2. restores `tools/rvc/Applio` from the Actions cache, or builds it with `deploy/ci/install_rvc.sh` (Applio
   pinned to the commit the models were trained with, Python 3.11 venv, CPU torch, plus the rmvpe and
   contentvec models; about 2 GB);
3. runs the conversion with `RVC_DEVICE=cpu`.

If the models, the Applio env, or the conversion itself fail, `duo.py` prints why and renders with the
clone (Chatterbox) voices instead, so a broken RVC setup never costs a video.
After retraining, upload the new models with `deploy/ci/pack_assets.sh --rvc`.
Locally with an NVIDIA GPU: `TORCH_INDEX=https://download.pytorch.org/whl/cu128 deploy/ci/install_rvc.sh`.

## Notes
- Epochs per character are set in `CHARS` at the top of the script (Baymax has less clean audio, so it
  gets more epochs). If a model sounds metallic/over-trained, retrain with fewer epochs.
- Local equivalent: `tools/rvc/train.sh <character> [epochs] [batch] [gpu]` (GPU "" = CPU).
