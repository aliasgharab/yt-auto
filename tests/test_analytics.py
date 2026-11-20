import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from yt_auto import analytics as an

NOW = datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc)


def ago(**kw):
    return NOW - timedelta(**kw)


def pubrow(i, days, v72=None, **kw):
    r = {"_id": f"r{i}", "Title": f"T{i}", "Status": "Live", "Video ID": f"vid{i}", "Publish At": ago(days=days)}
    if v72 is not None:
        r["Checkpoints"] = json.dumps({"72h": {"v": v72}})
    r.update(kw)
    return r


def live(views, **kw):
    return {"found": True, "views": views, "likes": 1, "comments": 0, "privacy": "public",
            "upload_status": "processed", **kw}


# ---------------- median / checkpoints

def test_median():
    assert an.median([1, 3, 2]) == 2
    assert an.median([1, 2, 3, 4]) == 2.5
    assert an.median([None, 5, None]) == 5
    assert an.median([]) is None and an.median([None]) is None


def test_due_label():
    assert an.due_label({}, 0.5) is None
    assert an.due_label({}, None) is None
    assert an.due_label({}, 1.5) == "1h"
    assert an.due_label({"1h": {}}, 1.5) is None
    assert an.due_label({}, 80) == "72h"          # skips the missed 1h/6h/24h
    assert an.due_label({"72h": {}}, 80) is None
    assert an.due_label({"72h": {}}, 200) == "7d"


def test_record_checkpoint():
    cps, label = an.record_checkpoint({}, 80.04, {"views": 9, "likes": 1, "comments": 2}, NOW)
    assert label == "72h" and list(cps) == ["72h"]
    assert cps["72h"]["v"] == 9 and cps["72h"]["age_h"] == 80.0 and cps["72h"]["at"].startswith("2026-11-19T12:00")
    assert an.record_checkpoint({}, 0.5, {"views": 9}, NOW) == ({}, None)
    assert an.record_checkpoint({}, None, {"views": 9}, NOW) == ({}, None)


def test_non_public_rows_are_never_due():
    r = {"Status": "Needs Approval", "Publish At": ago(hours=100)}
    assert an.age_hours(r, NOW) is None and not an.any_due([r], NOW)
    future = {"Status": "Scheduled", "Publish At": NOW + timedelta(hours=3)}
    assert an.age_hours(future, NOW) is None


def test_any_due():
    assert an.any_due([{"Status": "Live", "Publish At": ago(hours=2)}], NOW)
    done = {"Status": "Live", "Publish At": ago(hours=2), "Checkpoints": json.dumps({"1h": {"v": 1}})}
    assert not an.any_due([done], NOW)


# ---------------- baseline / classify / hooks

def test_baseline():
    rows = [pubrow(i, 30 - i, v72=100 + i) for i in range(5)]
    me = pubrow(9, 10, v72=999)
    later = pubrow(10, 1, v72=5)
    longf = pubrow(11, 20, v72=7, Format="long")
    no72 = pubrow(12, 12)
    pool = rows + [me, later, longf, no72]
    assert an.baseline(pool, me) == [100, 101, 102, 103, 104]
    assert an.baseline(pool, me, n=2) == [103, 104]
    assert 999 not in an.baseline(pool, me)


def test_classify():
    base = [100, 100, 100]
    assert an.classify(160, base) == ("winner", 1.6)
    assert an.classify(150, base)[0] == "average"      # not strictly > 1.5
    assert an.classify(29, base)[0] == "loser"
    assert an.classify(100, base) == ("average", 1.0)
    assert an.classify(500, [100, 100]) == ("no baseline", None)
    assert an.classify(500, [5, 5, 5]) == ("no baseline", None)
    assert an.classify(None, base) == ("no baseline", None)


def test_hook_problem():
    assert an.hook_problem(50, None, None) is True
    assert an.hook_problem(80, 40, 100) is True
    assert an.hook_problem(80, 60, 100) is False
    assert an.hook_problem(None, None, 100) is None
    assert an.hook_problem(None, 10, 0) is None


def test_hook_pattern():
    assert an.hook_pattern("Baymax, why does the sky look blue?", ("Baymax",)) == "why"
    assert an.hook_pattern("What happens if you fall into a black hole?") == "what-if"
    assert an.hook_pattern("Can a fish drown?") == "yes-no"
    assert an.hook_pattern("How do magnets work?") == "how"
    assert an.hook_pattern("Cats sleep sixteen hours a day.") == "statement"


# ---------------- similarity

def test_similarity():
    t = "a watchdog timer resets the chip when software hangs"
    assert an.similarity(t, t) == 1.0
    assert an.similarity("", t) == 0.0
    recent = [{"title": "Why watchdogs reset chips", "text": t}]
    hit = an.too_similar("Different", t, recent, 0.85)
    assert hit and hit[0] == 1.0 and hit[1] == "Why watchdogs reset chips"
    assert an.too_similar("How rainbows form", "light bends inside raindrops", recent, 0.85) is None
    # title-only near-duplicate (no script text)
    assert an.too_similar("Why watchdogs reset chips!", "", recent, 0.85)


def test_script_text():
    assert an.script_text({"lines": [{"text": "a"}, {"text": "b"}]}) == "a b"


# ---------------- policy / streak / cadence

def test_policy_issues():
    assert an.policy_issues(live(1)) == []
    assert "copyright" in an.policy_issues(live(1, upload_status="rejected", rejection_reason="copyright"))[0]
    assert "2 region" in an.policy_issues(live(1, blocked=["DE", "FR"]))[0]
    assert "age" in an.policy_issues(live(1, age_restricted=True))[0]
    assert "not found" in an.policy_issues(None)[0]
    assert "not found" in an.policy_issues({"found": False})[0]


def test_drop_streak():
    rows = [pubrow(i, 10 - i, **{"Ratio 72h": r}) for i, r in enumerate([1.0, 0.2, 0.1, 0.3])]
    assert [r["_id"] for r in an.drop_streak(rows)] == ["r1", "r2", "r3"]
    rows[2]["Ratio 72h"] = 0.8     # one recovery breaks it
    assert an.drop_streak(rows) is None
    assert an.drop_streak(rows[:2]) is None


def _wk(i, days_ago, v):
    return {"_id": f"c{i}", "Checkpoints": json.dumps({"7d": {"v": v, "at": ago(days=days_ago).isoformat()}})}


def test_cadence():
    bad = [_wk(1, 1, 50), _wk(2, 3, 80), _wk(3, 8, 20), _wk(4, 10, 60)]
    n, why = an.cadence(bad, NOW, 2)
    assert n == 1 and why and "1 Short" in why
    good_week = [_wk(1, 1, 50), _wk(2, 3, 5000), _wk(3, 8, 20), _wk(4, 10, 60)]
    assert an.cadence(good_week, NOW, 2) == (2, None)
    assert an.cadence(bad, NOW, 1) == (1, None)
    assert an.cadence(bad[:3], NOW, 2) == (2, None)     # only 1 video in the older week


# ---------------- follow-ups

def test_followup_row():
    w = {"Title": "Why sky blue", "Topic": "sky", "Ratio 72h": 3.0, "Hook Pattern": "why", "Hook": "Why blue?"}
    fu = an.followup_row(w, [])
    assert fu["Source"] == "follow-up" and fu["Status"] == "Idea" and fu["Series"] == "Why sky blue"
    assert fu["Title"].startswith("Follow-up (2)") and "why" in fu["Idea Notes"]
    made = [{"Series": "Why sky blue", "Source": "follow-up", "Status": "Idea"}]
    assert an.followup_row(w, made)["Title"].startswith("Follow-up (3)")
    made.append({"Series": "Why sky blue", "Source": "follow-up", "Status": "Failed"})   # failed ones don't count
    assert an.followup_row(w, made)["Title"].startswith("Follow-up (3)")
    made = made[:1] * 3
    assert an.followup_row(w, made) is None


# ---------------- board

def test_board_round_trip():
    board1 = an.BOARD_HEADING + "\n- old\n"
    page = "# What Works\n- hooks\n\n" + board1
    head, b = an.split_board(page)
    assert head == "# What Works\n- hooks\n" and b == board1
    board2 = an.BOARD_HEADING + "\n- new\n"
    out = an.merge_board(page, board2)
    assert "- hooks" in out and "- new" in out and "- old" not in out and out.count(an.BOARD_HEADING) == 1
    assert an.merge_board("", board2) == board2
    assert an.split_board("plain") == ("plain", "")


# ---------------- sweep

class FakeYT:
    def __init__(self, lives, deep=None, deep_error=None):
        self.lives, self.deep, self.deep_error = lives, deep or {}, deep_error
        self.live_calls, self.deep_calls = [], []

    def fetch_live(self, ids):
        self.live_calls.append(list(ids))
        return {i: self.lives[i] for i in ids if i in self.lives}

    def fetch_deep(self, ids):
        self.deep_calls.append(list(ids))
        if self.deep_error:
            raise self.deep_error
        return {i: self.deep[i] for i in ids if i in self.deep}


def baseline_rows():
    return [{"Title": f"B{i}", "Status": "Live", "Video ID": f"b{i}", "Publish At": ago(days=30 + i),
             "Verdict": "average", "Ratio 72h": 1.0,
             "Checkpoints": json.dumps({"72h": {"v": 100}, "7d": {"v": 300, "at": ago(days=20).isoformat()}})}
            for i in range(3)]


def make_nc(fake_notion, extra=()):
    nc = fake_notion([*baseline_rows(),
                      {"Title": "Winner", "Topic": "sky", "Status": "Live", "Video ID": "w", "Publish At": ago(days=5)},
                      {"Title": "Young", "Status": "Live", "Video ID": "y", "Publish At": ago(hours=2)}, *extra])
    nc.page = "# What Works\n- hooks"
    return nc


def row(nc, title):
    return next(r for r in nc.rows if r.get("Title") == title)


def test_sweep_end_to_end(cfg, fake_notion, no_push):
    nc = make_nc(fake_notion)
    yt = FakeYT({"b0": live(900), "b1": live(900), "b2": live(900), "w": live(1000), "y": live(7)},
                deep={"w": {"views": 1000, "avg_view_pct": 90, "avg_view_s": 20, "engaged_views": 900,
                            "shares": 3, "subs_gained": 2}})
    s = an.sweep(cfg, nc, yt, now=NOW)
    assert s["ran"] and s["checkpoints"] == 2 and s["deep"] == 1 and s["followups"] == 1
    w, y = row(nc, "Winner"), row(nc, "Young")
    assert yt.deep_calls == [["w"]]                         # only the >=4-day-old video inside the window
    cps = json.loads(w["Checkpoints"])
    assert cps["72h"]["v"] == 1000 and "1h" not in cps and "deep_at" in cps and w["Views 72h"] == 1000
    assert w["Avg View %"] == 90 and w["Hook Check"] == "ok" and w["Verdict"] == "winner" and w["Ratio 72h"] == 10.0
    assert json.loads(y["Checkpoints"])["1h"]["v"] == 7 and "deep_at" not in json.loads(y["Checkpoints"])
    assert y.get("Verdict") is None and y["YT Status"].startswith("public")
    fus = [r for r in nc.rows if r.get("Source") == "follow-up"]
    assert len(fus) == 1 and fus[0]["Status"] == "Idea" and fus[0]["Series"] == "Winner"
    assert an.BOARD_HEADING in nc.page and nc.page.startswith("# What Works")
    # second sweep: no second follow-up, no new deep fetch
    s2 = an.sweep(cfg, nc, yt, now=NOW)
    assert s2["followups"] == 0 and len([r for r in nc.rows if r.get("Source") == "follow-up"]) == 1
    assert len(yt.deep_calls) == 1


def test_sweep_deep_failure_is_survivable(cfg, fake_notion):
    nc = make_nc(fake_notion)
    yt = FakeYT({"w": live(1000)}, deep_error=RuntimeError("analytics down"))
    s = an.sweep(cfg, nc, yt, now=NOW)
    assert s["ran"] and s["deep"] == 0 and row(nc, "Winner")["Views 72h"] == 1000


def test_sweep_no_baseline_is_final(cfg, fake_notion):
    nc = fake_notion([{"Title": "Solo", "Status": "Live", "Video ID": "s", "Publish At": ago(days=5)}])
    yt = FakeYT({"s": live(500)})
    an.sweep(cfg, nc, yt, now=NOW)
    assert row(nc, "Solo")["Verdict"] == "no baseline"
    nc.rows.extend(fake_notion(baseline_rows()).rows)       # baseline appears later
    an.sweep(cfg, nc, yt, now=NOW)
    assert row(nc, "Solo")["Verdict"] == "no baseline"
    assert not [r for r in nc.rows if r.get("Source") == "follow-up"]


def test_sweep_policy_alert_once(cfg, fake_notion, no_push):
    nc = fake_notion([{"Title": "Claimed", "Status": "Live", "Video ID": "c", "Publish At": ago(hours=30)}])
    yt = FakeYT({"c": live(10, upload_status="rejected", rejection_reason="copyright")})
    s = an.sweep(cfg, nc, yt, now=NOW)
    flagged = [c for c in no_push if "flagged" in c[0][0]]
    assert s["alerts"] == 1 and len(flagged) == 1
    assert "policy:" in row(nc, "Claimed")["Alerts"]
    s2 = an.sweep(cfg, nc, yt, now=NOW + timedelta(hours=1))
    assert s2["alerts"] == 0 and len([c for c in no_push if "flagged" in c[0][0]]) == 1


def test_sweep_due_only(cfg, fake_notion):
    cps = {"1h": {"v": 1}, "6h": {"v": 2}, "24h": {"v": 3}}
    base = {"Title": "A", "Status": "Live", "Video ID": "a", "Publish At": ago(hours=30),
            "Checkpoints": json.dumps(cps)}
    nc = fake_notion([{**base, "Stats Updated": ago(hours=1)}])
    yt = FakeYT({"a": live(5)})
    assert an.sweep(cfg, nc, yt, now=NOW, due_only=True)["ran"] is False
    assert yt.live_calls == []
    nc2 = fake_notion([{**base, "Stats Updated": ago(hours=7)}])          # stale -> runs
    assert an.sweep(cfg, nc2, yt, now=NOW, due_only=True)["ran"] is True
    nc3 = fake_notion([{**base, "Checkpoints": "{}", "Stats Updated": ago(hours=1)}])   # checkpoint due -> runs
    assert an.sweep(cfg, nc3, yt, now=NOW, due_only=True)["ran"] is True


def test_sweep_no_rows(cfg, fake_notion):
    s = an.sweep(cfg, fake_notion([{"Title": "x", "Status": "Idea"}]), FakeYT({}), now=NOW)
    assert s["ran"] is False
