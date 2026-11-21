#!/usr/bin/env bash
# Install a minimal Applio inference environment for the rvc voice backend (duo.voice_backend: rvc):
# tools/rvc/Applio at a pinned commit, its .venv (Python 3.11, CPU torch by default), and the two models
# inference needs (rmvpe pitch predictor, contentvec embedder). No training pretraineds, no Gradio UI.
#   deploy/ci/install_rvc.sh                                                     # CPU (GitHub Actions)
#   TORCH_INDEX=https://download.pytorch.org/whl/cu128 deploy/ci/install_rvc.sh  # local NVIDIA GPU
# Idempotent: every step is skipped when its output already exists (CI restores tools/rvc/Applio from cache).
set -euo pipefail
cd "$(dirname "$0")/../.."
A=tools/rvc/Applio
REF=ce6ef71915535871b516cdc3f1eaad827ea3bd3c          # Applio commit the Kaggle models were trained with
TORCH_INDEX="${TORCH_INDEX:-https://download.pytorch.org/whl/cpu}"
HF=https://huggingface.co/IAHispano/Applio/resolve/main/Resources

if [ ! -f "$A/core.py" ]; then
  git init -q "$A"
  git -C "$A" fetch -q --depth 1 https://github.com/IAHispano/Applio "$REF"
  git -C "$A" checkout -q FETCH_HEAD
fi

if [ ! -f "$A/.venv/.yt_ok" ]; then
  uv venv -q --allow-existing -p 3.11 "$A/.venv"
  uv pip install -q -p "$A/.venv/bin/python" --index-strategy unsafe-best-match \
    --extra-index-url "$TORCH_INDEX" -r "$A/requirements-engine.txt" python-ffmpeg
  touch "$A/.venv/.yt_ok"
fi

get() {  # get <remote path> <local path>
  [ -s "$A/rvc/models/$2" ] && return
  mkdir -p "$(dirname "$A/rvc/models/$2")"
  curl -fsSL --retry 3 -o "$A/rvc/models/$2.part" "$HF/$1" && mv "$A/rvc/models/$2.part" "$A/rvc/models/$2"
}
get predictors/rmvpe.pt predictors/rmvpe.pt
get embedders/contentvec/pytorch_model.bin embedders/contentvec/pytorch_model.bin
get embedders/contentvec/config.json embedders/contentvec/config.json

"$A/.venv/bin/python" -c "import torch, faiss; print('applio env ok, torch', torch.__version__, 'cuda', torch.cuda.is_available())"
