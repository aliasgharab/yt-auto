#!/usr/bin/env bash
# Install + enable the yt-auto systemd *user* timers (no sudo needed).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
dest="$HOME/.config/systemd/user"
mkdir -p "$dest"
cp "$here"/systemd/yt-auto-*.service "$here"/systemd/yt-auto-*.timer "$dest"/
systemctl --user daemon-reload
for t in nightly publish weekly; do
  systemctl --user enable --now "yt-auto-$t.timer"
done
# Let timers fire while logged out (e.g. 02:30 after a reboot without login).
loginctl enable-linger "$USER" 2>/dev/null || echo "note: 'loginctl enable-linger $USER' failed; timers only run while logged in"
systemctl --user list-timers 'yt-auto-*'
