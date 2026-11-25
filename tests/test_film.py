import json
from pathlib import Path

from yt_auto import film, pipeline


def test_minutes_rounds_up():
    assert film.minutes_for(163) == 3
    assert film.minutes_for(119.5) == 2
    assert film.minutes_for(120) == 3      # exactly 2:00 is not 'under 2 minutes'
    assert film.minutes_for(40) == 1


def test_title_pattern():
    assert film.make_title("The Enigma Machine", 3) == "The Enigma Machine Explained in Under 3 Minutes"
    assert film.make_title("  Y2K. ", 1) == "Y2K Explained in Under 1 Minute"


def test_description_has_summary_sources_disclosure_hashtags():
    d = film.make_description(
        "How Britain broke the 'unbreakable' Enigma.",
        [{"title": "Enigma machine (Wikipedia)", "url": "https://en.wikipedia.org/wiki/Enigma_machine"}],
        ["Enigma", "#Alan Turing", "TechHistory", "Enigma", "!!", "Cryptography", "WW2", "extra"])
    parts = d.split("\n\n")
    assert parts[0] == "How Britain broke the 'unbreakable' Enigma."
    assert parts[1] == "Sources:\n• Enigma machine (Wikipedia): https://en.wikipedia.org/wiki/Enigma_machine"
    assert parts[2] == film.DISCLOSURE
    assert parts[3] == "#Enigma #AlanTuring #TechHistory #Cryptography #WW2"   # deduped, cleaned, max 5


class _Resp:
    def __init__(self, status):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _Opener:
    def __init__(self, good):
        self.good, self.seen = good, []

    def open(self, req, timeout=None):
        self.seen.append((req.get_method(), req.full_url, req.get_header("User-agent")))
        if req.full_url in self.good:
            return _Resp(200)
        raise OSError("404")


def test_check_sources_drops_broken_and_invalid():
    op = _Opener({"https://ok.example/a"})
    kept = film.check_sources([{"title": " A ", "url": "https://ok.example/a"},
                               {"title": "B", "url": "https://bad.example/b"},
                               {"title": "C", "url": "ftp://x"}], opener=op)
    assert kept == [{"title": "A", "url": "https://ok.example/a"}]
    assert ("GET", "https://bad.example/b") in [(m, u) for m, u, _ in op.seen]   # HEAD failed -> GET tried
    assert all("@" not in (ua or "") for _, _, ua in op.seen)                    # no personal details sent


def test_srt_from_timings(tmp_path: Path):
    tim = {"lines": [{"text": "In 1939.", "start": 0.0, "end": 1.5}, {"text": "They were wrong.", "start": 2.0, "end": 3.25}]}
    film.write_srt(tim, tmp_path / "c.srt")
    srt = (tmp_path / "c.srt").read_text()
    assert "1\n00:00:00,667 --> 00:00:02,167\nIn 1939." in srt
    assert "2\n00:00:02,667 --> 00:00:03,917\nThey were wrong." in srt


def test_composition_id():
    assert film.composition_id("enigma") == "FilmEnigma"
    assert film.composition_id("morris-worm") == "FilmMorrisWorm"


def test_builder_registry_and_urls():
    assert pipeline.builder_for("film") is film.build_film
    assert pipeline.builder_for("short").__name__ == "build_short"
    assert pipeline.youtube_url("abc", "film") == "https://youtu.be/abc"
    assert pipeline.youtube_url("abc", "short") == "https://youtube.com/shorts/abc"
    assert pipeline.per_night({"publish": {"videos_per_night": 1, "shorts_per_night": 5}}) == 1


def test_qa_film_duration_and_resolution(tmp_path: Path, monkeypatch):
    from yt_auto import agents
    (tmp_path / "job.json").write_text(json.dumps({"format": "film"}))
    (tmp_path / "script.json").write_text(json.dumps({"lines": [{"text": "hello there"}]}))
    (tmp_path / "video.mp4").write_bytes(b"0" * 20000)
    (tmp_path / "captions.srt").write_text("1\n00:00:00,667 --> 00:00:02,000\nhello there\n")
    monkeypatch.setattr(agents, "ffprobe", lambda v: {"format": {"duration": "163.0"}, "streams": [
        {"codec_type": "video", "width": 1920, "height": 1080}, {"codec_type": "audio"}]})
    monkeypatch.setattr(agents, "volumedetect", lambda v: {"mean_volume": -18.0, "max_volume": -1.2})
    monkeypatch.setattr(agents, "media_checks", lambda *a: a[4]("ok", "media checks stubbed"))
    checks, facts = agents.deterministic_checks(tmp_path)
    fails = [m for s, m in checks if s == "fail"]
    assert not fails, fails


# ---------------------------------------------------------------- schedule, Shorts, compilations
from datetime import datetime as _dt
from zoneinfo import ZoneInfo as _Z


def test_build_days():
    cfg = {"publish": {"timezone": "America/Toronto", "build_days": ["mon", "wed", "fri", "sun"]}}
    tz = _Z("America/Toronto")
    assert pipeline.build_day(cfg, _dt(2026, 11, 23, 2, 30, tzinfo=tz))       # Monday
    assert not pipeline.build_day(cfg, _dt(2026, 11, 24, 2, 30, tzinfo=tz))   # Tuesday
    assert pipeline.build_day({"publish": {}}, _dt(2026, 11, 24, 2, 30, tzinfo=tz))   # default: every day


def test_short_end_line_prefers_writer_cliffhanger_within_limit():
    from yt_auto import cuts
    lines = [{"text": f"l{i}", "pause": 1.4 if i == 10 else 0.5} for i in range(1, 15)]
    tim = {"lines": [{"startFrame": i * 100, "endFrame": i * 100 + 80} for i in range(14)]}
    assert cuts.short_end_line({"lines": lines, "short_end_line": 10}, tim) == 10
    # asked for a line past ~55 s -> falls back to the last fitting line with a long pause, else the last fitting
    tim_long = {"lines": [{"startFrame": i * 200, "endFrame": i * 200 + 150} for i in range(14)]}
    n = cuts.short_end_line({"lines": lines, "short_end_line": 14}, tim_long)
    assert 1 <= n <= 8


def test_short_waits_for_and_follows_its_film():
    tz = _Z("America/Toronto")
    film = {"Title": "The Enigma Machine Explained in Under 3 Minutes", "Format": "film",
            "Publish At": _dt(2026, 11, 23, 17, 0, tzinfo=tz)}
    short = {"Series": film["Title"], "Format": "short", "Source": "film-cut"}
    assert pipeline._parent_publish_at(short, [film], tz) == film["Publish At"]
    assert pipeline._parent_publish_at(short, [], tz) is None


def test_baseline_compares_like_with_like():
    from yt_auto import analytics
    old_short = {"_id": "a", "Format": "short", "Publish At": "2026-11-01", "Views 72h": 900}
    cut = {"_id": "b", "Format": "short", "Source": "film-cut", "Publish At": "2026-11-20", "Views 72h": 50}
    film = {"_id": "c", "Format": "film", "Publish At": "2026-11-21", "Views 72h": 300}
    me = {"_id": "d", "Format": "short", "Source": "film-cut", "Publish At": "2026-11-25"}
    assert analytics._kind(me) == analytics._kind(cut) != analytics._kind(old_short)
    assert analytics._kind(film) != analytics._kind(me)


# ---------------------------------------------------------------- thumbnail rotation test
def test_thumbtest_rotation_and_winner():
    from datetime import date as _d
    from yt_auto import thumbtest as tt
    assert [tt.variant_for(i) for i in range(7)] == ["a", "b", "c", "a", "b", "c", None]
    pub = _dt(2026, 11, 23, 17, 0, tzinfo=_Z("America/Toronto"))          # 14:00 PT, day 0
    assert tt.plan_day(pub, _dt(2026, 11, 24, 1, 0, tzinfo=tt.PT)) == 1
    per_day = {"2026-11-23": 0.04, "2026-11-24": 0.06, "2026-11-25": 0.03,
               "2026-11-26": 0.05, "2026-11-27": 0.07, "2026-11-28": 0.02}
    s = tt.score(per_day, _d(2026, 11, 23))
    assert round(s["a"], 3) == 0.045 and round(s["b"], 3) == 0.065 and round(s["c"], 3) == 0.025
    assert tt.pick_winner(s) == "b"
    assert tt.pick_winner({"a": 0.050, "b": 0.051}) == "a"     # needs a >5% lift to replace A
    assert tt.pick_winner({}) == "a"


def test_thumbtest_tick_rotates_and_records(monkeypatch, tmp_path):
    import json as _j
    from yt_auto import thumbtest as tt

    class NC:
        def __init__(self):
            self.rows = [{"_id": "r1", "Title": "T", "Format": "film", "Video ID": "vid", "Status": "Live",
                          "Publish At": "2026-11-23T17:00:00-05:00", "Job": "x"}]
            self.updates = []

        def query(self, st):
            return self.rows

        def update_row(self, rid, vals):
            self.updates.append(vals)
            self.rows[0].update(vals)

    f = tmp_path / "thumbnail_b.jpg"
    f.write_bytes(b"x")
    set_calls = []
    monkeypatch.setattr(tt, "thumb_file", lambda cfg, r, v, td: f)
    monkeypatch.setattr(tt, "set_thumb", lambda yt, vid, p: set_calls.append(vid))
    monkeypatch.setattr(tt, "reach_job", lambda rp: None)
    monkeypatch.setattr(tt, "_reporting", lambda: None)
    nc = NC()
    out = tt.tick({"_root": tmp_path}, nc, None, now=_dt(2026, 11, 24, 9, 0, tzinfo=tt.PT))   # day 1 -> B
    assert out["rotated"] == 1 and set_calls == ["vid"]
    assert _j.loads(nc.rows[0]["Thumb Test"])["current"] == "b"
    tt.tick({"_root": tmp_path}, nc, None, now=_dt(2026, 11, 24, 10, 0, tzinfo=tt.PT))           # same day: no-op
    assert set_calls == ["vid"]


def test_built_today_blocks_a_second_build_same_toronto_day():
    tz = _Z("America/Toronto")

    class NC:
        def __init__(self, rows):
            self.rows = rows

        def query(self, st):
            return self.rows

    cfg = {"default_format": "film", "publish": {"timezone": "America/Toronto"}}
    now = _dt(2026, 11, 23, 14, 0, tzinfo=tz)
    film_today = {"Format": "film", "_created": "2026-11-23T07:45:00.000Z"}       # 02:45 Toronto, same day
    film_yday = {"Format": "film", "_created": "2026-11-22T08:00:00.000Z"}
    short_today = {"Format": "short", "Source": "film-cut", "_created": "2026-11-23T08:00:00.000Z"}
    assert pipeline.built_today(cfg, NC([film_today]), now)
    assert not pipeline.built_today(cfg, NC([film_yday, short_today]), now)


def test_speech_coverage_ignores_spelled_out_numbers():
    script = "The alarm was twelve oh two. In nineteen sixty-nine, Armstrong kept going."
    heard = set("the alarm was 1202 in 1969 armstrong kept going".split())
    assert film.coverage_of(heard, script) == 1.0
    assert film.coverage_of({"the"}, "the alarm") == 0.5


def test_nightly_retries_next_idea_after_a_failed_build(monkeypatch):
    import types
    ideas = [{"_id": "i1", "Title": "A", "Status": "Idea"}, {"_id": "i2", "Title": "B", "Status": "Idea"}]

    class NC:
        def query(self, st):
            return [r for r in ideas if r["Status"] == "Idea"] if st == "Idea" else []

        def create_row(self, v):
            return {"_id": "new", **v}

        def update_row(self, *a):
            pass

    built = []

    def fake_produce(cfg, nc, row, *a, **k):
        built.append(row["_id"])
        row["Status"] = "Failed" if row["_id"] == "i1" else "Needs Approval"
        return dict(row)

    monkeypatch.setattr(pipeline, "produce", fake_produce)
    monkeypatch.setattr(pipeline, "publish", lambda *a, **k: None)
    monkeypatch.setattr(pipeline, "_ensure_schema", lambda nc: None)
    monkeypatch.setattr(pipeline, "build_day", lambda cfg: True)
    monkeypatch.setattr(pipeline, "built_today", lambda cfg, nc: False)
    monkeypatch.setattr(pipeline, "_cadence", lambda cfg, nc, n: 1)
    monkeypatch.setattr(pipeline, "compilation_due", lambda cfg, nc: None)
    for f in ("_guidance", "_feedback", "_recent_scripts"):
        monkeypatch.setattr(pipeline, f, lambda nc, *a: [] if f != "_guidance" else "")
    cfg = {"default_format": "film", "publish": {"timezone": "America/Toronto", "videos_per_night": 1}}
    res = pipeline.nightly(cfg, NC())
    assert built == ["i1", "i2"] and [r["Status"] for r in res] == ["Failed", "Needs Approval"]


# ---------------------------------------------------------------- SEO
def test_seo_demand_and_subject_choice():
    from yt_auto import seo
    sugg = {"taum sauk dam failure": ["taum sauk dam failure", "taum sauk dam failure 2005"],
            "taum sauk reservoir breach": [],
            "taum sauk": ["taum sauk", "taum sauk dam failure", "taum sauk dam", "taum sauk reservoir"]}
    plan = seo.keyword_plan("The Taum Sauk Reservoir Breach", ["taum sauk dam failure", "taum sauk"],
                            fetch=lambda q: sugg.get(q.lower(), []), pause=0)
    assert plan["primary"] in ("taum sauk dam failure", "taum sauk")
    assert plan["subject"].startswith("The ") and plan["subject"] != "The Taum Sauk Reservoir Breach"
    assert seo.demand("anything", []) == 0.0
    drift = seo.keyword_plan("The Apollo 11 1202 Alarm", ["apollo guidance computer"],
                             fetch=lambda q: ["apollo guidance computer", "apollo guidance computer explained"]
                             if "guidance" in q else [], pause=0)
    assert drift["subject"] == "The Apollo 11 1202 Alarm" and drift["primary"] == "apollo guidance computer"


def test_seo_lead_chapters_tags():
    from yt_auto import seo
    assert seo.lead_with("In 1999 NASA lost the Mars Climate Orbiter.", "mars climate orbiter").startswith("In 1999")
    assert seo.lead_with("NASA lost a probe.", "mars climate orbiter crash").startswith("Mars climate orbiter crash: ")
    ch = seo.chapters([(0.7, "The Probe"), (40, "The Units"), (45, "too close"), (90, "Why It Crashed")], 150)
    assert ch == [("0:00", "The Probe"), ("0:40", "The Units"), ("1:30", "Why It Crashed")]
    assert seo.chapters([(0, "a"), (50, "b")], 150) == []          # fewer than 3 -> none
    t = seo.tags("mars climate orbiter", ["mars climate orbiter crash", "Mars Climate Orbiter"], ["x"] * 3)
    assert t[:2] == ["mars climate orbiter", "mars climate orbiter crash"] and len(t) == 3
    assert seo.tags("The Mars Climate Orbiter", [], [])[0] == "Mars Climate Orbiter"
    rel = seo.clean_related(["mars climate orbiter crash - 1998", "mars climate orbiter deutsch", "sonda mars climate orbiter",
                             "mars climate orbiter launch", "mars climate orbiter error", "mars bars recipe"],
                            ["The Mars Climate Orbiter"])
    assert rel == ["mars climate orbiter crash 1998", "mars climate orbiter error"]


def test_film_description_has_chapters_between_summary_and_sources():
    d = film.make_description("S.", [{"title": "W", "url": "https://w"}], ["A"], [("0:00", "Intro"), ("0:40", "B"), ("1:30", "C")])
    parts = d.split("\n\n")
    assert parts[1].startswith("0:00 Intro") and parts[2].startswith("Sources:")
