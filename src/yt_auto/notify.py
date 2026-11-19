"""Phone push notifications via ntfy.sh (free, no account). Topic lives in ~/.config/yt-auto/ntfy.json
(or $YT_AUTO_CONFIG_DIR/ntfy.json); env NTFY_TOPIC overrides the topic."""

from __future__ import annotations

import base64
import json
import logging
import os
import secrets
import urllib.request
from pathlib import Path

from .config import config_dir

log = logging.getLogger(__name__)

CONFIG_PATH = config_dir() / "ntfy.json"   # YT_AUTO_CONFIG_DIR overrides the dir
DEFAULT_SERVER = "https://ntfy.sh"


def settings(path: Path = CONFIG_PATH) -> dict:
    """Load (or create on first use) {server, topic}; the topic is a random unguessable string.
    Env NTFY_TOPIC (and optional NTFY_SERVER) win over the file, e.g. on CI."""
    if os.environ.get("NTFY_TOPIC"):
        return {"server": os.environ.get("NTFY_SERVER") or DEFAULT_SERVER, "topic": os.environ["NTFY_TOPIC"]}
    if path.exists():
        return json.loads(path.read_text())
    path.parent.mkdir(parents=True, exist_ok=True)
    s = {"server": DEFAULT_SERVER, "topic": "yt-auto-" + secrets.token_urlsafe(18)}
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(s, f, indent=2)
    os.chmod(path, 0o600)
    return s


def _header(v: str) -> str:
    """HTTP headers must be latin-1; ntfy accepts RFC 2047 encoded-words for anything else."""
    try:
        v.encode("latin-1")
        return v
    except UnicodeEncodeError:
        return "=?UTF-8?B?" + base64.b64encode(v.encode()).decode() + "?="


def send(title: str, message: str, click: str | None = None, tags: list[str] | None = None,
         priority: int | None = None, path: Path = CONFIG_PATH, opener=None,
         actions: list[tuple[str, str]] | None = None) -> bool:
    """Best effort: never raises, returns True on success. actions: [(label, url)] -> "view" buttons."""
    try:
        s = settings(path)
        headers = {"Title": _header(title)}
        if click:
            headers["Click"] = click
        if tags:
            headers["Tags"] = ",".join(tags)
        if priority:
            headers["Priority"] = str(priority)
        if actions:
            headers["Actions"] = _header("; ".join(f"view, {lbl.replace(',', ' ')}, {url}"
                                                   for lbl, url in actions if url))
        req = urllib.request.Request(f"{s.get('server', DEFAULT_SERVER).rstrip('/')}/{s['topic']}",
                                     data=message.encode(), method="POST", headers=headers)
        with (opener or urllib.request.urlopen)(req, timeout=20) as r:
            r.read()
        return True
    except Exception as e:  # notifications must never break the pipeline
        log.warning("ntfy push failed: %s", e)
        return False


def cmd_topic(_args=None, _cfg=None) -> int:
    s = settings()
    url = f"{s.get('server', DEFAULT_SERVER).rstrip('/')}/{s['topic']}"
    print(f"ntfy topic: {s['topic']}\n"
          f"web:        {url}\n\n"
          "Subscribe on your phone:\n"
          "  1. Install the free ntfy app (F-Droid / Play Store / App Store).\n"
          "  2. Tap +  ->  'Subscribe to topic'  ->  paste the topic above (server: ntfy.sh).\n"
          "  3. Keep the topic secret: anyone who knows it can read/send these notifications.\n"
          "Test it:  yt-auto ntfy-topic --test")
    if getattr(_args, "test", False):
        ok = send("yt-auto test", "Notifications are working.", tags=["white_check_mark"])
        print("test push sent" if ok else "test push FAILED (see log)")
    return 0
