"""YouTube upload + stats via YouTube Data API v3 and YouTube Analytics API v2.

One-time setup: docs/youtube-setup.md, then `yt-auto youtube-auth`.

Quota (verified 2026-11-19, developers.google.com/youtube/v3/determine_quota_cost):
videos.insert has its own bucket of 100 calls/day at 1 unit each; everything else
shares 10,000 units/day (videos.list = 1, channels.list = 1, thumbnails.set = 50).

Audit / private lock: from July 2020 until November 2, 2026, videos uploaded by
unverified API projects (no YouTube API compliance audit) were locked private.
The Data API revision history entry for 2026-11-02 removed that restriction. If
YouTube ever locks an upload anyway, the uploader still works: open YouTube
Studio and switch the video to Public by hand.
"""

from __future__ import annotations

import json
import os
import random
import re
import time
from datetime import date, datetime, timezone
from pathlib import Path

from .config import config_dir

CONFIG_DIR = config_dir()                      # YT_AUTO_CONFIG_DIR overrides
CLIENT_SECRET = CONFIG_DIR / "client_secret.json"
TOKEN = CONFIG_DIR / "youtube_token.json"
SCOPES = [
    "https://www.googleapis.com/auth/youtube",              # videos.update (schedule / keep private)
    "https://www.googleapis.com/auth/youtube.force-ssl",    # captions.insert (films upload their own SRT)
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]
# videos.update accepts any of these; youtube.upload alone is NOT enough (tokens made before
# 2026-11-19 only had upload/readonly: rerun `yt-auto youtube-auth`).
MANAGE_SCOPES = ("https://www.googleapis.com/auth/youtube", "https://www.googleapis.com/auth/youtube.force-ssl",
                 "https://www.googleapis.com/auth/youtubepartner")
# status properties videos.update can set; any other omitted one is cleared by the API
MUTABLE_STATUS = ("embeddable", "license", "privacyStatus", "publicStatsViewable", "publishAt",
                  "selfDeclaredMadeForKids", "containsSyntheticMedia")

CATEGORY_ID = "28"            # Science & Technology
TITLE_MAX = 100               # characters
DESCRIPTION_MAX_BYTES = 5000
TAGS_MAX = 500                # characters, commas included; tags with spaces count their quotes
CHUNK = 8 * 1024 * 1024       # resumable chunk size (multiple of 256 KiB)
MAX_RETRIES = 10
RETRIABLE_STATUS = {500, 502, 503, 504}
# thumbnails.set gained Shorts support on 2026-11-03, but the Shorts pipeline makes no
# thumbnail and YouTube picks a frame for the Shorts feed anyway; keep Shorts frame-only.
THUMBNAIL_FOR_SHORTS = False


# ---------------------------------------------------------------- auth

def is_configured() -> bool:
    return CLIENT_SECRET.is_file() and TOKEN.is_file()


def _save_token(creds) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN.write_text(creds.to_json())
    os.chmod(TOKEN, 0o600)


def _credentials(manage: bool = False):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    if not is_configured():
        raise RuntimeError(f"YouTube not configured: need {CLIENT_SECRET} and {TOKEN} "
                           "(see docs/youtube-setup.md, then run `yt-auto youtube-auth`)")
    # scopes=None: refresh with exactly what the token was granted (asking for more fails the refresh)
    creds = Credentials.from_authorized_user_file(str(TOKEN))
    if manage and not set(creds.scopes or ()) & set(MANAGE_SCOPES):
        raise RuntimeError("YouTube token lacks the 'youtube' scope needed to schedule/update videos; "
                           "rerun `yt-auto youtube-auth` (and update the YT_TOKEN_JSON secret on CI)")
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            _save_token(creds)
        else:
            raise RuntimeError("YouTube token invalid; run `yt-auto youtube-auth` again")
    return creds


def authorize() -> None:
    """Browser login once; stores a refreshable token."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not CLIENT_SECRET.is_file():
        raise SystemExit(f"missing {CLIENT_SECRET} (see docs/youtube-setup.md)")
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
    # access_type=offline + prompt=consent guarantees a refresh_token on every login
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    _save_token(creds)
    print(f"saved token to {TOKEN}")


def _youtube(manage: bool = False):
    from googleapiclient.discovery import build
    return build("youtube", "v3", credentials=_credentials(manage), cache_discovery=False)


def _analytics():
    from googleapiclient.discovery import build
    return build("youtubeAnalytics", "v2", credentials=_credentials(), cache_discovery=False)


# ---------------------------------------------------------------- request body

def _clean(s: str) -> str:
    return s.replace("<", "").replace(">", "")       # API rejects angle brackets


def _tag_cost(tag: str) -> int:
    return len(tag) + (2 if " " in tag else 0)


def trim_tags(tags: list[str], budget: int = TAGS_MAX) -> list[str]:
    """Keep tags in order until the 500-char budget (commas + quotes counted) is hit."""
    out, used, seen = [], 0, set()
    for t in tags:
        t = _clean(str(t)).replace(",", " ").strip()
        if not t or t.lower() in seen:
            continue
        cost = _tag_cost(t) + (1 if out else 0)
        if used + cost > budget:
            continue                                  # a shorter later tag may still fit
        out.append(t)
        seen.add(t.lower())
        used += cost
    return out


def format_publish_at(dt: datetime) -> str:
    """RFC3339 UTC. Naive datetimes are taken as local time."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _truncate_bytes(s: str, limit: int) -> str:
    b = s.encode()
    return s if len(b) <= limit else b[:limit].decode(errors="ignore")


def build_body(meta: dict, publish_at: datetime | None) -> dict:
    title = _clean(meta["title"]).strip()
    if len(title) > TITLE_MAX:
        title = title[:TITLE_MAX - 1].rstrip() + "…"
    status = {
        "privacyStatus": "private",
        "selfDeclaredMadeForKids": False,
        "containsSyntheticMedia": True,  # AI-generated voices: disclose A/S content
    }
    if publish_at is not None:
        status["publishAt"] = format_publish_at(publish_at)
    return {
        "snippet": {
            "title": title,
            "description": _truncate_bytes(_clean(meta.get("description", "")), DESCRIPTION_MAX_BYTES),
            "tags": trim_tags(meta.get("tags") or []),
            "categoryId": CATEGORY_ID,
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": status,
    }


# ---------------------------------------------------------------- upload

def _retriable(exc: Exception) -> bool:
    from googleapiclient.errors import HttpError
    import httplib2

    if isinstance(exc, HttpError):
        return exc.resp.status in RETRIABLE_STATUS
    return isinstance(exc, (httplib2.HttpLib2Error, ConnectionError, TimeoutError, OSError))


def _execute_resumable(request, sleep=time.sleep) -> dict:
    """Drive a resumable upload; exponential backoff on 5xx / connection errors."""
    response, retry = None, 0
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                print(f"  upload {status.progress() * 100:.0f}%", flush=True)
            retry = 0
        except Exception as e:  # noqa: BLE001 - filtered by _retriable
            if not _retriable(e):
                raise
            retry += 1
            if retry > MAX_RETRIES:
                raise
            wait = random.random() * 2 ** retry
            print(f"  retriable error ({e}); retry {retry}/{MAX_RETRIES} in {wait:.1f}s", flush=True)
            sleep(wait)
    if "id" not in response:
        raise RuntimeError(f"unexpected upload response: {response}")
    return response


def _with_retry(fn, sleep=time.sleep):
    for retry in range(MAX_RETRIES + 1):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            if not _retriable(e) or retry == MAX_RETRIES:
                raise
            sleep(random.random() * 2 ** (retry + 1))


def studio_url(video_id: str) -> str:
    return f"https://studio.youtube.com/video/{video_id}/edit"


def upload(job: Path, publish_at: datetime | None = None) -> str:
    """Upload job/video.mp4 as a private video (scheduled when publish_at is given); returns the id.
    Idempotent: job/upload.json records the id and a second call returns it without uploading."""
    from googleapiclient.http import MediaFileUpload

    job = Path(job)
    record = job / "upload.json"
    if record.exists():
        return json.loads(record.read_text())["video_id"]

    meta = json.loads((job / "metadata.json").read_text())
    body = build_body(meta, publish_at)
    yt = _youtube()
    media = MediaFileUpload(str(job / "video.mp4"), mimetype="video/mp4", chunksize=CHUNK, resumable=True)
    request = yt.videos().insert(part="snippet,status", body=body, media_body=media,
                                 notifySubscribers=True)
    video_id = _execute_resumable(request)["id"]

    # write the record before the thumbnail so a thumbnail failure never causes a re-upload
    record.write_text(json.dumps({
        "video_id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "publish_at": body["status"].get("publishAt"),
    }, indent=2))

    thumb = job / "thumbnail.jpg"
    if thumb.is_file() and (meta.get("format") != "short" or THUMBNAIL_FOR_SHORTS):
        try:
            _with_retry(lambda: yt.thumbnails().set(
                videoId=video_id, media_body=MediaFileUpload(str(thumb), mimetype="image/jpeg")).execute())
        except Exception as e:  # noqa: BLE001 - custom thumbnails need a verified (phone) channel
            print(f"  thumbnail not set: {e}", flush=True)
    if meta.get("playlist"):   # themed playlist (seo.PLAYLISTS): ranks in search, lengthens sessions (~100 units)
        try:
            from . import seo
            seo.add_to_playlist(yt, seo.ensure_playlist(yt, meta["playlist"]), video_id)
        except Exception as e:  # noqa: BLE001
            print(f"  playlist not set: {e}", flush=True)
    srt = job / "captions.srt"
    if srt.is_file() and meta.get("format") == "film":   # exact captions from the script (~400 quota units)
        try:
            _with_retry(lambda: yt.captions().insert(
                part="snippet", body={"snippet": {"videoId": video_id, "language": "en", "name": "English",
                                                  "isDraft": False}},
                media_body=MediaFileUpload(str(srt), mimetype="application/octet-stream")).execute())
        except Exception as e:  # noqa: BLE001 - needs the youtube.force-ssl scope; YouTube auto-captions otherwise
            print(f"  captions not uploaded: {e}", flush=True)
    return video_id


# ---------------------------------------------------------------- update an uploaded video

def status_body(current: dict, publish_at: str | None, privacy: str) -> dict:
    """Full `status` for videos.update: keeps current mutable values (omitted ones would be cleared)."""
    st = {k: current[k] for k in MUTABLE_STATUS if k in current and k != "publishAt"}
    st["privacyStatus"] = privacy
    if publish_at:
        st["publishAt"] = publish_at
    st.setdefault("selfDeclaredMadeForKids", False)
    st.setdefault("containsSyntheticMedia", True)
    return st


def _get_status(yt, video_id: str) -> dict:
    items = _with_retry(lambda: yt.videos().list(part="status", id=video_id).execute()).get("items") or []
    if not items:
        raise RuntimeError(f"video {video_id} not found on the channel (deleted?)")
    return items[0].get("status", {})


def _set_status(yt, video_id: str, status: dict) -> dict:
    resp = _with_retry(lambda: yt.videos().update(part="status", body={"id": video_id, "status": status})
                       .execute())
    return resp.get("status", status)


def schedule(video_id: str, publish_at: datetime | None, now: datetime | None = None) -> dict:
    """Make an already-uploaded private video go public at publish_at (YouTube flips it), or right
    away when publish_at is None / not in the future. No re-upload. Returns the new status.
    A video that is already public is left alone."""
    now = now or datetime.now(timezone.utc)
    yt = _youtube(manage=True)
    cur = _get_status(yt, video_id)
    if cur.get("privacyStatus") == "public":
        return cur
    if publish_at is not None and publish_at > now:
        st = status_body(cur, format_publish_at(publish_at), "private")   # publishAt requires private
    else:
        st = status_body(cur, None, "public")
    return _set_status(yt, video_id, st)


def keep_private(video_id: str) -> dict:
    """Rejected video: make sure it stays private (drop any publishAt). Never deletes anything."""
    yt = _youtube(manage=True)
    cur = _get_status(yt, video_id)
    if cur.get("privacyStatus") == "private" and not cur.get("publishAt"):
        return cur                                       # already private, unscheduled: no write
    return _set_status(yt, video_id, status_body(cur, None, "private"))


# ---------------------------------------------------------------- stats

def _chunks(xs: list, n: int):
    for i in range(0, len(xs), n):
        yield xs[i:i + n]


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def fetch_stats(video_ids: list[str]) -> dict[str, dict]:
    """{id: {views, likes, avg_view_pct, avg_view_s}}; None where unknown (Analytics lags ~2 days)."""
    ids = list(dict.fromkeys(v for v in video_ids if v))
    out = {v: {"views": None, "likes": None, "avg_view_pct": None, "avg_view_s": None} for v in ids}
    if not ids:
        return out

    try:
        yt = _youtube()
        for batch in _chunks(ids, 50):
            resp = _with_retry(lambda: yt.videos().list(part="statistics", id=",".join(batch),
                                                        maxResults=50).execute())
            for item in resp.get("items", []):
                if item.get("id") in out:
                    s = item.get("statistics", {})
                    out[item["id"]]["views"] = _int(s.get("viewCount"))
                    out[item["id"]]["likes"] = _int(s.get("likeCount"))
    except Exception as e:  # noqa: BLE001 - stats are best-effort
        print(f"  youtube stats unavailable: {e}", flush=True)

    try:
        an = _analytics()
        for batch in _chunks(ids, 200):
            try:
                resp = _analytics_query(an, filters="video==" + ",".join(batch), max_results=len(batch))
            except Exception as e:  # noqa: BLE001
                # "top videos" reports officially only require sort+maxResults; if the
                # video== filter is ever rejected, fall back to the channel's top 200.
                from googleapiclient.errors import HttpError
                if not (isinstance(e, HttpError) and e.resp.status == 400):
                    raise
                resp = _analytics_query(an, filters=None, max_results=200)
            _merge_analytics(out, resp)
    except Exception as e:  # noqa: BLE001
        print(f"  youtube analytics unavailable: {e}", flush=True)
    return out


def parse_live_item(item: dict) -> dict:
    s, st, cd = item.get("statistics", {}), item.get("status", {}), item.get("contentDetails", {})
    return {
        "found": True,
        "views": _int(s.get("viewCount")), "likes": _int(s.get("likeCount")),
        "comments": _int(s.get("commentCount")),
        "privacy": st.get("privacyStatus"), "upload_status": st.get("uploadStatus"),
        "rejection_reason": st.get("rejectionReason"), "failure_reason": st.get("failureReason"),
        "blocked": list((cd.get("regionRestriction") or {}).get("blocked") or []),
        "age_restricted": (cd.get("contentRating") or {}).get("ytRating") == "ytAgeRestricted",
        "published_at": item.get("snippet", {}).get("publishedAt"),
    }


def fetch_live(video_ids: list[str]) -> dict[str, dict]:
    """Statistics + status + policy signals, 50 ids per videos.list call (1 quota unit each).
    Ids missing from the response map to {"found": False} (removed / deleted)."""
    ids = list(dict.fromkeys(v for v in video_ids if v))
    out = {v: {"found": False} for v in ids}
    yt = _youtube()
    for batch in _chunks(ids, 50):
        resp = _with_retry(lambda: yt.videos().list(part="statistics,status,contentDetails,snippet",
                                                    id=",".join(batch), maxResults=50).execute())
        for item in resp.get("items", []):
            if item.get("id") in out:
                out[item["id"]] = parse_live_item(item)
    return out


DEEP_METRICS = ["views", "engagedViews", "averageViewDuration", "averageViewPercentage", "shares",
                "subscribersGained"]
_DEEP_KEYS = {"views": "views", "engagedViews": "engaged_views", "averageViewDuration": "avg_view_s",
              "averageViewPercentage": "avg_view_pct", "shares": "shares", "subscribersGained": "subs_gained"}


def parse_deep(resp: dict) -> dict[str, dict]:
    cols = [h["name"] for h in resp.get("columnHeaders", [])]
    out = {}
    for row in resp.get("rows") or []:
        r = dict(zip(cols, row))
        if r.get("video"):
            out[r["video"]] = {_DEEP_KEYS[k]: (float(v) if v is not None else None)
                               for k, v in r.items() if k in _DEEP_KEYS}
    return out


def fetch_deep(video_ids: list[str]) -> dict[str, dict]:
    """YouTube Analytics v2 lifetime metrics per video (lags 48-72 h). If the API rejects
    engagedViews for this report, retries without it."""
    ids = list(dict.fromkeys(v for v in video_ids if v))
    if not ids:
        return {}
    from googleapiclient.errors import HttpError
    an, out = _analytics(), {}
    for batch in _chunks(ids, 200):
        metrics = list(DEEP_METRICS)
        while True:
            try:
                resp = _analytics_query(an, "video==" + ",".join(batch), len(batch), ",".join(metrics))
                break
            except HttpError as e:
                if e.resp.status == 400 and "engagedViews" in metrics:
                    metrics.remove("engagedViews")
                    continue
                raise
        out.update(parse_deep(resp))
    return out


def _analytics_query(an, filters: str | None, max_results: int,
                     metrics: str = "views,averageViewDuration,averageViewPercentage") -> dict:
    kw = dict(
        ids="channel==MINE",
        startDate="2005-02-14",
        endDate=date.today().isoformat(),
        metrics=metrics,
        dimensions="video",
        sort="-views",            # top-videos reports require a descending views/minutes sort
        maxResults=max_results,   # <= 200
    )
    if filters:
        kw["filters"] = filters
    return _with_retry(lambda: an.reports().query(**kw).execute())


def _merge_analytics(out: dict, resp: dict) -> None:
    cols = [h["name"] for h in resp.get("columnHeaders", [])]
    for row in resp.get("rows") or []:
        r = dict(zip(cols, row))
        vid = r.get("video")
        if vid not in out:
            continue
        if r.get("averageViewPercentage") is not None:
            out[vid]["avg_view_pct"] = float(r["averageViewPercentage"])
        if r.get("averageViewDuration") is not None:
            out[vid]["avg_view_s"] = float(r["averageViewDuration"])


# ---------------------------------------------------------------- CLI

def register(subparsers) -> None:
    subparsers.add_parser("youtube-auth", help="one-time browser login for YouTube upload/analytics")
    subparsers.add_parser("youtube-check", help="print the authorized YouTube channel")


def run(cmd: str) -> bool:
    """Handle youtube-* subcommands; returns False if cmd isn't ours."""
    if cmd == "youtube-auth":
        authorize()
        cmd = "youtube-check"
    if cmd == "youtube-check":
        try:
            svc = _youtube()
        except RuntimeError as e:
            raise SystemExit(str(e))
        resp = svc.channels().list(part="snippet,statistics", mine=True).execute()
        items = resp.get("items") or []
        if not items:
            raise SystemExit("authorized, but this Google account has no YouTube channel")
        ch = items[0]
        subs = ch.get("statistics", {}).get("subscriberCount", "?")
        print(f"{ch['snippet']['title']}  (id {ch['id']}, {subs} subscribers)")
        return True
    return False
