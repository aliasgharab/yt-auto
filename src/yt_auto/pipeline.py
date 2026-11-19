"""Runtime orchestration around the Notion "Content Pipeline" board.

  yt-auto nightly [--count N]   build Shorts from Idea rows -> QA -> Needs Approval (+ phone push), then publish
  yt-auto publish               approved rows -> YouTube (scheduled at next free peak slot); rejected -> Rejected;
                                Scheduled rows whose time passed -> Live
  yt-auto stats                 refresh Views/Likes/retention for Scheduled + Live rows
  yt-auto research [--n 10]     researcher agent -> new Idea rows (deduped by title)
  yt-auto analyze               stats -> analyst agent -> rewrites the "What Works" page
  yt-auto ntfy-topic [--test]   print the phone-notification topic + how to subscribe

Status flow: Idea -> Scripted -> Rendered -> Needs Approval -> Scheduled -> Live   (or Rejected / Failed)
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import logging
import re
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
    return f"https://youtube.com/shorts/{video_id}" if fmt != "long" else f"https://youtu.be/{video_id}"


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
    approved = []
    for r in pending:
        if r.get("Reject"):
            nc.update_row(r["_id"], {"Status": "Rejected"})   # Feedback left as the user wrote it
            log.info("rejected: %s", r.get("Title"))
            summary["rejected"] += 1
        elif r.get("Approve"):
            approved.append(r)

    scheduled = nc.query(["Scheduled", "Live"])
    if approved:
        yt = _optional("youtube")
        ok = False
        if yt is not None:
            try:
                ok = bool(yt.is_configured())
            except Exception as e:
                log.warning("youtube.is_configured() failed: %s", e)
        if not ok:
            log.warning("YouTube upload not configured: leaving %d approved row(s) in Needs Approval", len(approved))
            summary["waiting"] = len(approved)
        else:
            taken = [_as_dt(r.get("Publish At"), tz) for r in scheduled]
            for r in approved:
                title = r.get("Title")
                try:
                    job = job_path(cfg, r.get("Job") or "")
                    if not r.get("Job") or not (job / "video.mp4").exists():
                        raise FileNotFoundError(f"rendered video missing: {job / 'video.mp4'}")
                    slot = next_slot(now, pc["slots"], tz, taken, pc["min_lead_hours"])
                    vid = yt.upload(job, slot)
                    taken.append(slot)
                    nc.update_row(r["_id"], {"Status": "Scheduled", "Video ID": vid, "Publish At": slot,
                                             "YouTube URL": youtube_url(vid, r.get("Format"))})
                    log.info("scheduled %r as %s for %s", title, vid, slot.isoformat())
                    summary["scheduled"] += 1
                except Exception as e:
                    log.error("upload failed for %r: %s", title, e)
                    summary["errors"] += 1
                    notify.send("yt-auto: upload failed", f"{title}: {e}"[:400], click=r.get("_url"),
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


def produce(cfg: dict, nc, row: dict, guidance: str, feedback: list[str], build=None) -> dict:
    """Build one Short for `row`, moving it through Scripted -> Rendered -> Needs Approval | Failed."""
    if build is None:
        from . import build_short as build
    topic = (row.get("Topic") or "").strip() or None
    if not topic and row.get("Source") != "auto":   # auto rows: let the script writer pick the topic
        topic = (row.get("Title") or "").strip() or None
    if topic and (row.get("Idea Notes") or "").strip():
        topic = f"{topic} (angle: {row['Idea Notes'].strip()})"
    rid = row["_id"]

    def on_script(sc, job):
        nc.update_row(rid, {"Status": "Scripted", "Title": sc["title"], "Job": job_ref(cfg, job),
                            "Format": "short"})

    try:
        job = build(cfg, topic, None, guidance=guidance, feedback=feedback, on_script=on_script)
        meta = json.loads((job / "metadata.json").read_text())
        nc.update_row(rid, {"Status": "Rendered", "Job": job_ref(cfg, job),
                            "Duration (s)": meta.get("duration_s")})
        qa = _qa(cfg, job)
        ok = qa["verdict"] != "fail"
        vals = {"QA": qa["verdict"], "QA Notes": qa["notes"], "Status": "Needs Approval" if ok else "Failed"}
        if ok and qa["verdict"] == "pass" and pcfg(cfg)["auto_approve"]:
            vals["Approve"] = True
        nc.update_row(rid, vals)
        title = meta.get("title", row.get("Title"))
        if ok:
            auto = vals.get("Approve")
            notify.send("New Short ready" + (" (auto-approved)" if auto else ", approve?"),
                        f"{title} - {meta.get('duration_s')}s, QA {qa['verdict']}" +
                        ("" if auto else "\nTick Approve (or Reject + Feedback) in Notion."),
                        click=row.get("_url"), tags=["clapper"])
        else:
            notify.send("Short failed QA", f"{title}: {qa['notes']}"[:400], click=row.get("_url"), tags=["x"])
        log.info("%s -> %s (QA %s)", title, vals["Status"], qa["verdict"])
        return {**row, **vals}
    except Exception as e:
        tb = traceback.format_exc()
        log.error("build failed for %r:\n%s", topic, tb)
        try:
            nc.update_row(rid, {"Status": "Failed", "QA": "fail",
                                "QA Notes": f"{type(e).__name__}: {e}\n\n{tb[-1500:]}"})
        except Exception as e2:
            log.error("could not mark row Failed: %s", e2)
        notify.send("Short build failed", f"{topic or 'auto topic'}: {e}"[:400], click=row.get("_url"),
                    tags=["x"])
        return {**row, "Status": "Failed"}


def nightly(cfg: dict, nc, count: int | None = None, build=None) -> list[dict]:
    count = count or pcfg(cfg)["shorts_per_night"]
    ideas = nc.query("Idea")[:count]
    guidance, feedback = _guidance(nc), _feedback(nc)
    while len(ideas) < count:
        ideas.append(nc.create_row({"Title": "(auto topic, writing script...)", "Status": "Idea",
                                    "Source": "auto", "Format": "short"}))
    results = [produce(cfg, nc, r, guidance, feedback, build) for r in ideas]
    publish(cfg, nc)
    return results


# ---------------------------------------------------------------- weekly jobs

def stats(cfg: dict, nc) -> int:
    rows = [r for r in nc.query(["Scheduled", "Live"]) if r.get("Video ID")]
    if not rows:
        log.info("stats: no uploaded videos yet")
        return 0
    yt = _optional("youtube")
    if yt is None or not yt.is_configured():
        log.warning("stats: YouTube not configured, skipping")
        return 0
    data = yt.fetch_stats([r["Video ID"] for r in rows])
    now = datetime.now(ZoneInfo(pcfg(cfg)["timezone"]))
    n = 0
    for r in rows:
        s = data.get(r["Video ID"])
        if not s:
            continue
        nc.update_row(r["_id"], {"Views": s.get("views"), "Likes": s.get("likes"),
                                 "Avg View %": s.get("avg_view_pct"), "Avg View (s)": s.get("avg_view_s"),
                                 "Stats Updated": now})
        n += 1
    log.info("stats: updated %d row(s)", n)
    return n


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
                       "Status": "Idea", "Source": "researcher", "Format": "short"})
        made += 1
    log.info("research: %d new idea(s)", made)
    return made


ANALYZE_FIELDS = ["Title", "Topic", "Format", "Source", "QA", "Duration (s)", "Publish At", "Views", "Likes",
                  "Avg View %", "Avg View (s)", "Stats Updated"]


def analyze(cfg: dict, nc) -> bool:
    rows = [r for r in nc.query(["Scheduled", "Live"]) if r.get("Views") is not None]
    if not rows:
        log.info("analyze: no rows with stats yet")
        return False
    agents = _optional("agents")
    if agents is None or not hasattr(agents, "analyze"):
        log.warning("analyze: agents module unavailable")
        return False
    clean = [{k: (v.isoformat() if isinstance(v, (date, datetime)) else v) for k, v in r.items()
              if k in ANALYZE_FIELDS} for r in rows]
    text = agents.analyze(cfg, clean, _guidance(nc))
    if not (text or "").strip():
        log.warning("analyze: empty result, What Works page left unchanged")
        return False
    nc.replace_page_text(text)
    log.info("analyze: What Works page updated from %d row(s)", len(rows))
    return True


# ---------------------------------------------------------------- CLI

def _run(name: str, fn, locked: bool):
    def handler(args, cfg) -> int:
        with run_log(cfg, name):
            try:
                with (pipeline_lock(cfg) if locked else contextlib.nullcontext()):
                    nc = _client()
                    fn(args, cfg, nc)
                return 0
            except Locked as e:
                log.info("%s skipped: %s", name, e)
                return 0
            except Exception as e:
                log.exception("%s failed: %s", name, e)
                notify.send(f"yt-auto {name} failed", str(e)[:400], tags=["rotating_light"])
                return 1
    return handler


def register(sub) -> None:
    p = sub.add_parser("nightly", help="build Shorts from Notion ideas -> QA -> Needs Approval, then publish")
    p.add_argument("--count", type=int, default=None, help="Shorts to build (default publish.shorts_per_night)")
    p.set_defaults(func=_run("nightly", lambda a, c, nc: nightly(c, nc, a.count), locked=True))

    p = sub.add_parser("publish", help="upload approved rows, mark rejected, flip Scheduled -> Live")
    p.set_defaults(func=_run("publish", lambda a, c, nc: publish(c, nc), locked=True))

    p = sub.add_parser("stats", help="refresh YouTube stats on Scheduled/Live rows")
    p.set_defaults(func=_run("stats", lambda a, c, nc: stats(c, nc), locked=False))

    p = sub.add_parser("research", help="researcher agent -> new Idea rows")
    p.add_argument("--n", type=int, default=10)
    p.set_defaults(func=_run("research", lambda a, c, nc: research(c, nc, a.n), locked=False))

    p = sub.add_parser("analyze", help="analyst agent -> rewrite the What Works page")
    p.set_defaults(func=_run("analyze", lambda a, c, nc: analyze(c, nc), locked=False))

    p = sub.add_parser("ntfy-topic", help="print the ntfy topic for phone notifications")
    p.add_argument("--test", action="store_true", help="also send a test push")
    p.set_defaults(func=lambda a, c: notify.cmd_topic(a, c))
