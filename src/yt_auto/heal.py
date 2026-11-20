"""Self-healing helpers: transient-error detection + retry with backoff, and the preflight check.

Transient = worth retrying and NOT a bug: network drops, timeouts, 429/5xx, Hugging Face download
hiccups, Claude overload / usage-limit. A Short whose build still fails for a transient reason after
the retries goes back to Idea (tried again next night) instead of Failed.

  yt-auto preflight      Chatterbox loads, Notion + YouTube + Claude logins work; ntfy + exit 1 if not
"""

from __future__ import annotations

import logging
import random
import re
import socket
import subprocess
import time
import urllib.error

from . import notify

log = logging.getLogger("yt_auto.heal")

TRANSIENT_RX = re.compile(
    r"timed? ?out|timeout|temporar(y|ily)|connection (reset|refused|aborted|error)|remotedisconnected|"
    r"incompleteread|broken pipe|network is unreachable|name resolution|name or service not known|"
    r"max retries exceeded|too many requests|rate.?limit|\b(429|500|502|503|504|529)\b|overloaded|"
    r"service unavailable|bad gateway|internal server error|usage limit|try again|"
    r"huggingface|hf_hub|hub\.huggingface|cas-bridge|xethub|ssl(error|: )|eof occurred",
    re.I)

# never transient, even if the text matches the regex above (needs a human / code fix)
PERMANENT_RX = re.compile(r"invalid_grant|unauthori[sz]ed|\b401\b|\b403\b|forbidden|not connected|"
                          r"quotaexceeded|quota exceeded|lacks the|invalid api key|please run /login", re.I)


def _chain(exc: BaseException):
    seen = set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        yield exc
        exc = exc.__cause__ or exc.__context__


def is_transient(exc: BaseException) -> bool:
    text = " ".join(f"{type(e).__name__}: {e}" for e in _chain(exc))
    if isinstance(exc, subprocess.CalledProcessError):
        text += f" {exc.stderr or ''} {exc.output or ''}"
    if PERMANENT_RX.search(text):
        return False
    for e in _chain(exc):
        if isinstance(e, (TimeoutError, socket.timeout, ConnectionError, urllib.error.URLError)):
            return True
        status = getattr(getattr(e, "resp", None), "status", None) or getattr(e, "code", None)
        if isinstance(status, int) and (status == 429 or 500 <= status < 600):
            return True
    return bool(TRANSIENT_RX.search(text))


def retry(fn, tries: int = 3, base: float = 5.0, sleep=time.sleep, what: str = "call"):
    """Run fn(); on a transient error retry up to `tries` total with exponential backoff + jitter."""
    for attempt in range(1, tries + 1):
        try:
            return fn()
        except Exception as e:
            if attempt >= tries or not is_transient(e):
                raise
            wait = base * 2 ** (attempt - 1) * (1 + random.random() / 2)
            log.warning("%s: transient error (%s: %s); retry %d/%d in %.0fs", what, type(e).__name__,
                        str(e)[:200], attempt + 1, tries, wait)
            sleep(wait)


# ---------------------------------------------------------------- preflight

def _check_notion(cfg):
    from .notion import Notion
    Notion().check()
    return "ok"


def _check_youtube(cfg):
    from . import youtube
    if not youtube.is_configured():
        raise RuntimeError("YouTube credentials missing")
    yt = youtube._youtube(manage=True)          # refreshes the token: catches revoked/expired logins
    items = yt.channels().list(part="snippet", mine=True).execute().get("items") or []
    if not items:
        raise RuntimeError("token works but the account has no channel")
    youtube._analytics()
    return items[0]["snippet"]["title"]


def _check_claude(cfg):
    res = subprocess.run(["claude", "-p", "--model", "haiku", "--tools", "", "--no-session-persistence",
                          "Reply with exactly: OK"], capture_output=True, text=True, timeout=180)
    if res.returncode != 0 or "OK" not in res.stdout:
        raise RuntimeError(f"claude CLI: rc={res.returncode} {(res.stderr or res.stdout)[-300:]}")
    return "ok"


def _check_chatterbox(cfg):
    if (cfg.get("duo") or {}).get("voice_backend") != "clone":
        return "skipped (voice_backend is not clone)"
    py = cfg["_root"] / "tools/clone/.venv/bin/python"
    if not py.exists():
        raise RuntimeError(f"Chatterbox venv missing: {py}")
    res = subprocess.run([str(py), "-c", "from chatterbox.tts import ChatterboxTTS; "
                          "ChatterboxTTS.from_pretrained(device='cpu'); print('LOADED')"],
                         capture_output=True, text=True, timeout=1800)
    if res.returncode != 0 or "LOADED" not in res.stdout:
        raise RuntimeError(f"Chatterbox failed to load: {(res.stderr or res.stdout)[-500:]}")
    return "loaded"


CHECKS = {"notion": _check_notion, "youtube": _check_youtube, "claude": _check_claude,
          "chatterbox": _check_chatterbox}


def preflight(cfg: dict, checks: dict | None = None, sleep=time.sleep) -> dict:
    """{name: (ok, detail)}; each check gets the transient retries. ntfy once if anything is broken."""
    out = {}
    for name, fn in (checks or CHECKS).items():
        try:
            out[name] = (True, str(retry(lambda: fn(cfg), tries=3, base=10, sleep=sleep, what=name)))
        except Exception as e:
            out[name] = (False, f"{type(e).__name__}: {str(e)[:300]}")
        log.info("preflight %-10s %s  %s", name, "OK  " if out[name][0] else "FAIL", out[name][1])
    bad = {k: v[1] for k, v in out.items() if not v[0]}
    if bad:
        from .pipeline import ci_run_url
        notify.send("yt-auto preflight: tonight's build will fail",
                    "\n".join(f"{k}: {v}" for k, v in bad.items())[:700], click=ci_run_url(),
                    tags=["warning"], priority=4)
    return out


def register(sub) -> None:
    p = sub.add_parser("preflight", help="check Chatterbox, Notion, YouTube and Claude before the nightly")
    p.add_argument("--skip", action="append", default=[], choices=list(CHECKS), help="skip a check")

    def run(a, cfg):
        logging.basicConfig(level=logging.INFO, format="%(message)s")
        res = preflight(cfg, {k: v for k, v in CHECKS.items() if k not in a.skip})
        return 0 if all(ok for ok, _ in res.values()) else 1
    p.set_defaults(func=run)
