#!/usr/bin/env bash
# Run on CI: download + unpack the private asset release, install fonts. Env: GH_TOKEN (read access to
# $ASSETS_REPO), ASSETS_REPO=<owner>/yt-auto-assets.
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p dist
gh release download assets -R "$ASSETS_REPO" -D dist --clobber
tar --zstd -xf dist/assets-core.tar.zst
tar -xf dist/assets-gameplay.tar
bash deploy/ci/install_fonts.sh
rm -rf dist
