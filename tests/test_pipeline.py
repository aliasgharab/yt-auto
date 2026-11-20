import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from yt_auto import pipeline
from yt_auto.pipeline import next_slot

TZ = ZoneInfo("America/Toronto")
SLOTS = ["12:00", "19:00"]


def at(*a):
    return datetime(*a, tzinfo=TZ)


# ---------------- slot scheduling

def test_next_slot_same_day():
    assert next_slot(at(2026, 11, 19, 9, 0), SLOTS, TZ, []) == at(2026, 11, 19, 12, 0)


def test_next_slot_needs_one_hour_lead():
    assert next_slot(at(2026, 11, 19, 11, 30), SLOTS, TZ, []) == at(2026, 11, 19, 19, 0)
    assert next_slot(at(2026, 11, 19, 18, 1), SLOTS, TZ, []) == at(2026, 11, 20, 12, 0)


def test_next_slot_skips_taken_any_tz():
    taken = [at(2026, 11, 19, 12, 0).astimezone(ZoneInfo("UTC")), at(2026, 11, 19, 19, 0)]
    assert next_slot(at(2026, 11, 19, 9, 0), SLOTS, TZ, taken) == at(2026, 11, 20, 12, 0)


def test_next_slot_dst_and_utc_now():
    # DST ends 2026-11-01 in Toronto; a UTC "now" must still produce local 12:00
    s = next_slot(datetime(2026, 11, 1, 2, 0, tzinfo=ZoneInfo("UTC")), SLOTS, "America/Toronto", [])
    assert s == at(2026, 11, 1, 12, 0) and s.utcoffset().total_seconds() == -5 * 3600


# ---------------- publish transitions

def make_job(cfg, name):
    job = cfg["_root"] / "out" / name
    job.mkdir(parents=True)
    (job / "video.mp4").write_bytes(b"x")
    return f"out/{name}"


@pytest.fixture
def youtube(fake_module):
    uploads = []

    schedules = []

    def upload(job, publish_at=None):
        uploads.append((job, publish_at))
        return f"vid{len(uploads)}"

    def schedule(video_id, publish_at, now=None):
        schedules.append((video_id, publish_at))
        return {"privacyStatus": "private" if publish_at else "public"}

    m = fake_module("youtube", is_configured=lambda: True, upload=upload, uploads=uploads,
                    schedule=schedule, schedules=schedules, keep_private=lambda vid: None)
    return m


def test_publish_schedules_rejects_and_goes_live(cfg, fake_notion, youtube):
    now = at(2026, 11, 19, 9, 0)
    nc = fake_notion([
        {"Title": "A", "Status": "Needs Approval", "Approve": True, "Job": make_job(cfg, "a"), "Format": "short"},
        {"Title": "B", "Status": "Needs Approval", "Approve": True, "Job": make_job(cfg, "b"), "Format": "short"},
        {"Title": "C", "Status": "Needs Approval", "Reject": True, "Feedback": "too slow"},
        {"Title": "D", "Status": "Needs Approval"},
        {"Title": "E", "Status": "Scheduled", "Publish At": at(2026, 11, 19, 8, 0)},
        {"Title": "F", "Status": "Scheduled", "Publish At": at(2026, 11, 19, 19, 0)},
    ])
    s = pipeline.publish(cfg, nc, now=now)
    by = {r["Title"]: r for r in nc.rows}
    assert s == {"rejected": 1, "scheduled": 2, "live": 1, "waiting": 0, "errors": 0}
    assert by["A"]["Status"] == "Scheduled" and by["A"]["Publish At"] == at(2026, 11, 19, 12, 0)
    # 19:00 today is taken by F -> B goes to tomorrow noon
    assert by["B"]["Publish At"] == at(2026, 11, 20, 12, 0)
    assert by["A"]["Video ID"] == "vid1" and by["A"]["YouTube URL"] == "https://youtube.com/shorts/vid1"
    assert youtube.uploads[0][0] == cfg["_root"] / "out/a"
    assert by["C"]["Status"] == "Rejected" and by["C"]["Feedback"] == "too slow"
    assert by["D"]["Status"] == "Needs Approval"
    assert by["E"]["Status"] == "Live" and by["F"]["Status"] == "Scheduled"


def test_publish_without_youtube_leaves_approved(cfg, fake_notion, fake_module):
    fake_module("youtube", is_configured=lambda: False)
    nc = fake_notion([{"Title": "A", "Status": "Needs Approval", "Approve": True, "Job": "out/a"}])
    s = pipeline.publish(cfg, nc, now=at(2026, 11, 19, 9, 0))
    assert s["waiting"] == 1 and nc.rows[0]["Status"] == "Needs Approval"
    assert not [x for x in nc.log if x[0] == "update"]


def test_publish_missing_module_is_graceful(cfg, fake_notion, monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, "yt_auto.youtube", None)  # forces ImportError
    nc = fake_notion([{"Title": "A", "Status": "Needs Approval", "Approve": True, "Job": "out/a"}])
    assert pipeline.publish(cfg, nc)["waiting"] == 1


def test_publish_upload_error_keeps_row(cfg, fake_notion, fake_module, no_push):
    def boom(job, at_):
        raise RuntimeError("quota")
    fake_module("youtube", is_configured=lambda: True, upload=boom)
    nc = fake_notion([{"Title": "A", "Status": "Needs Approval", "Approve": True, "Job": make_job(cfg, "a")}])
    s = pipeline.publish(cfg, nc, now=at(2026, 11, 19, 9, 0))
    assert s["errors"] == 1 and nc.rows[0]["Status"] == "Needs Approval" and no_push


# ---------------- nightly

def fake_build(cfg, topic, job, guidance="", feedback=None, on_script=None, past=None):
    fake_build.calls.append({"topic": topic, "guidance": guidance, "feedback": feedback})
    job = cfg["_root"] / "out" / f"job{len(fake_build.calls)}"
    job.mkdir(parents=True)
    on_script({"title": f"Title {len(fake_build.calls)}"}, job)
    (job / "video.mp4").write_bytes(b"x")
    (job / "metadata.json").write_text(json.dumps({"title": f"Title {len(fake_build.calls)}",
                                                   "duration_s": 28.4}))
    return job


def test_nightly_flow(cfg, fake_notion, fake_module, no_push):
    fake_build.calls = []
    verdicts = iter(["pass", "fail"])
    fake_module("agents", qa_review=lambda c, j: {"verdict": next(verdicts), "notes": "ok"})
    fake_module("youtube", is_configured=lambda: False)
    nc = fake_notion([{"Title": "Why watchdogs?", "Topic": "watchdog timers", "Status": "Idea"},
                      {"Title": "old", "Status": "Rejected", "Feedback": "too fast"}])
    nc.page = "# What Works\n- hooks"
    res = pipeline.nightly(cfg, nc, count=2, build=fake_build)
    assert [r["Status"] for r in res] == ["Needs Approval", "Failed"]
    assert fake_build.calls[0]["topic"] == "watchdog timers"
    assert fake_build.calls[1]["topic"] is None          # auto row: writer picks topic
    assert fake_build.calls[0]["guidance"].startswith("# What Works")
    assert fake_build.calls[0]["feedback"] == ["old: too fast"]
    a, b = nc.rows[0], nc.rows[2]
    assert b["Source"] == "auto" and b["Title"] == "Title 2"
    assert a["Job"] == "out/job1" and a["Duration (s)"] == 28.4 and a["QA"] == "pass"
    assert a["Approve"] is False
    statuses = [v.get("Status") for op, rid, v in nc.log if op == "update" and rid == a["_id"] and "Status" in v]
    assert statuses == ["Scripted", "Rendered", "Needs Approval"]
    assert any("approve?" in call[0][0] for call in no_push)


def test_nightly_auto_approve_and_exception(cfg, fake_notion, fake_module, youtube):
    cfg["publish"]["auto_approve"] = True
    fake_build.calls = []
    fake_module("agents", qa_review=lambda c, j: {"verdict": "pass", "notes": ""})

    def flaky(cfg_, topic, job, **kw):
        if topic == "bad":
            raise RuntimeError("tts crashed")
        return fake_build(cfg_, topic, job, **kw)
    nc = fake_notion([{"Title": "good", "Status": "Idea"}, {"Title": "bad", "Status": "Idea"}])
    pipeline.nightly(cfg, nc, count=2, build=flaky)
    good, bad = nc.rows
    assert good["Status"] == "Scheduled" and good["Approve"] is True and good["Video ID"] == "vid1"
    assert bad["Status"] == "Failed" and "tts crashed" in bad["QA Notes"]


def test_research_dedupes(cfg, fake_notion, fake_module):
    fake_module("agents", research_ideas=lambda c, titles, n: [
        {"title": "Why Watchdogs?", "topic": "x", "notes": ""},       # dup of existing (case/punct)
        {"title": "What is DMA", "topic": "dma", "notes": "n"},
        {"title": "what is dma!", "topic": "dma", "notes": ""}])       # dup within batch
    nc = fake_notion([{"Title": "why watchdogs", "Status": "Live"}])
    assert pipeline.research(cfg, nc, 3) == 1
    assert nc.rows[-1]["Source"] == "researcher" and nc.rows[-1]["Status"] == "Idea"


def test_stats_and_analyze(cfg, fake_notion, fake_module):
    fake_module("youtube", is_configured=lambda: True, fetch_stats=lambda ids: {
        "v1": {"views": 100, "likes": 5, "avg_view_pct": 80.5, "avg_view_s": 22.1}})
    seen = {}

    def analyze(c, rows, cur):
        seen.update(rows=rows, cur=cur)
        return "# What Works\n- short hooks"
    fake_module("agents", analyze=analyze)
    nc = fake_notion([{"Title": "A", "Status": "Live", "Video ID": "v1"},
                      {"Title": "B", "Status": "Needs Approval"}])
    assert pipeline.stats(cfg, nc) == 1
    assert nc.rows[0]["Views"] == 100 and nc.rows[0]["Avg View %"] == 80.5 and nc.rows[0]["Stats Updated"]
    assert pipeline.analyze(cfg, nc) is True
    assert nc.page.startswith("# What Works") and seen["rows"][0]["Views"] == 100
    assert isinstance(seen["rows"][0]["Stats Updated"], str)


def test_lock_prevents_overlap(cfg):
    with pipeline.pipeline_lock(cfg):
        with pytest.raises(pipeline.Locked):
            with pipeline.pipeline_lock(cfg):
                pass
