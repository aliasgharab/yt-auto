#!/usr/bin/env bash
# Run on CI: download + unpack the private asset release, install fonts. Env: GH_TOKEN (read access to
# $ASSETS_REPO), ASSETS_REPO=<owner>/yt-auto-assets. RVC=1 also fetches the RVC voice models (assets-rvc).
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p dist
gh release download assets -R "$ASSETS_REPO" -D dist --clobber -p 'assets-core.tar.zst' -p 'assets-gameplay.tar'
tar --zstd -xf dist/assets-core.tar.zst
tar -xf dist/assets-gameplay.tar
if [ "${RVC:-}" = 1 ]; then   # assets/voices/rvc/{hiro,baymax}.{pth,index}; a missing file means clone fallback
  gh release download assets -R "$ASSETS_REPO" -D dist --clobber -p 'assets-rvc.tar.zst' &&
    tar --zstd -xf dist/assets-rvc.tar.zst || echo "::warning::no RVC models in the asset release"
fi
bash deploy/ci/install_fonts.sh
rm -rf dist
