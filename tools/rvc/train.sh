#!/usr/bin/env bash
# Train one RVC voice model with Applio's CLI from Demucs-cleaned clips, then install it for the rvc backend.
#   usage: tools/rvc/train.sh CHARACTER [EPOCHS] [BATCH] [GPU]      e.g. tools/rvc/train.sh hiro 300 4 0
#   GPU "" = CPU training (very slow).  Run detached:  setsid nohup tools/rvc/train.sh hiro &> logs/rvc-hiro.log &
# Inputs : assets/voices/clean/<character>/*.wav       (tools/clean_voice.py)
# Outputs: assets/voices/rvc/<character>.pth + .index  (referenced by config.yaml duo.characters.*.rvc_model)
set -euo pipefail
ROOT="${YT_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"  # YT_ROOT overrides (e.g. run from a git worktree)
CHAR="${1:?character}"; EPOCHS="${2:-300}"; BATCH="${3:-4}"; GPU="${4-0}"
SR=40000
APPLIO="$ROOT/tools/rvc/Applio"; PY="$APPLIO/.venv/bin/python"
DATA="$ROOT/assets/voices/clean/$CHAR"
cd "$APPLIO"
echo "== $(date -Is) $CHAR: $(command ls "$DATA"/*.wav | wc -l) clips, epochs=$EPOCHS batch=$BATCH gpu=${GPU:-cpu}"
if [ ! -f "logs/$CHAR/.yt_extracted" ]; then
  "$PY" core.py preprocess --model-name "$CHAR" --dataset-path "$DATA" --sample-rate $SR \
      --cpu-cores 10 --cut-preprocess Automatic --normalization-mode post
  "$PY" core.py extract --model-name "$CHAR" --f0-method rmvpe --cpu-cores 10 ${GPU:+--gpu "$GPU"} \
      --sample-rate $SR --embedder-model contentvec
  touch "logs/$CHAR/.yt_extracted"
fi
echo "== $(date -Is) train"
"$PY" core.py train --model-name "$CHAR" --vocoder HiFi-GAN --sample-rate $SR --batch-size "$BATCH" \
    --total-epoch "$EPOCHS" --save-every-epoch 25 --save-only-latest --pretrained \
    ${GPU:+--gpu "$GPU"} --index-algorithm Auto
"$PY" core.py index --model-name "$CHAR" --index-algorithm Auto
W="$(command ls -t logs/$CHAR/${CHAR}_*e_*s.pth | head -1)"
mkdir -p "$ROOT/assets/voices/rvc"
cp "$W" "$ROOT/assets/voices/rvc/$CHAR.pth"
cp "logs/$CHAR/$CHAR.index" "$ROOT/assets/voices/rvc/$CHAR.index"
echo "== $(date -Is) done: $W -> assets/voices/rvc/$CHAR.pth"
