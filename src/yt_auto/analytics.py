"""Live analytics + reaction: checkpoints, deep metrics, winner/loser classification, hook check,
policy alerts, cadence rule, the "Scoreboard" section of the What Works page, and the script
similarity guard.

Everything here is pure logic (testable without Notion/YouTube) except `sweep`, which wires it to
the board. Notion rows are the only state (runners are ephemeral):

  Checkpoints   JSON {"1h": {"v", "l", "c", "age_h", "at"}, ..., "deep_at": iso}
  Views 1h..7d  the checkpoint view counts as plain numbers (sortable in Notion)
  Verdict       winner / average / loser / no baseline   (set once, at the 72 h checkpoint)
  Ratio 72h     72 h views / rolling median of the previous 20 Shorts' 72 h views
  Hook, Hook Pattern, Hook Check, Script, Series, YT Status, Alerts (dedupe tags for ntfy)

Quota: one videos.list call (1 unit) per 50 videos per sweep; Analytics API has its own quota.
"""

from __future__ import annotations

import difflib
import json
import logging
import re
import statistics
from datetime import date, datetime, timedelta, timezone

from . import notify

log = logging.getLogger("yt_auto.analytics")

CHECKPOINTS: list[tuple[str, float]] = [("1h", 1), ("6h", 6), ("24h", 24), ("72h", 72), ("7d", 168)]
VIEW_FIELDS = {"1h": "Views 1h", "6h": "Views 6h", "24h": "Views 24h", "72h": "Views 72h", "7d": "Views 7d"}

# Notion properties this module needs (added to the database on first use)
SCHEMA: dict[str, str] = {
    **{f: "number" for f in VIEW_FIELDS.values()},
    "Checkpoints": "rich_text",
    "Comments": "number",
    "Engaged Views": "number",
    "Shares": "number",
    "Subs Gained": "number",
    "Verdict": "select",
    "Ratio 72h": "number",
    "Hook": "rich_text",
    "Hook Pattern": "select",
    "Hook Check": "select",
    "Script": "rich_text",
    "Series": "rich_text",
    "YT Status": "rich_text",
    "Alerts": "rich_text",
    "Thumb Test": "rich_text",   # thumbtest.py rotation state (JSON)
    "Search Terms": "rich_text",  # YouTube-search terms that brought viewers (seo.search_terms), "term (views); ..."
}

DEFAULTS = {
    "sweep_hours": 6,          # full refresh at most this often (publish cron checks every 30 min)
    "deep_min_days": 4,        # Analytics API lags 48-72 h: deep metrics only from day 4
    "deep_max_days": 28,       # stop refreshing deep metrics after this
    "active_days": 28,         # due-only sweeps skip rows older than this (weekly full sweep still covers them)
    "baseline_n": 20,          # rolling median over the previous N Shorts' 72 h views
    "baseline_min": 3,         # fewer comparable Shorts than this -> "no baseline"
    "min_median_views": 10,    # a median below this is noise: no verdict
    "winner_ratio": 1.5,
    "loser_ratio": 0.3,
    "max_followups": 3,        # per series (topic)
    "hook_min_view_pct": 60.0,
    "hook_min_view_pct_long": 40.0,   # films / compilations: average % viewed below this = weak opening
    "hook_min_engaged_ratio": 0.5,
    "drop_ratio": 0.3,         # "down 70 %+" vs the median ...
    "drop_streak": 3,          # ... for this many Shorts in a row -> ntfy
    "cadence_floor_views": 100,  # 7-day median under this for 2 straight weeks -> 1 Short/night
    "similarity_threshold": 0.85,
    "similarity_window": 30,
}


def acfg(cfg: dict) -> dict:
    return {**DEFAULTS, **(cfg.get("analytics") or {})}


# ---------------------------------------------------------------- small helpers

def median(xs) -> float | None:
    vals = [float(x) for x in xs if x is not None]
    return statistics.median(vals) if vals else None


def _aware(v) -> datetime | None:
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    if isinstance(v, date):
        return datetime(v.year, v.month, v.day, tzinfo=timezone.utc)
    if isinstance(v, str) and v:
        try:
            return _aware(datetime.fromisoformat(v.replace("Z", "+00:00")))
        except ValueError:
            return None
    return None


def published_at(row: dict) -> datetime | None:
    return _aware(row.get("Publish At"))


def age_hours(row: dict, now: datetime) -> float | None:
    """Hours since the video went public; None if it isn't public yet (or has no publish time)."""
    p = published_at(row)
    if p is None or row.get("Status") not in ("Scheduled", "Live") or p > now:
        return None
    return (now - p).total_seconds() / 3600


def parse_cps(s) -> dict:
    if isinstance(s, dict):
        return dict(s)
    try:
        v = json.loads(s or "{}")
        return v if isinstance(v, dict) else {}
    except ValueError:
        return {}


def dump_cps(cps: dict) -> str:
    return json.dumps(cps, separators=(",", ":"), sort_keys=True)


def cp_views(row: dict, label: str) -> float | None:
    cp = parse_cps(row.get("Checkpoints")).get(label)
    if isinstance(cp, dict) and cp.get("v") is not None:
        return float(cp["v"])
    v = row.get(VIEW_FIELDS.get(label, ""))
    return float(v) if v is not None else None


def _tags(row: dict) -> set[str]:
    return {t.strip() for t in (row.get("Alerts") or "").split(",") if t.strip()}


def add_tag(row: dict, tag: str) -> str:
    return ", ".join(sorted(_tags(row) | {tag}))


# ---------------------------------------------------------------- checkpoints

def due_label(cps: dict, age_h: float | None) -> str | None:
    """The checkpoint to record now: the LATEST threshold already passed that isn't recorded yet.
    Earlier missed ones stay empty (recording 80 h views as the "1h" value would lie)."""
    if age_h is None:
        return None
    passed = [lb for lb, h in CHECKPOINTS if age_h >= h]
    if not passed or passed[-1] in cps:
        return None
    return passed[-1]


def record_checkpoint(cps: dict, age_h: float | None, stats: dict, now: datetime) -> tuple[dict, str | None]:
    """Returns (new checkpoints, label recorded or None). stats: {views, likes, comments}."""
    label = due_label(cps, age_h)
    if label is None or stats.get("views") is None:
        return cps, None
    out = dict(cps)
    out[label] = {"v": stats.get("views"), "l": stats.get("likes"), "c": stats.get("comments"),
                  "age_h": round(age_h, 1), "at": now.astimezone(timezone.utc).isoformat(timespec="minutes")}
    return out, label


def any_due(rows: list[dict], now: datetime) -> bool:
    return any(due_label(parse_cps(r.get("Checkpoints")), age_hours(r, now)) for r in rows)


# ---------------------------------------------------------------- classification

def _kind(r: dict) -> tuple[str, bool]:
    return (r.get("Format") or "short"), r.get("Source") == "film-cut"


def baseline(rows: list[dict], row: dict, n: int = 20) -> list[float]:
    """72 h views of the last n videos of the same kind published before `row` (excluding it): films vs
    films, compilations vs compilations, Shorts cut from films vs those Shorts (not the old Shorts)."""
    me = published_at(row) or datetime.max.replace(tzinfo=timezone.utc)
    kind = _kind(row)
    prev = [(published_at(r), cp_views(r, "72h")) for r in rows
            if r.get("_id") != row.get("_id") and _kind(r) == kind]
    prev = sorted((p, v) for p, v in prev if p is not None and v is not None and p < me)
    return [v for _, v in prev[-n:]]


def classify(views: float | None, base: list[float], a: dict | None = None) -> tuple[str, float | None]:
    """-> (verdict, ratio). verdict: winner / average / loser / no baseline."""
    a = a or DEFAULTS
    med = median(base)
    if views is None or med is None or len(base) < a["baseline_min"] or med < a["min_median_views"]:
        return "no baseline", None
    ratio = views / med
    if ratio > a["winner_ratio"]:
        return "winner", round(ratio, 2)
    if ratio < a["loser_ratio"]:
        return "loser", round(ratio, 2)
    return "average", round(ratio, 2)


def hook_problem(avg_view_pct: float | None, engaged: float | None, views: float | None,
                 a: dict | None = None, fmt: str | None = None) -> bool | None:
    """Day-4 gate: low retention or low engaged/views means the hook lost people. None = no data."""
    a = a or DEFAULTS
    checks = []
    if avg_view_pct is not None:
        checks.append(avg_view_pct < (a["hook_min_view_pct"] if fmt in (None, "short") else a["hook_min_view_pct_long"]))
    if engaged is not None and views:
        checks.append(engaged / views < a["hook_min_engaged_ratio"])
    return any(checks) if checks else None


_HOOK_RULES = [
    ("what-if", r"^(what (happens|would happen) (if|when)|what if)\b"),
    ("why", r"^why\b"),
    ("how", r"^how\b"),
    ("what-is", r"^(what('s| is| are| does)|what)\b"),
    ("myth", r"\b(is it true|really|actually|myth|lie)\b"),
    ("yes-no", r"^(is|are|can|could|does|do|did|will|would|should)\b"),
]


def hook_pattern(hook: str, names: tuple[str, ...] = ()) -> str:
    """Coarse, deterministic hook family from the opening line ("Baymax, why does ..." -> "why")."""
    s = (hook or "").strip().lower()
    for n in names:
        s = re.sub(rf"^{re.escape(n.lower())}\s*[,:!.-]*\s*", "", s)
    s = re.sub(r"^(hey|ok|okay|so|wait|um|uh)\b[\s,!.]*", "", s)
    for name, rx in _HOOK_RULES:
        if re.search(rx, s):
            return name
    return "statement"


# ---------------------------------------------------------------- similarity guard

def _norm_words(s: str) -> list[str]:
    return re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower()).split()


def similarity(a: str, b: str) -> float:
    wa, wb = _norm_words(a), _norm_words(b)
    if not wa or not wb:
        return 0.0
    return difflib.SequenceMatcher(None, wa, wb, autojunk=False).ratio()


def script_text(sc: dict) -> str:
    return " ".join(ln.get("text", "") for ln in sc.get("lines", []))


def too_similar(title: str, text: str, recent: list[dict], threshold: float = 0.85) -> tuple[float, str] | None:
    """recent: [{"title", "text"}]. Returns (score, matching title) of the closest one over threshold."""
    best = (0.0, "")
    for r in recent:
        s = max(similarity(title, r.get("title", "")),
                similarity(text, r.get("text", "")) if text and r.get("text") else 0.0)
        if s > best[0]:
            best = (s, r.get("title", ""))
    return best if best[0] >= threshold else None


# ---------------------------------------------------------------- alerts

POLICY_REASONS = {
    "copyright": "copyright", "claim": "copyright claim", "duplicate": "duplicate upload",
    "inappropriate": "inappropriate content", "legal": "legal complaint", "length": "too long",
    "termsOfUse": "terms of use violation", "trademark": "trademark", "uploaderAccountClosed": "account closed",
    "uploaderAccountSuspended": "account suspended",
}


def policy_issues(live: dict | None) -> list[str]:
    """Problems worth a push from a fetch_live() entry (None = video missing from the channel)."""
    if live is None or not live.get("found", True):
        return ["video not found on the channel (removed by YouTube or deleted)"]
    out = []
    us = live.get("upload_status")
    if us in ("rejected", "failed", "deleted"):
        why = live.get("rejection_reason") or live.get("failure_reason") or "?"
        out.append(f"upload {us}: {POLICY_REASONS.get(why, why)}")
    if live.get("blocked"):
        out.append(f"blocked in {len(live['blocked'])} region(s) (likely a copyright claim)")
    if live.get("age_restricted"):
        out.append("age-restricted by YouTube")
    return out


def yt_status_text(live: dict | None) -> str:
    if live is None or not live.get("found", True):
        return "not found"
    parts = [live.get("privacy") or "?", live.get("upload_status") or "?"]
    parts += policy_issues(live)
    return " | ".join(parts)


def drop_streak(rows: list[dict], a: dict | None = None) -> list[dict] | None:
    """The last `drop_streak` classified Shorts if ALL are <= drop_ratio x median, else None."""
    a = a or DEFAULTS
    done = sorted((r for r in rows if r.get("Ratio 72h") is not None and published_at(r)), key=published_at)
    last = done[-a["drop_streak"]:]
    if len(last) == a["drop_streak"] and all(r["Ratio 72h"] <= a["drop_ratio"] for r in last):
        return last
    return None


def cadence(rows: list[dict], now: datetime, configured: int, a: dict | None = None) -> tuple[int, str | None]:
    """Shorts per night. Drops to 1 when the median 7-day views were under the floor in BOTH of the
    last two weeks (by when the 7 d checkpoint landed; >= 2 videos per week needed)."""
    a = a or DEFAULTS
    if configured <= 1:
        return configured, None
    weeks = [[], []]
    for r in rows:
        cp = parse_cps(r.get("Checkpoints")).get("7d")
        at = _aware(cp.get("at")) if isinstance(cp, dict) else None
        if at is None or cp.get("v") is None:
            continue
        d = (now - at).days
        if 0 <= d < 7:
            weeks[0].append(cp["v"])
        elif 7 <= d < 14:
            weeks[1].append(cp["v"])
    if all(len(w) >= 2 for w in weeks):
        meds = [median(w) for w in weeks]
        if all(m < a["cadence_floor_views"] for m in meds):
            return 1, (f"7-day median views were {meds[1]:.0f} then {meds[0]:.0f} over the last two weeks "
                       f"(< {a['cadence_floor_views']}): making 1 Short a night instead of {configured} "
                       "until it recovers.")
    return configured, None


# ---------------------------------------------------------------- follow-ups

def series_root(row: dict) -> str:
    return (row.get("Series") or "").strip() or (row.get("Title") or "").strip()


def followup_row(winner: dict, all_rows: list[dict], a: dict | None = None) -> dict | None:
    """Idea row for one follow-up Short (same hook pattern, new subtopic), or None at the series cap."""
    a = a or DEFAULTS
    root = series_root(winner)
    made = [r for r in all_rows if (r.get("Series") or "").strip() == root and r.get("Source") == "follow-up"
            and r.get("Status") != "Failed"]
    if len(made) >= a["max_followups"]:
        return None
    part = len(made) + 2   # the original is part 1
    topic = (winner.get("Topic") or root).strip()
    pattern = winner.get("Hook Pattern") or "?"
    notes = (f"FOLLOW-UP to a winner: '{winner.get('Title')}' got {winner.get('Ratio 72h')}x the median 72 h views. "
             f"Reuse its hook pattern ({pattern}), e.g. its opening line: \"{winner.get('Hook') or winner.get('Title')}\". "
             f"Pick a NEW, adjacent subtopic of '{topic}' (do not re-explain the original). "
             f"Series '{root}', part {part}.")
    return {"Title": f"Follow-up ({part}): {topic}"[:90], "Topic": f"a new subtopic related to: {topic}",
            "Idea Notes": notes, "Status": "Idea", "Source": "follow-up", "Format": "short", "Series": root}


# ---------------------------------------------------------------- What Works scoreboard

BOARD_HEADING = "## Scoreboard (auto-updated from YouTube stats)"


def scoreboard(rows: list[dict], a: dict | None = None) -> str:
    """Deterministic signals for the writer/analyst (the analyst's prose sits above this section)."""
    a = a or DEFAULTS
    pub = [r for r in rows if published_at(r) and r.get("Status") in ("Scheduled", "Live")]
    v72 = [cp_views(r, "72h") for r in pub]
    lines = [BOARD_HEADING]
    base = [v for v in v72 if v is not None][-a["baseline_n"]:]
    lines.append(f"- Rolling median 72 h views (last {len(base)} Shorts): "
                 f"{median(base):.0f}" if base else "- Rolling median 72 h views: no data yet")
    pats: dict[str, dict] = {}
    for r in pub:
        p = r.get("Hook Pattern") or "unknown"
        d = pats.setdefault(p, {"n": 0, "winner": 0, "loser": 0, "weak": 0, "ratios": []})
        d["n"] += 1
        if r.get("Verdict") in ("winner", "loser"):
            d[r["Verdict"]] += 1
        if r.get("Hook Check") == "weak hook":
            d["weak"] += 1
        if r.get("Ratio 72h") is not None:
            d["ratios"].append(r["Ratio 72h"])
    if pats:
        lines.append("### Hook patterns")
        for p, d in sorted(pats.items(), key=lambda kv: -(median(kv[1]["ratios"]) or 0)):
            med = median(d["ratios"])
            tag = " WEAK" if d["loser"] and d["loser"] >= d["winner"] else (" STRONG" if d["winner"] > d["loser"] else "")
            lines.append(f"- {p}: {d['n']} videos, {d['winner']} winners, {d['loser']} losers, "
                         f"{d['weak']} weak-hook flags, median ratio {med:.2f}{tag}" if med is not None else
                         f"- {p}: {d['n']} videos, not classified yet")
    win = [r for r in pub if r.get("Verdict") == "winner"][-5:]
    lose = [r for r in pub if r.get("Verdict") == "loser"][-5:]
    weak = [r for r in pub if r.get("Hook Check") == "weak hook"][-5:]
    if win:
        lines.append("### Winners (make more like these)")
        lines += [f"- {r.get('Title')} ({r.get('Ratio 72h')}x, hook {r.get('Hook Pattern')})" for r in win]
    if lose:
        lines.append("### Losers (avoid these hook patterns)")
        lines += [f"- {r.get('Title')} ({r.get('Ratio 72h')}x, hook {r.get('Hook Pattern')})" for r in lose]
    if weak:
        lines.append("### Hook problems: change the hook, not the topic")
        lines += [f"- {r.get('Title')}: avg viewed {r.get('Avg View %')}%, engaged {r.get('Engaged Views')} "
                  f"of {r.get('Views')} views. The topic can return with a stronger first line." for r in weak]
    return "\n".join(lines) + "\n"


def split_board(page: str) -> tuple[str, str]:
    """(analyst text, scoreboard section) of the What Works page."""
    i = page.find(BOARD_HEADING)
    return (page, "") if i < 0 else (page[:i].rstrip() + "\n", page[i:])


def merge_board(page: str, board: str) -> str:
    head, _ = split_board(page)
    return (head.rstrip() + "\n\n" if head.strip() else "") + board


# ---------------------------------------------------------------- the sweep

def ensure_schema(nc) -> None:
    """Add the analytics columns to the Notion database (no-op for fakes / when already there)."""
    from . import notion
    notion.PROPS.update({k: v for k, v in SCHEMA.items() if k not in notion.PROPS})
    if hasattr(nc, "ensure_props"):
        nc.ensure_props(SCHEMA)


def sweep(cfg: dict, nc, yt, now: datetime | None = None, due_only: bool = False) -> dict:
    """One stats pass. due_only (publish cron): skip unless a checkpoint is due or the last sweep is
    older than sweep_hours. yt: the youtube module (fetch_live / fetch_deep)."""
    a = acfg(cfg)
    now = now or datetime.now(timezone.utc)
    summary = {"ran": False, "checkpoints": 0, "deep": 0, "classified": 0, "followups": 0, "alerts": 0}
    rows = [r for r in nc.query(["Needs Approval", "Scheduled", "Live"]) if r.get("Video ID")]
    if not rows:
        return summary
    if due_only:
        last = max((_aware(r.get("Stats Updated")) for r in rows if r.get("Stats Updated")), default=None)
        stale = last is None or now - last >= timedelta(hours=a["sweep_hours"])
        if not stale and not any_due(rows, now):
            return summary
        rows = [r for r in rows if (age_hours(r, now) or 0) <= a["active_days"] * 24]
    summary["ran"] = True
    ensure_schema(nc)

    live = yt.fetch_live([r["Video ID"] for r in rows])
    deep_ids = []
    for r in rows:
        age = age_hours(r, now)
        cps = parse_cps(r.get("Checkpoints"))
        deep_at = _aware(cps.get("deep_at"))
        if age is not None and a["deep_min_days"] * 24 <= age <= a["deep_max_days"] * 24 \
                and (deep_at is None or now - deep_at >= timedelta(hours=20)):
            deep_ids.append(r["Video ID"])
    try:
        deep = yt.fetch_deep(deep_ids) if deep_ids else {}
    except Exception as e:   # Analytics API down / report rejected: live stats still get recorded
        log.warning("deep metrics unavailable: %s", e)
        deep = {}

    updates: dict[str, dict] = {}
    for r in rows:
        lv = live.get(r["Video ID"])
        vals: dict = {"YT Status": yt_status_text(lv)[:300]}
        issues = policy_issues(lv)
        tag = "policy:" + "|".join(sorted(issues))[:60] if issues else None
        if tag and tag not in _tags(r):
            notify.send("yt-auto: YouTube flagged a video", f"{r.get('Title')}: {'; '.join(issues)}"[:400],
                        click=r.get("YouTube URL") or r.get("_url"), tags=["rotating_light"], priority=4)
            vals["Alerts"] = add_tag(r, tag)
            summary["alerts"] += 1
        cps = parse_cps(r.get("Checkpoints"))
        age = age_hours(r, now)
        if lv and lv.get("found", True) and age is not None:
            vals.update({"Views": lv.get("views"), "Likes": lv.get("likes"), "Comments": lv.get("comments")})
            cps, label = record_checkpoint(cps, age, lv, now)
            if label:
                vals[VIEW_FIELDS[label]] = lv.get("views")
                summary["checkpoints"] += 1
        d = deep.get(r["Video ID"])
        if d:
            vals.update({"Avg View %": d.get("avg_view_pct"), "Avg View (s)": d.get("avg_view_s"),
                         "Engaged Views": d.get("engaged_views"), "Shares": d.get("shares"),
                         "Subs Gained": d.get("subs_gained")})
            cps["deep_at"] = now.astimezone(timezone.utc).isoformat(timespec="minutes")
            hp = hook_problem(d.get("avg_view_pct"), d.get("engaged_views"), d.get("views"), a, r.get("Format"))
            if hp is not None:
                vals["Hook Check"] = "weak hook" if hp else "ok"
            summary["deep"] += 1
        vals["Checkpoints"] = dump_cps(cps)
        vals["Stats Updated"] = now
        r.update(vals)            # later steps (baseline, scoreboard) see the fresh values
        updates[r["_id"]] = vals

    # classify at 72 h against the previous 20 Shorts (all published rows form the baseline pool)
    pool = {r["_id"]: r for r in nc.query(["Scheduled", "Live"])}
    pool.update({r["_id"]: r for r in rows if r["_id"] in pool})
    every = None
    for r in sorted(pool.values(), key=lambda r: published_at(r) or now):
        # one verdict per video, at its 72 h checkpoint ("no baseline" is final too: a late verdict
        # would queue a follow-up long after the moment has passed)
        if r.get("Verdict") or cp_views(r, "72h") is None:
            continue
        verdict, ratio = classify(cp_views(r, "72h"), baseline(list(pool.values()), r, a["baseline_n"]), a)
        vals = {"Verdict": verdict, "Ratio 72h": ratio}
        r.update(vals)
        summary["classified"] += verdict != "no baseline"
        if verdict == "winner":
            every = every if every is not None else nc.query()
            fu = followup_row(r, every, a)
            if fu:
                every.append(nc.create_row(fu))
                vals["Series"] = series_root(r)
                summary["followups"] += 1
                notify.send("Winner! Follow-up queued", f"{r.get('Title')}: {ratio}x the median at 72 h. "
                            "Tonight's build makes a follow-up with the same hook.", click=r.get("_url"),
                            tags=["trophy"])
        updates.setdefault(r["_id"], {}).update(vals)
        r.update(vals)

    streak = drop_streak(list(pool.values()), a)
    if streak and not any("drop3" in _tags(r) for r in streak):
        newest = streak[-1]
        notify.send("yt-auto: views dropped", f"The last {len(streak)} Shorts got <= {a['drop_ratio']:.0%} of the "
                    "usual 72 h views: " + "; ".join(f"{r.get('Title')} ({r.get('Ratio 72h')}x)" for r in streak),
                    click=newest.get("_url"), tags=["chart_with_downwards_trend"], priority=4)
        updates.setdefault(newest["_id"], {})["Alerts"] = add_tag(newest, "drop3")
        summary["alerts"] += 1

    byid = {r["_id"]: r for r in [*rows, *pool.values()]}
    for rid, vals in updates.items():
        if vals:
            nc.update_row(rid, vals)
    log.info("stats sweep: %s", summary)

    try:
        board = scoreboard(sorted(byid.values(), key=lambda r: published_at(r) or now), a)
        page = nc.read_page_text()
        new = merge_board(page, board)
        if new.strip() != page.strip():
            nc.replace_page_text(new)
    except Exception as e:   # the board is a convenience; never fail the sweep over it
        log.warning("could not update the What Works scoreboard: %s", e)
    return summary
