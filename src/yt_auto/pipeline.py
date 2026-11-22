"""Runtime orchestration around the Notion "Content Pipeline" board.

  yt-auto nightly [--count N]   build videos (default_format: film or short) from Idea rows -> QA -> private YouTube upload (preview) ->
                                Needs Approval (+ phone push with the YouTube Studio link), then publish
  yt-auto publish               approved rows -> schedule the private upload for the next free peak slot
                                (videos.update, no re-upload); rejected -> stays private, row Rejected;
                                Scheduled rows whose time passed -> Live
  yt-auto stats                 refresh Views/Likes/retention for Scheduled + Live rows
  yt-auto research [--n 10]     researcher agent -> new Idea rows (deduped by title)
  yt-auto analyze               stats -> analyst agent -> rewrites the "What Works" page
  yt-auto ntfy-topic [--test]   print the phone-notification topic + how to subscribe

Status flow: Idea -> Scripted -> Rendered -> Needs Approval -> Scheduled -> Live   (or Rejected / Failed)

Preview: the render host can be an ephemeral CI runner, so the video can't wait on disk for approval.
After QA it is uploaded to YouTube as PRIVATE without publishAt (Video ID + YouTube URL set while the
row is still Needs Approval; preview it in YouTube Studio). Without YouTube configured the video stays
in the job dir (laptop) and, on GitHub Actions, is also copied to out/artifacts/ for the workflow to keep
as a 7-day run artifact (run URL in QA Notes). Approving a row that has no Video ID uploads the local
job video at publish time (laptop path).
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import logging
import os
import re
import shutil
import sys
import traceback
from datetime import date, datetime, time as dtime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from . import notify

log = logging.getLogger("yt_auto.pipeline")

DEFAULTS = {"timezone": "America/Toronto", "slots": ["12:00", "19:00"], "min_lead_hours": 1,
            "auto_approve": False, "shorts_per_night": 2}


def pcfg(cfg: dict) -> dict:
    return {**DEFAULTS, **(cfg.get("publish") or {})}


# ---------------------------------------------------------------- infra: logging + lock

class _Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, s):
        for st in self.streams:
            st.write(s)
            st.flush()
        return len(s)

    def flush(self):
        for st in self.streams:
            st.flush()

    def isatty(self):
        return False


@contextlib.contextmanager
def run_log(cfg: dict, name: str):
    """Log (and tee stdout/stderr) to out/logs/<name>-<date>.log."""
    d = cfg["_root"] / cfg["output_dir"] / "logs"
    d.mkdir(parents=True, exist_ok=True)
    f = open(d / f"{name}-{date.today():%Y-%m-%d}.log", "a", buffering=1)
    root = logging.getLogger()
    h = logging.StreamHandler(f)
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root.addHandler(h)
    root.setLevel(logging.INFO)
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = _Tee(old_out, f), _Tee(old_err, f)
    try:
        yield
    finally:
        sys.stdout, sys.stderr = old_out, old_err
        root.removeHandler(h)
        f.close()


class Locked(RuntimeError):
    pass


@contextlib.contextmanager
def pipeline_lock(cfg: dict):
    """Exclusive non-blocking lock shared by nightly and publish so runs can't overlap."""
    p = cfg["_root"] / cfg["output_dir"] / ".pipeline.lock"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Locked(f"another yt-auto run holds {p}") from None
        f.write(str(datetime.now()))
        f.flush()
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


# ---------------------------------------------------------------- helpers

def _client():
    from .notion import Notion
    return Notion()


def _optional(modname: str):
    """Lazy-import a sibling module built on another branch; None (with a log line) if missing."""
    import importlib
    try:
        return importlib.import_module(f"yt_auto.{modname}")
    except ImportError as e:
        log.warning("yt_auto.%s not available (%s)", modname, e)
        return None


def _norm(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()


def job_ref(cfg: dict, job: Path) -> str:
    job = Path(job).resolve()
    try:
        return str(job.relative_to(cfg["_root"].resolve()))
    except ValueError:
        return str(job)


def job_path(cfg: dict, ref: str) -> Path:
    p = Path(ref)
    return p if p.is_absolute() else cfg["_root"] / p


def youtube_url(video_id: str, fmt: str | None) -> str:
    return f"https://youtube.com/shorts/{video_id}" if fmt in (None, "short") else f"https://youtu.be/{video_id}"


LABELS = {"short": "Short", "film": "Film", "long": "Video"}


def default_format(cfg: dict) -> str:
    return cfg.get("default_format") or "short"


def builder_for(fmt: str):
    """Format -> build function (the format contract in YT-AUTO-ARCHITECTURE.md section 4)."""
    if fmt == "film":
        from .film import build_film
        return build_film
    from . import build_short
    return build_short


def per_night(cfg: dict) -> int:
    p = cfg.get("publish") or {}
    return int(p.get("videos_per_night") or p.get("shorts_per_night") or pcfg(cfg)["shorts_per_night"])


def studio_url(video_id: str) -> str:
    return f"https://studio.youtube.com/video/{video_id}/edit"


def ci_run_url() -> str | None:
    """Link to the current GitHub Actions run (None when not on Actions)."""
    e = os.environ
    if e.get("GITHUB_ACTIONS") == "true" and e.get("GITHUB_RUN_ID") and e.get("GITHUB_REPOSITORY"):
        return f"{e.get('GITHUB_SERVER_URL', 'https://github.com')}/{e['GITHUB_REPOSITORY']}/actions/runs/{e['GITHUB_RUN_ID']}"
    return None


def _youtube_ready():
    """The youtube module when it is importable and configured, else None."""
    yt = _optional("youtube")
    if yt is None:
        return None
    try:
        return yt if yt.is_configured() else None
    except Exception as e:
        log.warning("youtube.is_configured() failed: %s", e)
        return None


# ---------------------------------------------------------------- slot scheduling

def _as_dt(v, tz: ZoneInfo) -> datetime | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=tz)
    if isinstance(v, date):
        return datetime.combine(v, dtime(0), tz)
    return None


def next_slot(now: datetime, slots: list[str], tz: str | ZoneInfo, taken, min_lead_hours: float = 1,
              horizon_days: int = 120) -> datetime:
    """Earliest local peak slot >= now + min_lead that no other video occupies (one video per slot)."""
    tz = ZoneInfo(tz) if isinstance(tz, str) else tz
    now = now.astimezone(tz)
    earliest = now + timedelta(hours=min_lead_hours)
    busy = {t.astimezone(tz).replace(second=0, microsecond=0) for t in taken if t}
    times = sorted(dtime(*map(int, s.split(":"))) for s in slots)
    for d in range(horizon_days):
        day = now.date() + timedelta(days=d)
        for t in times:
            cand = datetime.combine(day, t, tz)
            if cand >= earliest and cand not in busy:
                return cand
    raise RuntimeError(f"no free publish slot in the next {horizon_days} days")


# ---------------------------------------------------------------- publish

def publish(cfg: dict, nc, now: datetime | None = None) -> dict:
    pc = pcfg(cfg)
    tz = ZoneInfo(pc["timezone"])
    now = now or datetime.now(tz)
    summary = {"rejected": 0, "scheduled": 0, "live": 0, "waiting": 0, "errors": 0}

    pending = nc.query("Needs Approval")
    rejected = [r for r in pending if r.get("Reject")]
    approved = [r for r in pending if r.get("Approve") and not r.get("Reject")]
    yt = _youtube_ready() if (approved or any(r.get("Video ID") for r in rejected)) else None

    for r in rejected:
        vid = r.get("Video ID")
        if vid:
            # never delete automatically: the private upload stays in Studio for the user to remove
            try:
                if yt is None:
                    raise RuntimeError("YouTube not configured")
                yt.keep_private(vid)
                log.info("rejected %r: video %s stays private on YouTube (delete it in Studio if unwanted)",
                         r.get("Title"), vid)
            except Exception as e:
                log.warning("rejected %r: could not confirm video %s is private: %s", r.get("Title"), vid, e)
        nc.update_row(r["_id"], {"Status": "Rejected"})   # Feedback left as the user wrote it
        log.info("rejected: %s", r.get("Title"))
        summary["rejected"] += 1

    scheduled = nc.query(["Scheduled", "Live"])
    if approved and yt is None:
        log.warning("YouTube upload not configured: leaving %d approved row(s) in Needs Approval", len(approved))
        summary["waiting"] = len(approved)
    elif approved:
        taken = [_as_dt(r.get("Publish At"), tz) for r in scheduled]
        for r in approved:
            title = r.get("Title")
            try:
                vid = r.get("Video ID")
                if not vid:   # laptop path / preview upload failed at night: upload the local render now
                    job = job_path(cfg, r.get("Job") or "")
                    if not r.get("Job") or not (job / "video.mp4").exists():
                        raise FileNotFoundError(
                            f"no YouTube preview upload and rendered video missing ({job / 'video.mp4'}); "
                            "if it was rendered on CI, download the run artifact and upload it by hand")
                    vid = yt.upload(job)
                slot = next_slot(now, pc["slots"], tz, taken, pc["min_lead_hours"]) if pc["slots"] else None
                yt.schedule(vid, slot)
                vals = {"Video ID": vid, "YouTube URL": youtube_url(vid, r.get("Format"))}
                if slot is None:   # no slots configured: public right away
                    vals.update({"Status": "Live", "Publish At": now})
                    summary["live"] += 1
                else:
                    taken.append(slot)
                    vals.update({"Status": "Scheduled", "Publish At": slot})
                    summary["scheduled"] += 1
                nc.update_row(r["_id"], vals)
                log.info("%s %r (%s) for %s", vals["Status"].lower(), title, vid, vals["Publish At"].isoformat())
            except Exception as e:
                log.error("publish failed for %r: %s", title, e)
                summary["errors"] += 1
                notify.send("yt-auto: publish failed", f"{title}: {e}"[:400], click=r.get("_url"),
                            tags=["warning"])

    for r in scheduled:
        at = _as_dt(r.get("Publish At"), tz)
        if r.get("Status") == "Scheduled" and at and at <= now:
            nc.update_row(r["_id"], {"Status": "Live"})
            log.info("live: %s", r.get("Title"))
            summary["live"] += 1
    log.info("publish: %s", summary)
    return summary


# ---------------------------------------------------------------- nightly

def _guidance(nc) -> str:
    try:
        return nc.read_page_text()
    except Exception as e:
        log.warning("could not read What Works page: %s", e)
        return ""


def _feedback(nc, limit: int = 10) -> list[str]:
    try:
        rows = nc.query("Rejected", newest_first=True)
    except Exception as e:
        log.warning("could not read rejection feedback: %s", e)
        return []
    return [f"{r.get('Title')}: {r['Feedback']}" for r in rows if (r.get("Feedback") or "").strip()][:limit]


def _qa(cfg: dict, job: Path) -> dict:
    agents = _optional("agents")
    if agents is None or not hasattr(agents, "qa_review"):
        return {"verdict": "warn", "notes": "QA agent unavailable; review manually."}
    res = agents.qa_review(cfg, job)
    v = res.get("verdict")
    return {"verdict": v if v in ("pass", "warn", "fail") else "warn", "notes": str(res.get("notes", ""))}


def preview(cfg: dict, job: Path) -> dict:
    """Make a passed render reviewable after this process exits. Returns
    {"video_id"?, "studio"?, "note"}: a private, unscheduled YouTube upload when possible; otherwise the
    file stays in the job dir and (on GitHub Actions) is copied to out/artifacts/ for the run artifact."""
    yt = _youtube_ready()
    err = None
    if yt is not None:
        try:
            vid = yt.upload(job)   # private, no publishAt; idempotent via job/upload.json
            return {"video_id": vid, "studio": studio_url(vid),
                    "note": f"Preview (private): {studio_url(vid)}"}
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            log.error("preview upload failed for %s: %s", job.name, err)
    run = ci_run_url()
    where = "YouTube not configured" if err is None else f"preview upload failed ({err[:300]})"
    if run:
        art = cfg["_root"] / cfg["output_dir"] / "artifacts"
        art.mkdir(parents=True, exist_ok=True)
        shutil.copy2(job / "video.mp4", art / f"{job.name}.mp4")
        return {"note": f"{where}: video kept 7 days as run artifact 'videos' -> {run}", "run": run}
    return {"note": f"{where}: video at {job / 'video.mp4'}"}


def _call_build(build, cfg, topic, job=None, **kw):
    """Pass only the keyword arguments `build` accepts (older/fake builders lack `past`)."""
    import inspect
    params = inspect.signature(build).parameters
    if not any(p.kind == p.VAR_KEYWORD for p in params.values()):
        kw = {k: v for k, v in kw.items() if k in params}
    return build(cfg, topic, job, **kw)


MAX_REQUEUES = 3   # a row that keeps failing transiently becomes Failed after this many nights


def _tags(row: dict) -> list[str]:
    return [t.strip() for t in (row.get("Alerts") or "").split(",") if t.strip()]


def _with_tag(row: dict, tag: str, drop_prefix: str | None = None) -> str:
    keep = [t for t in _tags(row) if not (drop_prefix and t.startswith(drop_prefix))]
    return ", ".join(dict.fromkeys([*keep, tag]))


def _requeues(row: dict) -> int:
    return max((int(t.split(":")[1]) for t in _tags(row) if re.fullmatch(r"requeue:\d+", t)), default=0)


def produce(cfg: dict, nc, row: dict, guidance: str, feedback: list[str], build=None,
            past: list[str] | None = None, recent: list[dict] | None = None, sleep=None) -> dict:
    """Build one Short for `row`: Scripted -> Rendered -> (private preview upload) -> Needs Approval | Failed.
    Transient errors (network, HF download, Claude overload...) are retried; if they persist the row goes
    back to Idea for the next night instead of Failed. Returns the row with "Status" and, on a build
    exception, "_error": "transient" | "bug"."""
    import time as _time

    from . import heal
    from .analytics import hook_pattern, script_text
    fmt = (row.get("Format") or default_format(cfg)).strip().lower()
    label = LABELS.get(fmt, "Video")
    if build is None:
        build = builder_for(fmt)
    topic = (row.get("Topic") or "").strip() or None
    if not topic and row.get("Source") != "auto":   # auto rows: let the script writer pick the topic
        topic = (row.get("Title") or "").strip() or None
    if topic and (row.get("Idea Notes") or "").strip():
        topic = f"{topic} (angle: {row['Idea Notes'].strip()})"
    rid = row["_id"]

    made = {}

    def on_script(sc, job):
        made["job"] = job
        vals = {"Status": "Scripted", "Title": sc["title"], "Job": job_ref(cfg, job), "Format": fmt}
        if sc.get("lines") and fmt == "film":
            vals.update({"Hook": sc["lines"][0].get("text", ""), "Script": script_text(sc)[:1900]})
        elif sc.get("lines"):
            duo = cfg.get("duo") or {}
            hook = sc["lines"][0].get("text", "")
            vals.update({"Hook": hook, "Script": script_text(sc)[:1900],
                         "Hook Pattern": hook_pattern(hook, tuple(x for x in (duo.get("asker"), duo.get("explainer")) if x))})
        nc.update_row(rid, vals)

    tries = int((cfg.get("heal") or {}).get("build_tries", 2))
    try:
        job = heal.retry(lambda: _call_build(build, cfg, topic, made.get("job"), guidance=guidance, feedback=feedback,
                                             on_script=on_script, past=past, recent=recent),
                         tries=tries, base=30, sleep=sleep or _time.sleep, what=f"build {topic or 'auto topic'}")
        meta = json.loads((job / "metadata.json").read_text())
        nc.update_row(rid, {"Status": "Rendered", "Job": job_ref(cfg, job),
                            "Duration (s)": meta.get("duration_s")})
        qa = _qa(cfg, job)
        ok = qa["verdict"] != "fail"
        vals = {"QA": qa["verdict"], "QA Notes": qa["notes"], "Status": "Needs Approval" if ok else "Failed"}
        pv = {}
        if ok:
            pv = preview(cfg, job)
            vals["QA Notes"] = f"{qa['notes']}\n\n{pv['note']}".strip()
            if pv.get("video_id"):
                vals["Video ID"] = pv["video_id"]
                vals["YouTube URL"] = youtube_url(pv["video_id"], fmt)
        if ok and pcfg(cfg)["auto_approve"]:   # pass or warn; only a QA fail still blocks a video
            vals["Approve"] = True
        nc.update_row(rid, vals)
        title = meta.get("title", row.get("Title"))
        if ok:
            auto = vals.get("Approve")
            notion = row.get("_url")
            msg = f"{title} - {meta.get('duration_s')}s, QA {qa['verdict']}"
            if auto:
                msg += "\nUploaded; goes public automatically at the next free slot."
            elif pv.get("studio"):
                msg += "\nTap to preview in YouTube Studio (private)."
            elif pv.get("run"):
                msg += "\nVideo is a 7-day artifact of the CI run (tap to open)."
            if not auto:
                msg += "\nTick Approve (or Reject + Feedback) in Notion."
            if notion:
                msg += f"\nNotion: {notion}"
            actions = [("Notion", notion)] if notion and (pv.get("studio") or pv.get("run")) else None
            notify.send(f"New {label} done" + (", auto-publishing" if auto else ", approve?"), msg,
                        click=pv.get("studio") or pv.get("run") or notion, tags=["clapper"], actions=actions)
        else:
            notify.send(f"{label} failed QA", f"{title}: {qa['notes']}"[:400], click=row.get("_url"), tags=["x"])
        log.info("%s -> %s (QA %s)", title, vals["Status"], qa["verdict"])
        return {**row, **vals}
    except Exception as e:
        tb = traceback.format_exc()
        log.error("build failed for %r:\n%s", topic, tb)
        n = _requeues(row) + 1
        transient = heal.is_transient(e) and n <= MAX_REQUEUES
        run = os.environ.get("GITHUB_RUN_ID")
        if transient:
            vals = {"Status": "Idea", "Alerts": _with_tag(row, f"requeue:{n}", "requeue:"),
                    "QA Notes": f"Transient failure #{n}, back to Idea for the next night: {type(e).__name__}: {e}"[:1900]}
        else:
            vals = {"Status": "Failed", "QA": "fail", "QA Notes": f"{type(e).__name__}: {e}\n\n{tb[-1500:]}",
                    "Alerts": _with_tag(row, f"run:{run}") if run else row.get("Alerts") or ""}
        try:
            nc.update_row(rid, vals)
        except Exception as e2:
            log.error("could not update the failed row: %s", e2)
        notify.send(f"{label} build hit a network hiccup, retrying tomorrow" if transient else f"{label} build failed",
                    f"{topic or 'auto topic'}: {e}"[:400], click=row.get("_url"), tags=["x"])
        return {**row, **vals, "_error": "transient" if transient else "bug"}


def _ensure_schema(nc) -> None:
    from . import analytics
    try:
        analytics.ensure_schema(nc)
    except Exception as e:
        log.warning("could not add analytics columns to Notion: %s", e)


def _cadence(cfg: dict, nc, configured: int) -> int:
    """Apply the cadence rule (analytics.cadence); ntfy once when it first kicks in."""
    from . import analytics
    try:
        rows = nc.query(["Scheduled", "Live"])
        now = datetime.now(ZoneInfo(pcfg(cfg)["timezone"]))
        n, why = analytics.cadence(rows, now, configured, analytics.acfg(cfg))
    except Exception as e:
        log.warning("cadence rule skipped: %s", e)
        return configured
    if why:
        log.info("cadence: %s", why)
        recent = [r for r in rows if analytics.parse_cps(r.get("Checkpoints")).get("7d")]
        if recent and not any("cadence" in _tags(r) for r in recent[-14:]):
            notify.send("yt-auto: slowing down to 1 Short a night", why, tags=["turtle"])
            newest = recent[-1]
            nc.update_row(newest["_id"], {"Alerts": _with_tag(newest, "cadence")})
    return n


def _recent_scripts(nc, n: int = 30) -> list[dict]:
    try:
        rows = nc.query(["Needs Approval", "Scheduled", "Live", "Rejected"])
    except Exception as e:
        log.warning("could not read recent scripts: %s", e)
        return []
    return [{"title": r.get("Title") or "", "text": r.get("Script") or ""} for r in rows if r.get("Title")][-n:]


class BuildsFailed(RuntimeError):
    """Nightly finished but builds failed: exit non-zero so the Actions run is red (and the doctor runs)."""


def nightly_status(results: list[dict]) -> str | None:
    """Why the nightly should exit non-zero, or None. Any bug-type build error counts; transient
    errors only when nothing at all got built."""
    if not results:
        return None
    bugs = [r for r in results if r.get("_error") == "bug"]
    ok = [r for r in results if r.get("Status") not in ("Failed", "Idea")]
    if bugs:
        return f"{len(bugs)} of {len(results)} build(s) failed with an error: " + "; ".join(
            str(r.get("Title") or r.get("Topic")) for r in bugs)
    if not ok:
        return f"all {len(results)} build(s) failed"
    return None


def nightly(cfg: dict, nc, count: int | None = None, build=None) -> list[dict]:
    _ensure_schema(nc)
    count = count or _cadence(cfg, nc, per_night(cfg))
    queue = nc.query("Idea")
    queue.sort(key=lambda r: r.get("Source") != "follow-up")   # winners' follow-ups first (stable sort)
    ideas = queue[:count]
    guidance, feedback = _guidance(nc), _feedback(nc)
    recent = _recent_scripts(nc)
    while len(ideas) < count:
        ideas.append(nc.create_row({"Title": "(auto topic, writing script...)", "Status": "Idea",
                                    "Source": "auto", "Format": default_format(cfg)}))
    try:   # titles already made: Notion is the memory on ephemeral runners (out/ starts empty there)
        past = [r["Title"] for r in nc.query(["Needs Approval", "Scheduled", "Live", "Rejected"]) if r.get("Title")]
    except Exception as e:
        log.warning("could not read past titles: %s", e)
        past = []
    results = [produce(cfg, nc, r, guidance, feedback, build, past, recent) for r in ideas]
    publish(cfg, nc)
    return results


# ---------------------------------------------------------------- weekly jobs

def stats(cfg: dict, nc, due_only: bool = False) -> dict:
    """Live analytics sweep (analytics.sweep): checkpoints, deep metrics, verdicts, follow-ups, alerts.
    due_only: the 30-min publish cron; only touches YouTube when a checkpoint is due or every ~6 h."""
    from . import analytics
    yt = _youtube_ready()
    if yt is None:
        log.warning("stats: YouTube not configured, skipping")
        return {"ran": False}
    return analytics.sweep(cfg, nc, yt, due_only=due_only)


def research(cfg: dict, nc, n: int = 10) -> int:
    agents = _optional("agents")
    if agents is None or not hasattr(agents, "research_ideas"):
        log.warning("research: agents module unavailable, nothing to do")
        return 0
    rows = nc.query()
    titles = [r.get("Title", "") for r in rows if r.get("Title")]
    seen = {_norm(t) for t in titles} | {_norm(r.get("Topic", "")) for r in rows if r.get("Topic")}
    made = 0
    for idea in agents.research_ideas(cfg, titles, n):
        title = (idea.get("title") or "").strip()
        if not title or _norm(title) in seen:
            continue
        seen.add(_norm(title))
        nc.create_row({"Title": title, "Topic": idea.get("topic") or title, "Idea Notes": idea.get("notes", ""),
                       "Status": "Idea", "Source": "researcher", "Format": default_format(cfg)})
        made += 1
    log.info("research: %d new idea(s)", made)
    return made


ANALYZE_FIELDS = ["Title", "Topic", "Format", "Source", "QA", "Duration (s)", "Publish At", "Views", "Likes",
                  "Avg View %", "Avg View (s)", "Stats Updated", "Views 1h", "Views 24h", "Views 72h", "Views 7d",
                  "Engaged Views", "Shares", "Subs Gained", "Comments", "Verdict", "Ratio 72h", "Hook",
                  "Hook Pattern", "Hook Check", "Series", "Script"]


def analyze(cfg: dict, nc) -> bool:
    rows = [r for r in nc.query(["Scheduled", "Live"]) if r.get("Views") is not None]
    if not rows:
        log.info("analyze: no rows with stats yet")
        return False
    agents = _optional("agents")
    if agents is None or not hasattr(agents, "analyze"):
        log.warning("analyze: agents module unavailable")
        return False
    from . import analytics
    clean = [{k: (v.isoformat() if isinstance(v, (date, datetime)) else v) for k, v in r.items()
              if k in ANALYZE_FIELDS} for r in rows]
    a = analytics.acfg(cfg)
    current, _ = analytics.split_board(_guidance(nc))
    board = analytics.scoreboard(sorted(rows, key=lambda r: analytics.published_at(r) or datetime.min.astimezone()), a)
    text = agents.analyze(cfg, clean, current, board)
    if not (text or "").strip():
        log.warning("analyze: empty result, What Works page left unchanged")
        return False
    nc.replace_page_text(analytics.merge_board(text, board))
    log.info("analyze: What Works page updated from %d row(s)", len(rows))
    return True


def requeue(cfg: dict, nc, run_id: str | None = None) -> int:
    """Failed rows (only those tagged by CI run `run_id`, if given) -> Idea. Used after a doctor fix."""
    n = 0
    for r in nc.query("Failed"):
        if run_id and f"run:{run_id}" not in _tags(r):
            continue
        nc.update_row(r["_id"], {"Status": "Idea", "QA": None,
                                 "QA Notes": f"Re-queued after a fix (run {run_id or 'manual'})."})
        n += 1
    log.info("requeue: %d row(s) back to Idea", n)
    print(n)
    return n


# ---------------------------------------------------------------- CLI

def _nightly_cli(cfg: dict, nc, count: int | None) -> list[dict]:
    results = nightly(cfg, nc, count)
    why = nightly_status(results)
    if why:
        raise BuildsFailed(why)
    return results


def _run(name: str, fn, locked: bool):
    def handler(args, cfg) -> int:
        with run_log(cfg, name):
            try:
                with (pipeline_lock(cfg) if locked else contextlib.nullcontext()):
                    nc = _client()
                    fn(args, cfg, nc)
                return 0
            except BuildsFailed as e:   # rows + pushes are already done; just make the run red
                log.error("%s: %s", name, e)
                return 1
            except Locked as e:
                log.info("%s skipped: %s", name, e)
                return 0
            except Exception as e:
                log.exception("%s failed: %s", name, e)
                notify.send(f"yt-auto {name} failed", str(e)[:400], tags=["rotating_light"])
                return 1
    return handler


def register(sub) -> None:
    p = sub.add_parser("nightly", help="build videos from Notion ideas -> QA -> Needs Approval, then publish")
    p.add_argument("--count", type=int, default=None, help="videos to build (default publish.videos_per_night)")
    p.set_defaults(func=_run("nightly", lambda a, c, nc: _nightly_cli(c, nc, a.count), locked=True))

    p = sub.add_parser("publish", help="upload approved rows, mark rejected, flip Scheduled -> Live")
    p.set_defaults(func=_run("publish", lambda a, c, nc: publish(c, nc), locked=True))

    p = sub.add_parser("stats", help="analytics sweep: checkpoints, deep metrics, verdicts, alerts")
    p.add_argument("--due", action="store_true", help="only if a checkpoint is due or the last sweep is ~6 h old")
    p.set_defaults(func=_run("stats", lambda a, c, nc: stats(c, nc, a.due), locked=False))

    p = sub.add_parser("requeue", help="Failed rows -> Idea (after a fix)")
    p.add_argument("--run", default=None, help="only rows failed by this GitHub Actions run id")
    p.set_defaults(func=_run("requeue", lambda a, c, nc: requeue(c, nc, a.run), locked=False))

    p = sub.add_parser("research", help="researcher agent -> new Idea rows")
    p.add_argument("--n", type=int, default=10)
    p.set_defaults(func=_run("research", lambda a, c, nc: research(c, nc, a.n), locked=False))

    p = sub.add_parser("analyze", help="analyst agent -> rewrite the What Works page")
    p.set_defaults(func=_run("analyze", lambda a, c, nc: analyze(c, nc), locked=False))

    p = sub.add_parser("ntfy-topic", help="print the ntfy topic for phone notifications")
    p.add_argument("--test", action="store_true", help="also send a test push")
    p.set_defaults(func=lambda a, c: notify.cmd_topic(a, c))
