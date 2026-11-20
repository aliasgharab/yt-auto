#!/usr/bin/env bash
# Run on the laptop: bundle the git-ignored assets CI needs into dist/assets-*.tar.zst and upload them as
# release "assets" of the PRIVATE repo $ASSETS_REPO (default <you>/yt-auto-assets). Needs gh + zstd.
#   deploy/ci/pack_assets.sh [gameplay clips to include...]   (default: the smallest clip)
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$root"
repo="${ASSETS_REPO:-$(gh api user -q .login)/yt-auto-assets}"
mkdir -p dist
if [ $# -gt 0 ]; then clips=("$@"); else clips=("$(ls -S assets/gameplay/*.mp4 | tail -1)"); fi
fonts=$(mktemp -d); trap 'rm -rf "$fonts"' EXIT
mkdir -p "$fonts/fonts/Inter" "$fonts/fonts/mono"
cp ~/.local/share/fonts/Inter/Inter-*.ttf "$fonts/fonts/Inter/"
cp "$(.venv/bin/python -c 'from yt_auto.config import load_config; print(load_config()["render"]["mono_font"])')" "$fonts/fonts/mono/"
tar --zstd -cf dist/assets-core.tar.zst models/kokoro-v1.0.onnx models/voices-v1.0.bin \
    assets/characters/*.png assets/voices/*_ref.wav -C "$fonts" fonts
tar -cf dist/assets-gameplay.tar "${clips[@]}"          # mp4 is already compressed
ls -lh dist/assets-*
gh repo view "$repo" >/dev/null 2>&1 || gh repo create "$repo" --private -d "yt-auto binary assets (CI only)"
gh release view assets -R "$repo" >/dev/null 2>&1 || gh release create assets -R "$repo" -t assets -n "CI assets"
gh release upload assets -R "$repo" --clobber dist/assets-core.tar.zst dist/assets-gameplay.tar
echo "uploaded to $repo release 'assets'"
