# Training the RVC voices on Kaggle (free GPU)

Local training on the MX550 (2 GB VRAM) works but is slow. Kaggle gives ~30 GPU-hours/week free
(T4 16 GB or P100), which trains both characters in roughly 1 hour.

## One-time
1. Create a free account at <https://www.kaggle.com> and verify your phone number
   (required for GPU + internet in notebooks).

## Each training run
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

## Notes
- Epochs per character are set in `CHARS` at the top of the script (Baymax has less clean audio, so it
  gets more epochs). If a model sounds metallic/over-trained, retrain with fewer epochs.
- Local equivalent: `tools/rvc/train.sh <character> [epochs] [batch] [gpu]` (GPU "" = CPU).
