"""Search optimisation for films, Shorts and compilations, driven by measurable signals.

Signals (all free / cheap):
  * YouTube search autocomplete (suggestqueries, ds=yt): what people actually type. A phrase that
    autocompletes has search demand; its rank and how many longer queries extend it is the score.
  * The channel's own "found via YouTube search" terms (YouTube Analytics, per video), fed back into the
    analyst + research prompts as the channel grows (analytics.sweep -> Notion "Search Terms").

What it changes (metadata only; never the film itself):
  * title subject: the writer's subject vs its search_phrases, the one with the most demand that still
    reads as a title ("The Taum Sauk Dam Failure" > "The Taum Sauk Reservoir Breach")
  * description: first sentence leads with the primary search phrase (YouTube shows ~150 chars before
    "more"); chapter timestamps (Google/YouTube "key moments"); the 3 most relevant hashtags first
  * tags: primary phrase + autocomplete expansions + the writer's tags, deduped, within YouTube's 500 chars
  * playlist: one themed playlist per film (playlists rank in search and lengthen sessions)

Network calls use a generic User-Agent and send only the search phrase.
"""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request

PLAYLISTS = {
    "hacks": "Hacks & Cyberattacks Explained",
    "space": "Space & Science Failures Explained",
    "engineering": "Engineering Disasters Explained",
    "crypto": "Codebreaking & Cryptography Explained",
    "bugs": "Famous Software Bugs Explained",
    "history": "Tech History Explained",
}
CHAPTER_MIN_S = 10          # YouTube needs >= 3 chapters, first at 0:00, each >= 10 s


def suggest(query: str, opener=None, timeout: float = 8) -> list[str]:
    url = "https://suggestqueries.google.com/complete/search?" + urllib.parse.urlencode(
        {"client": "firefox", "ds": "yt", "q": query})
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; seo-check)"})
    try:
        with (opener or urllib.request.build_opener()).open(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", "ignore"))
        return [s for s in data[1] if isinstance(s, str)]
    except Exception:  # noqa: BLE001 - no signal is fine; metadata falls back to the writer's
        return []


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def demand(phrase: str, sugg: list[str]) -> float:
    """0..1: does YouTube autocomplete this phrase, and how many longer searches extend it."""
    p = _norm(re.sub(r"^the ", "", phrase.strip(), flags=re.I))
    if not p or not sugg:
        return 0.0
    ns = [_norm(s) for s in sugg]
    exact = 1.0 if p in ns else 0.0
    extends = sum(1 for s in ns if s.startswith(p) and s != p)
    contains = sum(1 for s in ns if p in s)
    return round(0.5 * exact + 0.3 * min(1, extends / 5) + 0.2 * min(1, contains / 6), 3)


def keyword_plan(subject: str, phrases: list[str], fetch=suggest, pause: float = 0.3) -> dict:
    """Score the writer's subject and its search phrases; returns
    {"primary": best phrase, "subject": title subject to use, "scores": {...}, "related": [...]}"""
    cands = list(dict.fromkeys([subject, *phrases]))
    scores, related = {}, []
    for c in cands:
        q = re.sub(r"^the ", "", c.strip(), flags=re.I)
        sugg = fetch(q)
        scores[c] = demand(c, sugg)
        related += [s for s in sugg if _norm(s) != _norm(q)]
        time.sleep(pause)
    best = max(cands, key=lambda c: (scores[c], c == subject))
    # the title keeps a title-like subject: switch only to a phrase with clearly more demand, 1-6 words
    title_subject = subject
    stop = {"the", "a", "an", "of", "and", "in", "on", "to", "how", "why", "what"}
    shared = ({w for w in _norm(best).split() if w not in stop} & {w for w in _norm(subject).split() if w not in stop})
    if best != subject and scores[best] >= scores.get(subject, 0) + 0.2 and 1 <= len(best.split()) <= 6 \
            and len(shared) >= 2:   # same story, better-searched wording; never drift to a neighbouring topic
        title_subject = best if best[:1].isupper() else best.title()
        if subject.lower().startswith("the ") and not title_subject.lower().startswith("the "):
            title_subject = "The " + title_subject
    return {"primary": best, "subject": title_subject, "scores": scores,
            "related": list(dict.fromkeys(r for r in related if 2 <= len(r.split()) <= 7))[:12]}


def lead_with(summary: str, phrase: str) -> str:
    """First sentence must contain the primary search phrase (shown before 'more')."""
    s = " ".join(summary.split())
    if _norm(phrase) and _norm(phrase) in _norm(s[:160]):
        return s
    p = phrase.strip()
    return f"{p[:1].upper() + p[1:]}: {s}"


def _ts(sec: float) -> str:
    sec = int(sec)
    return f"{sec // 60}:{sec % 60:02d}"


def chapters(marks: list[tuple[float, str]], duration: float) -> list[tuple[str, str]]:
    """marks: (seconds, label) from the writer's chapter lines. Valid YouTube chapters or []."""
    out: list[tuple[float, str]] = []
    for t, label in sorted(marks):
        label = " ".join(str(label).split())[:60]
        if not label:
            continue
        t = 0.0 if not out else t
        if out and (t - out[-1][0] < CHAPTER_MIN_S or duration - t < CHAPTER_MIN_S):
            continue
        out.append((t, label))
    return [(_ts(t), l) for t, l in out] if len(out) >= 3 else []


def tags(primary: str, related: list[str], writer: list[str], budget: int = 480) -> list[str]:
    seen, out, used = set(), [], 0
    for t in [primary, *related[:8], *writer]:
        t = " ".join(str(t).split()).strip(" ,#")
        k = t.lower()
        cost = len(t) + (2 if " " in t else 0) + 1
        if not t or k in seen or used + cost > budget:
            continue
        seen.add(k)
        out.append(t)
        used += cost
    return out


# ---------------------------------------------------------------- playlists (YouTube Data API)

def ensure_playlist(yt, title: str, description: str = "") -> str:
    """Id of the channel's playlist with this title, created (public) if missing. ~1 + 50 quota units."""
    page = None
    while True:
        resp = yt.playlists().list(part="snippet", mine=True, maxResults=50, pageToken=page).execute()
        for p in resp.get("items", []):
            if p["snippet"]["title"] == title:
                return p["id"]
        page = resp.get("nextPageToken")
        if not page:
            break
    body = {"snippet": {"title": title, "description": description or f"{title}. True tech stories, explained in minutes.",
                        "defaultLanguage": "en"}, "status": {"privacyStatus": "public"}}
    return yt.playlists().insert(part="snippet,status", body=body).execute()["id"]


def search_terms(video_id: str, days: int = 90, n: int = 15) -> list[tuple[str, float]]:
    """The YouTube-search terms that brought viewers to a video, from YouTube Analytics (lags ~2 days)."""
    from datetime import date, timedelta
    from .youtube import _analytics, _with_retry
    resp = _with_retry(lambda: _analytics().reports().query(
        ids="channel==MINE", startDate=(date.today() - timedelta(days=days)).isoformat(),
        endDate=date.today().isoformat(), metrics="views", dimensions="insightTrafficSourceDetail",
        filters=f"video=={video_id};insightTrafficSourceType==YT_SEARCH", sort="-views", maxResults=n).execute())
    return [(r[0], float(r[1])) for r in resp.get("rows") or []]


def add_to_playlist(yt, playlist_id: str, video_id: str) -> None:
    yt.playlistItems().insert(part="snippet", body={"snippet": {
        "playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": video_id}}}).execute()
