#!/usr/bin/env bash
# Install the fonts unpacked from the asset bundle (./fonts) into ~/.local/share/fonts, where
# config.resolve_fonts() finds them by file name.
set -euo pipefail
cd "$(dirname "$0")/../.."
dest="$HOME/.local/share/fonts"
mkdir -p "$dest/Inter"
cp fonts/Inter/*.ttf "$dest/Inter/"
cp fonts/mono/* "$dest/"
rm -rf fonts
fc-cache -f "$dest" >/dev/null 2>&1 || true
