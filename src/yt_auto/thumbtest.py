"""Hands-off thumbnail A/B/C test for films and compilations, with the official YouTube APIs only.

YouTube Studio's own "Test & Compare" has no API, and driving Studio with a stored login from a cloud
runner would put the channel at risk, so this does the same job by ROTATION:

  day 0..5 after publish (YouTube's day = Pacific time):  A, B, C, A, B, C   (thumbnails.set, 50 units each)
  day 9 (reports lag ~2-3 days):  score each variant over its days, set the winner for good, push a summary

Score = thumbnail click-through rate from the YouTube Reporting API "reach" report when that API is
enabled for the project (impressions + CTR per video per day), else views per day from the Analytics API
(noisier: day-of-week and age effects, mitigated by showing every variant twice in alternating order).

State lives in the Notion column "Thumb Test" (JSON), so ephemeral CI runners can carry it on.
Thumbnail files: the local job dir, else the GitHub release `film-<slug>` (cuts.persist_film).
"""

from __future__ import annotations

import csv
import io
import json
import logging
import subprocess
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from . import notify

log = logging.getLogger("yt_auto.thumbtest")

PT = ZoneInfo("America/Los_Angeles")   # YouTube Analytics days are Pacific time
ORDER = ["a", "b", "c", "a", "b", "c"]
FILES = {"a": "thumbnail.jpg", "b": "thumbnail_b.jpg", "c": "thumbnail_c.jpg"}
EVAL_AFTER_DAYS = 9
COLUMN = "Thumb Test"
REACH_TYPE_HINTS = ("channel_reach_basic", "channel_reach")


def variant_for(day: int) -> str | None:
    return ORDER[day] if 0 <= day < len(ORDER) else None


def plan_day(published: datetime, now: datetime) -> int:
    return (now.astimezone(PT).date() - published.astimezone(PT).date()).days


def score(per_day: dict[str, float], start: date) -> dict[str, float]:
    """per_day: {"YYYY-MM-DD": value}; averages each variant over the days it was live."""
    sums: dict[str, list[float]] = {}
    for i, v in enumerate(ORDER):
        d = (start + timedelta(days=i)).isoformat()
        if d in per_day:
            sums.setdefault(v, []).append(per_day[d])
    return {v: sum(x) / len(x) for v, x in sums.items() if x}


def pick_winner(scores: dict[str, float], min_lift: float = 0.05) -> str:
    """Best variant; A (the circled-word default) keeps the slot unless another beats it by > min_lift."""
    if not scores:
        return "a"
    best = max(scores, key=scores.get)
    base = scores.get("a")
    if best != "a" and base and scores[best] < base * (1 + min_lift):
        return "a"
    return best


# ---------------------------------------------------------------- data sources

def _reporting():
    from googleapiclient.discovery import build
    from .youtube import _credentials
    return build("youtubereporting", "v1", credentials=_credentials(), cache_discovery=False)


def reach_job(rp) -> str | None:
    """The id of our Reporting API job for the reach report, creating it once. None if the API is off."""
    try:
        jobs = rp.jobs().list().execute().get("jobs", [])
        types = [t["id"] for t in rp.reportTypes().list().execute().get("reportTypes", [])]
    except Exception as e:  # noqa: BLE001 - API disabled for the project, etc.
        log.info("thumbtest: Reporting API unavailable (%s); using views per day", str(e)[:120])
        return None
    rtype = next((t for h in REACH_TYPE_HINTS for t in types if t.startswith(h)), None)
    if not rtype:
        return None
    for j in jobs:
        if j.get("reportTypeId") == rtype:
            return j["id"]
    job = rp.jobs().create(body={"reportTypeId": rtype, "name": "yt-auto thumbnail tests"}).execute()
    log.info("thumbtest: created Reporting API job %s (%s); first data in ~2 days", job["id"], rtype)
    return job["id"]


def ctr_by_day(rp, job_id: str, video_id: str, since: date) -> dict[str, float]:
    """{date: thumbnail CTR} for one video from the reach report CSVs."""
    from googleapiclient.http import MediaIoBaseDownload
    out: dict[str, tuple[float, float]] = {}
    created_after = datetime.combine(since, datetime.min.time(), PT).isoformat()
    reports = rp.jobs().reports().list(jobId=job_id, createdAfter=created_after).execute().get("reports", [])
    for rep in reports:
        buf = io.BytesIO()
        dl = MediaIoBaseDownload(buf, rp.media().download(resourceName=rep["downloadUrl"].split("/media/")[-1]))
        done = False
        while not done:
            _, done = dl.next_chunk()
        for row in csv.DictReader(io.StringIO(buf.getvalue().decode())):
            if row.get("video_id") != video_id:
                continue
            imp = float(row.get("video_thumbnail_impressions") or 0)
            ctr = float(row.get("video_thumbnail_impressions_ctr") or 0)
            d = f"{row['date'][:4]}-{row['date'][4:6]}-{row['date'][6:8]}"
            a, b = out.get(d, (0.0, 0.0))
            out[d] = (a + imp, b + imp * ctr)
    return {d: (c / i if i else 0.0) for d, (i, c) in out.items() if i >= 20}   # ignore near-empty days


def views_by_day(video_id: str, start: date, end: date) -> dict[str, float]:
    from .youtube import _analytics, _with_retry
    resp = _with_retry(lambda: _analytics().reports().query(
        ids="channel==MINE", startDate=start.isoformat(), endDate=end.isoformat(), metrics="views",
        dimensions="day", filters=f"video=={video_id}").execute())
    return {r[0]: float(r[1]) for r in resp.get("rows") or []}


# ---------------------------------------------------------------- thumbnails on disk

def thumb_file(cfg: dict, row: dict, variant: str, tmp: Path) -> Path | None:
    from .pipeline import job_path
    job = job_path(cfg, row.get("Job") or "") if row.get("Job") else None
    if job and (job / FILES[variant]).exists():
        return job / FILES[variant]
    slug = Path(row.get("Job") or "").name
    slug = slug.split("-", 1)[-1].rsplit("-film", 1)[0] if slug else ""
    if not slug:
        return None
    r = subprocess.run(["gh", "release", "download", f"film-{slug}", "-p", FILES[variant], "-D", str(tmp), "--clobber"],
                       cwd=cfg["_root"], capture_output=True, text=True)
    p = tmp / FILES[variant]
    return p if r.returncode == 0 and p.exists() else None


def set_thumb(yt_mod, video_id: str, path: Path) -> None:
    from googleapiclient.http import MediaFileUpload
    yt = yt_mod._youtube()
    yt_mod._with_retry(lambda: yt.thumbnails().set(
        videoId=video_id, media_body=MediaFileUpload(str(path), mimetype="image/jpeg")).execute())


# ---------------------------------------------------------------- the tick (runs with every publish/stats pass)

def tick(cfg: dict, nc, yt_mod, now: datetime | None = None) -> dict:
    from .analytics import published_at
    now = now or datetime.now(PT)
    done = {"rotated": 0, "decided": 0}
    rows = [r for r in nc.query("Live") if r.get("Video ID") and r.get("Format") in ("film", "compilation")]
    rp, job_id = None, None
    for r in rows:
        st = json.loads(r.get(COLUMN) or "{}")
        if st.get("winner"):
            continue
        pub = published_at(r)
        if pub is None:
            continue
        day = plan_day(pub, now)
        with tempfile.TemporaryDirectory() as td:
            want = variant_for(day)
            if want and st.get("current") != want:
                f = thumb_file(cfg, r, want, Path(td))
                if f is None:   # no B/C on disk or in the release: nothing to test
                    st.update({"winner": "a", "note": "variants unavailable"})
                    nc.update_row(r["_id"], {COLUMN: json.dumps(st)})
                    continue
                set_thumb(yt_mod, r["Video ID"], f)
                st.update({"current": want, "start": st.get("start") or pub.astimezone(PT).date().isoformat()})
                nc.update_row(r["_id"], {COLUMN: json.dumps(st)})
                done["rotated"] += 1
                log.info("thumbtest: %r -> thumbnail %s (day %d)", r.get("Title"), want.upper(), day)
            elif day >= EVAL_AFTER_DAYS:
                start = date.fromisoformat(st.get("start") or pub.astimezone(PT).date().isoformat())
                if rp is None:
                    try:
                        rp = _reporting()
                        job_id = reach_job(rp)
                    except Exception:  # noqa: BLE001
                        job_id = None
                metric, per_day = "views/day", {}
                if job_id:
                    try:
                        per_day = ctr_by_day(rp, job_id, r["Video ID"], start)
                        metric = "thumbnail CTR"
                    except Exception as e:  # noqa: BLE001
                        log.warning("thumbtest: reach report failed: %s", e)
                if not per_day:
                    metric = "views/day"
                    per_day = views_by_day(r["Video ID"], start, start + timedelta(days=len(ORDER) - 1))
                scores = score(per_day, start)
                win = pick_winner(scores)
                f = thumb_file(cfg, r, win, Path(td))
                if f is not None and st.get("current") != win:
                    set_thumb(yt_mod, r["Video ID"], f)
                st.update({"winner": win, "current": win, "metric": metric,
                           "scores": {k: round(v, 4) for k, v in scores.items()}})
                nc.update_row(r["_id"], {COLUMN: json.dumps(st)})
                done["decided"] += 1
                notify.send("Thumbnail test finished",
                            f"{r.get('Title')}: {win.upper()} wins on {metric} "
                            + ", ".join(f"{k.upper()} {v:.3g}" for k, v in sorted(scores.items())),
                            click=r.get("YouTube URL"), tags=["frame_with_picture"])
    if rp is None and rows:   # create the reach job early so data exists by evaluation time
        try:
            reach_job(_reporting())
        except Exception:  # noqa: BLE001
            pass
    return done
