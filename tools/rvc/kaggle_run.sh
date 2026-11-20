#!/usr/bin/env bash
# Train the Hiro + Baymax RVC voices on Kaggle's free GPU, fully from the command line.
#   tools/rvc/kaggle_run.sh            # upload clips, start the GPU job, wait, download + install models
#   tools/rvc/kaggle_run.sh status     # just show the job status
#   tools/rvc/kaggle_run.sh fetch      # download + install the models of a finished job
# Needs: `kaggle` CLI (uv tool install kaggle) and ~/.kaggle/kaggle.json (Kaggle -> Settings -> API ->
# Create New Token), and a phone-verified Kaggle account (GPU + internet in notebooks).
# Output: assets/voices/rvc/{hiro,baymax}.{pth,index}  (then set duo.voice_backend: rvc to A/B).
set -euo pipefail
ROOT="${YT_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
HERE="$(cd "$(dirname "$0")" && pwd)"
K="${KAGGLE:-$(command -v kaggle || echo "$HOME/.local/bin/kaggle")}"
USER_K="$(python3 -c "import json,os;print(json.load(open(os.path.expanduser('~/.kaggle/kaggle.json')))['username'])")"
DS="$USER_K/yt-auto-voices"
KERNEL="$USER_K/yt-auto-rvc-train"
WORK="${TMPDIR:-/tmp}/yt-auto-kaggle"; mkdir -p "$WORK"

status() { "$K" kernels status "$KERNEL" 2>&1 | tail -1; }

fetch() {
  rm -rf "$WORK/out" && mkdir -p "$WORK/out"
  "$K" kernels output "$KERNEL" -p "$WORK/out" >/dev/null
  zip="$(find "$WORK/out" -name 'rvc_models.zip' | head -1)"
  [ -n "$zip" ] || { echo "no rvc_models.zip in the job output (see $WORK/out/*.log)"; exit 1; }
  mkdir -p "$ROOT/assets/voices/rvc" && unzip -o -q "$zip" -d "$ROOT/assets/voices/rvc"
  ls -l "$ROOT/assets/voices/rvc"
  echo "installed. A/B: set duo.voice_backend: rvc in config.yaml and render one Short."
}

case "${1:-run}" in
  status) status; exit ;;
  fetch)  fetch; exit ;;
esac

echo "== 1/4 dataset $DS (cleaned clips)"
D="$WORK/dataset"; rm -rf "$D" && mkdir -p "$D"
(cd "$ROOT/assets/voices" && zip -qr "$D/yt-auto-voices.zip" clean)
printf '{"title":"yt-auto-voices","id":"%s","licenses":[{"name":"other"}]}\n' "$DS" > "$D/dataset-metadata.json"
if "$K" datasets status "$DS" >/dev/null 2>&1; then
  "$K" datasets version -p "$D" -m "update clips" -r zip -q
else
  "$K" datasets create -p "$D" -r zip -q          # private by default
fi
for i in $(seq 1 60); do [ "$("$K" datasets status "$DS" 2>/dev/null)" = "ready" ] && break; sleep 10; done

echo "== 2/4 push GPU job $KERNEL"
KD="$WORK/kernel"; rm -rf "$KD" && mkdir -p "$KD"
cp "$HERE/kaggle_train.py" "$KD/"
cat > "$KD/kernel-metadata.json" <<EOF
{"id": "$KERNEL", "title": "yt-auto-rvc-train", "code_file": "kaggle_train.py",
 "language": "python", "kernel_type": "script", "is_private": true,
 "enable_gpu": true, "enable_internet": true, "dataset_sources": ["$DS"]}
EOF
"$K" kernels push -p "$KD"

echo "== 3/4 waiting (both voices take about 1-1.5 h on a T4; Ctrl+C is safe: re-run with 'status'/'fetch')"
while true; do
  s="$(status)"; echo "$(date +%H:%M) $s"
  case "$s" in *complete*) break ;; *error*|*cancel*) echo "job failed: see the log on kaggle.com/code/$KERNEL"; exit 1 ;; esac
  sleep 120
done

echo "== 4/4 download + install"
fetch
