"""Agents around the build pipeline: idea research, video QA, analytics -> "What works" guidance.

All LLM calls are headless `claude -p` on the user's subscription (no API key). Everything that can
be computed deterministically (network signals, ffprobe checks, word counts) is done in Python first
and handed to the model as facts.
"""

import concurrent.futures as cf
import difflib
import json
import re
import string
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from . import script

PROMPTS = Path(__file__).resolve().parent / "prompts"
UA = "yt-auto-research/0.1"


def load_prompt(name: str, **kw) -> str:
    """prompts/<name>.md with $placeholders filled (string.Template; unknown $words are left alone)."""
    return string.Template((PROMPTS / f"{name}.md").read_text()).safe_substitute(**kw)


def _claude(prompt: str, cfg: dict, schema: dict, *, tools: str = "", add_dirs: list[Path] = (),
            cwd: Path | None = None, timeout: int = 900) -> dict:
    """claude -p with structured output. tools="" disables every tool; tools="Read" allows reading
    only (pre-approved, confined to cwd + add_dirs)."""
    llm = cfg["llm"]
    if llm["backend"] != "claude-cli":
        raise ValueError(f"unknown llm backend {llm['backend']}")
    cmd = ["claude", "-p", "--output-format", "json", "--model", llm["model"],
           "--json-schema", json.dumps(schema), "--tools", tools, "--no-session-persistence"]
    if tools:
        cmd += ["--allowedTools", tools]
    for d in add_dirs:
        cmd += ["--add-dir", str(d)]
    res = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=timeout,
                         cwd=str(cwd) if cwd else None)
    return _parse_claude_output(res)


def _parse_claude_output(res: subprocess.CompletedProcess) -> dict:
    if res.returncode != 0:
        raise RuntimeError(f"claude CLI failed ({res.returncode}): {(res.stderr or res.stdout)[-2000:]}")
    out = json.loads(res.stdout)
    if out.get("is_error"):
        raise RuntimeError(f"claude CLI error: {str(out.get('result'))[:2000]}")
    if isinstance(out.get("structured_output"), dict):
        return out["structured_output"]
    return script._extract_json(out.get("result", ""))


# ============================================================================ 1. research
HN_KEYWORDS = ["interrupt", "watchdog timer", "DMA", "bootloader", "RTOS", "context switch", "virtual memory",
               "deadlock", "race condition", "system call", "device driver", "microcontroller", "scheduler",
               "page fault", "firmware"]
SUBREDDITS = ["embedded", "osdev", "arduino", "explainlikeimfive", "learnprogramming"]
ELI5_QUERY = "computer OR memory OR processor OR phone OR chip OR operating system"
YT_QUERIES = ["computer explained shorts", "how does a cpu work shorts", "operating system explained shorts",
              "embedded systems explained shorts", "microcontroller explained shorts"]
NET_BUDGET_S = 45


def _get_json(url: str, timeout: float = 8) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def _hn(keyword: str) -> list[dict]:
    since = int(time.time()) - 365 * 86400
    q = urllib.parse.urlencode({"query": keyword, "tags": "story", "hitsPerPage": 6,
                                "numericFilters": f"created_at_i>{since},points>20"})
    hits = _get_json(f"https://hn.algolia.com/api/v1/search?{q}").get("hits", [])
    return [{"source": "hn", "query": keyword, "title": h.get("title") or "",
             "url": f"https://news.ycombinator.com/item?id={h['objectID']}",
             "score": h.get("points") or 0, "comments": h.get("num_comments") or 0} for h in hits]


def _reddit(sub: str) -> list[dict]:
    if sub == "explainlikeimfive":
        q = urllib.parse.urlencode({"q": ELI5_QUERY, "restrict_sr": 1, "sort": "top", "t": "year", "limit": 15})
        path = f"r/{sub}/search.json?{q}"
    else:
        path = f"r/{sub}/top.json?t=month&limit=15"
    data = None
    for host in ("https://www.reddit.com", "https://old.reddit.com"):
        try:
            data = _get_json(f"{host}/{path}")
            break
        except Exception as e:  # reddit often 403s anonymous clients; try the other host once
            err = e
    if data is None:
        raise err
    out = []
    for c in data.get("data", {}).get("children", []):
        d = c.get("data", {})
        if d.get("stickied") or d.get("over_18"):
            continue
        out.append({"source": f"r/{sub}", "title": d.get("title", ""),
                    "url": "https://www.reddit.com" + d.get("permalink", ""),
                    "score": d.get("score", 0), "comments": d.get("num_comments", 0)})
    return out


def _youtube(query: str) -> list[dict]:
    res = subprocess.run([sys.executable, "-m", "yt_dlp", "--flat-playlist", "-J", "--no-warnings",
                          "--socket-timeout", "10", f"ytsearch20:{query}"],
                         capture_output=True, text=True, timeout=40)
    if res.returncode != 0:
        raise RuntimeError(res.stderr[-300:])
    out = []
    for e in json.loads(res.stdout).get("entries") or []:
        dur = e.get("duration")
        url = e.get("url") or f"https://www.youtube.com/watch?v={e.get('id')}"
        is_short = "/shorts/" in url or (dur is not None and dur <= 61)
        out.append({"source": "youtube", "query": query, "title": e.get("title") or "", "url": url,
                    "views": e.get("view_count"), "duration": dur, "short": is_short,
                    "channel": e.get("channel")})
    return out


def gather_signals(budget_s: float = NET_BUDGET_S) -> tuple[list[dict], list[str]]:
    """Runs every source in parallel under one wall-clock budget. Returns (signals, errors)."""
    jobs = ([(f"hn:{k}", _hn, k) for k in HN_KEYWORDS] + [(f"reddit:{s}", _reddit, s) for s in SUBREDDITS]
            + [(f"yt:{q}", _youtube, q) for q in YT_QUERIES])
    signals, errors = [], []
    ex = cf.ThreadPoolExecutor(max_workers=12)
    futs = {ex.submit(fn, arg): name for name, fn, arg in jobs}
    done, pending = cf.wait(futs, timeout=budget_s)
    for f in done:
        try:
            signals += f.result()
        except Exception as e:
            errors.append(f"{futs[f]}: {type(e).__name__}: {str(e)[:120]}")
    errors += [f"{futs[f]}: timed out" for f in pending]
    ex.shutdown(wait=False, cancel_futures=True)
    return _dedupe_signals(signals), errors


def _dedupe_signals(signals: list[dict]) -> list[dict]:
    seen, out = set(), []
    for s in signals:
        if s["url"] in seen or not s["title"]:
            continue
        seen.add(s["url"])
        out.append(s)
    return out


def format_signals(signals: list[dict], per_source: int = 25) -> str:
    """Compact, ranked text block for the prompt (highest score/views first per source family)."""
    def rank(s):
        return s.get("views") or s.get("score") or 0
    fams = {"hn": [], "reddit": [], "youtube": []}
    for s in signals:
        fams["reddit" if s["source"].startswith("r/") else s["source"]].append(s)
    parts = []
    for fam, items in fams.items():
        items = sorted(items, key=rank, reverse=True)[:per_source]
        if not items:
            parts.append(f"[{fam}] (no data: source unavailable)")
            continue
        parts.append(f"[{fam}]")
        for s in items:
            title = s["title"][:110]
            if fam == "youtube":
                v = s.get("views")
                kind = "Short" if s.get("short") else f"{s.get('duration') or '?'}s video"
                parts.append(f"- {title} | {v if v is not None else '?'} views | {kind} | {s['url']}")
            else:
                parts.append(f"- {title} | {s['source']} | {s['score']} pts, {s['comments']} comments | {s['url']}")
    return "\n".join(parts)


def _norm_title(t: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", t.lower().replace("baymax,", "")).strip()


def dedupe_ideas(ideas: list[dict], existing_titles: list[str], n: int, threshold: float = 0.8) -> list[dict]:
    kept, seen = [], [_norm_title(t) for t in existing_titles]
    for idea in ideas:
        t = _norm_title(idea.get("title", ""))
        if not t or any(difflib.SequenceMatcher(None, t, s).ratio() >= threshold for s in seen):
            continue
        seen.append(t)
        kept.append({"title": idea["title"].strip(), "topic": idea.get("topic", "").strip(),
                     "notes": idea.get("notes", "").strip()})
    return kept[:n]


IDEAS_SCHEMA = {
    "type": "object", "required": ["ideas"],
    "properties": {"ideas": {"type": "array", "items": {
        "type": "object", "required": ["title", "topic", "notes"],
        "properties": {"title": {"type": "string", "maxLength": 80}, "topic": {"type": "string"},
                       "notes": {"type": "string"}}}}},
}


def research_ideas(cfg: dict, existing_titles: list[str], n: int) -> list[dict]:
    """Free public signals (HN, Reddit, YouTube search) -> one claude call -> n question-style ideas."""
    signals, errors = gather_signals()
    for e in errors:
        print(f"  [research] source failed: {e}", file=sys.stderr)
    duo = cfg["duo"]
    prompt = load_prompt(
        "research", A=duo["asker"], B=duo["explainer"], niche=" ".join(cfg["channel"]["niche"].split()),
        signals=format_signals(signals) if signals else "(all sources failed today: rely on the niche)",
        existing="\n".join(f"- {t}" for t in existing_titles[-150:]) or "(none yet)", n=n + 2)
    ideas = _claude(prompt, cfg, IDEAS_SCHEMA).get("ideas", [])
    return dedupe_ideas(ideas, existing_titles, n)


# ============================================================================ 3. QA
QA_FRAMES = 6
SCHEMA_QA = {
    "type": "object", "required": ["verdict", "issues", "summary"],
    "properties": {
        "verdict": {"enum": ["pass", "warn", "fail"]},
        "summary": {"type": "string"},
        "issues": {"type": "array", "items": {
            "type": "object", "required": ["frame", "severity", "problem"],
            "properties": {"frame": {"type": "string"}, "severity": {"enum": ["warn", "fail"]},
                           "problem": {"type": "string"}}}},
    },
}
_RANK = {"pass": 0, "warn": 1, "fail": 2}


def _worst(*verdicts: str) -> str:
    return max(verdicts, key=lambda v: _RANK[v], default="pass")


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:'[a-z]+)?", text.lower().replace("’", "'"))


def srt_text(srt: str) -> str:
    keep = [ln for ln in srt.splitlines()
            if ln.strip() and not ln.strip().isdigit() and "-->" not in ln]
    return " ".join(keep)


def ass_text(ass: str) -> str:
    out = []
    for ln in ass.splitlines():
        if ln.startswith("Dialogue:"):
            out.append(re.sub(r"\{[^}]*\}", "", ln.split(",", 9)[-1]).replace("\\N", " "))
    return " ".join(out)


def word_overlap(script_text: str, caption_text: str) -> float:
    """Fraction of script words (as a multiset) that appear in the captions."""
    s, c = _words(script_text), _words(caption_text)
    if not s:
        return 0.0
    pool = {}
    for w in c:
        pool[w] = pool.get(w, 0) + 1
    hit = 0
    for w in s:
        if pool.get(w, 0) > 0:
            pool[w] -= 1
            hit += 1
    return hit / len(s)


def ffprobe(path: Path) -> dict:
    res = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams",
                          str(path)], capture_output=True, text=True, timeout=60)
    if res.returncode != 0:
        raise RuntimeError(res.stderr[-500:])
    return json.loads(res.stdout)


def volumedetect(path: Path) -> dict:
    res = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af", "volumedetect",
                          "-f", "null", "-"], capture_output=True, text=True, timeout=120)
    vals = dict(re.findall(r"(mean_volume|max_volume): (-?[\d.]+|-inf) dB", res.stderr))
    return {k: float(v) for k, v in vals.items()}


def _popup_refs(job: Path, sc: dict) -> tuple[list[Path], list[str]]:
    """Popup images the video depends on: ffmpeg_cmd.txt references (authoritative) plus, per script
    line with a popup, popup_XX.png (older renderer) or cards/XX/0000.png (animated renderer)."""
    refs, missing = [], []
    cmdf = job / "ffmpeg_cmd.txt"
    if cmdf.exists():
        marker = f"/{job.name}/"
        for tok in cmdf.read_text().split():
            if marker not in tok or not tok.endswith(".png"):
                continue
            rel = tok.split(marker, 1)[1]  # re-anchor on this job dir, in case it was moved
            if not (rel.startswith("popup_") or rel.startswith("cards/")):
                continue
            p = job / rel
            refs.append(p)
            first = p.parent / "0000.png" if "%" in p.name else p
            if not first.exists():
                missing.append(str(first.relative_to(job)))
    for i, ln in enumerate(sc.get("lines", [])):
        if not ln.get("popup"):
            continue
        cands = [job / f"popup_{i:02d}.png", job / "cards" / f"{i:02d}" / "0000.png"]
        if not any(c.exists() for c in cands):
            missing.append(f"popup for line {i} (popup_{i:02d}.png or cards/{i:02d}/)")
    return refs, sorted(set(missing))


def deterministic_checks(job: Path) -> tuple[list[tuple[str, str]], dict]:
    """Returns ([(severity, message)], facts). severity in ok|warn|fail."""
    res, facts = [], {}
    add = lambda sev, msg: res.append((sev, msg))  # noqa: E731
    video = job / "video.mp4"
    sc = json.loads((job / "script.json").read_text()) if (job / "script.json").exists() else {}
    timing = json.loads((job / "timing.json").read_text()) if (job / "timing.json").exists() else []
    if not sc:
        add("fail", "script.json missing")
    if not video.exists() or video.stat().st_size < 10_000:
        add("fail", "video.mp4 missing or empty")
        return res, facts

    try:
        info = ffprobe(video)
    except Exception as e:
        add("fail", f"ffprobe failed: {e}")
        return res, facts
    dur = float(info.get("format", {}).get("duration", 0))
    facts["duration_s"] = round(dur, 2)
    vs = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
    aus = [s for s in info.get("streams", []) if s.get("codec_type") == "audio"]
    if not 15 <= dur <= 60:
        add("fail", f"duration {dur:.1f}s outside 15-60s")
    else:
        add("ok", f"duration {dur:.1f}s")
    if timing:
        expect = timing[-1]["end"] + 0.5
        facts["expected_duration_s"] = round(expect, 2)
        if abs(dur - expect) > 1.5:
            add("warn", f"duration {dur:.1f}s differs from timing.json ({expect:.1f}s) by {abs(dur - expect):.1f}s")
        else:
            add("ok", f"duration matches timing.json ({expect:.1f}s)")
    else:
        add("warn", "timing.json missing")
    if not vs:
        add("fail", "no video stream")
    else:
        w, h = vs[0].get("width"), vs[0].get("height")
        facts["size"] = f"{w}x{h}"
        add("ok" if (w, h) == (1080, 1920) else "fail", f"resolution {w}x{h}")
    if not aus:
        add("fail", "no audio stream")
    else:
        vol = volumedetect(video)
        facts.update(vol)
        mean, peak = vol.get("mean_volume", -999), vol.get("max_volume", -999)
        if peak < -40 or mean < -50:
            add("fail", f"audio silent (mean {mean} dB, peak {peak} dB)")
        elif mean < -35:
            add("warn", f"audio very quiet (mean {mean} dB)")
        else:
            add("ok", f"audio mean {mean} dB, peak {peak} dB")

    text = " ".join(ln.get("text", "") for ln in sc.get("lines", []))
    cap = ""
    if (job / "captions.srt").exists():
        cap = srt_text((job / "captions.srt").read_text())
    elif (job / "captions.ass").exists():
        cap = ass_text((job / "captions.ass").read_text())
    if text:
        ov = word_overlap(text, cap)
        facts["caption_overlap"] = round(ov, 3)
        sev = "ok" if ov >= 0.85 else "warn" if ov >= 0.60 else "fail"
        add(sev, f"captions cover {ov:.0%} of script words")

    refs, missing = _popup_refs(job, sc)
    if missing:
        add("fail", "missing popup images: " + ", ".join(missing))
    else:
        n = sum(1 for ln in sc.get("lines", []) if ln.get("popup"))
        add("ok", f"all {n} popup cards present")
    return res, facts


def extract_frames(job: Path, duration: float, n: int = QA_FRAMES) -> list[tuple[Path, float]]:
    out = job / "qa_frames"
    out.mkdir(exist_ok=True)
    for old in out.glob("frame_*.jpg"):
        old.unlink()
    frames = []
    for k in range(n):
        t = duration * (k + 0.5) / n
        p = out / f"frame_{k + 1:02d}.jpg"
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{t:.2f}",
                        "-i", str(job / "video.mp4"), "-frames:v", "1", "-vf", "scale=540:-2", "-q:v", "3",
                        str(p)], check=True, timeout=60)
        frames.append((p, t))
    return frames


def _frame_context(frames, sc, timing) -> str:
    lines = sc.get("lines", [])
    rows = []
    for p, t in frames:
        cur = max((i for i, tm in enumerate(timing) if tm["start"] <= t), default=None)
        if cur is None or cur >= len(lines):
            rows.append(f"- {p.name} @ {t:.1f}s: (no line)")
            continue
        card = next((i for i in range(cur, -1, -1) if lines[i].get("popup")), None)
        cdesc = json.dumps(lines[card]["popup"], ensure_ascii=False) if card is not None else "none"
        rows.append(f"- {p.name} @ {t:.1f}s: {lines[cur]['speaker']} says \"{lines[cur]['text']}\"; "
                    f"card on screen (from line {card}): {cdesc}")
    return "\n".join(rows)


def vision_check(cfg: dict, job: Path, frames, sc: dict, timing: list) -> dict:
    duo = cfg["duo"]
    prompt = load_prompt(
        "qa_vision", A=duo["asker"], B=duo["explainer"],
        frames="\n".join(f"- {p.name}" for p, _ in frames),
        frame_context=_frame_context(frames, sc, timing),
        script="\n".join(f"{i}. {ln['speaker']}: {ln['text']}" for i, ln in enumerate(sc.get("lines", []))))
    fdir = frames[0][0].parent
    return _claude(prompt, cfg, SCHEMA_QA, tools="Read", add_dirs=[fdir], cwd=fdir, timeout=600)


def combine_qa(checks: list[tuple[str, str]], vision: dict | None, vision_error: str | None = None) -> dict:
    det = _worst(*("pass" if s == "ok" else s for s, _ in checks))
    notes = [f"[{s}] {m}" for s, m in checks if s != "ok"]
    vis = "pass"
    if vision_error:
        vis = "warn"
        notes.append(f"[warn] visual check unavailable: {vision_error}")
    elif vision is not None:
        issues = vision.get("issues", [])
        vis = _worst(vision.get("verdict", "pass"), *(i.get("severity", "warn") for i in issues))
        notes += [f"[{i.get('severity', 'warn')}] {i.get('frame', '?')}: {i.get('problem', '')}" for i in issues]
        if vision.get("summary"):
            notes.append(f"visual: {vision['summary']}")
    verdict = _worst(det, vis)
    if not notes:
        notes.append("all checks passed")
    return {"verdict": verdict, "notes": "\n".join(notes)}


def qa_review(cfg: dict, job: Path) -> dict:
    """Deterministic checks + a read-only claude look at ~6 frames. Writes job/qa.json."""
    job = Path(job)
    checks, facts = deterministic_checks(job)
    vision, verr = None, None
    if any(s == "fail" for s, m in checks if "video.mp4" in m or "ffprobe" in m):
        verr = "skipped (no playable video)"
    else:
        try:
            sc = json.loads((job / "script.json").read_text())
            timing = json.loads((job / "timing.json").read_text()) if (job / "timing.json").exists() else []
            frames = extract_frames(job, facts.get("duration_s", 20))
            vision = vision_check(cfg, job, frames, sc, timing)
        except Exception as e:
            verr = f"{type(e).__name__}: {str(e)[:300]}"
    result = combine_qa(checks, vision, verr)
    (job / "qa.json").write_text(json.dumps({**result, "checks": [{"severity": s, "check": m} for s, m in checks],
                                             "facts": facts, "vision": vision, "at": time.time()},
                                            indent=2, ensure_ascii=False))
    return result


# ============================================================================ 4. analytics
ANALYZE_SCHEMA = {"type": "object", "required": ["guidance_markdown"],
                  "properties": {"guidance_markdown": {"type": "string"}}}
_ROW_KEYS = ["title", "topic", "duration_s", "views", "likes", "avg_view_pct", "avg_view_s", "publish_at",
             "views_1h", "views_24h", "views_72h", "views_7d", "engaged_views", "shares", "subs_gained", "comments",
             "verdict", "ratio_72h", "hook_pattern", "hook_check", "series", "hook"]
# Notion column -> analyst key
_NOTION_KEYS = {"Title": "title", "Topic": "topic", "Duration (s)": "duration_s", "Views": "views", "Likes": "likes",
                "Avg View %": "avg_view_pct", "Avg View (s)": "avg_view_s", "Publish At": "publish_at",
                "Views 1h": "views_1h", "Views 24h": "views_24h", "Views 72h": "views_72h", "Views 7d": "views_7d",
                "Engaged Views": "engaged_views", "Shares": "shares", "Subs Gained": "subs_gained",
                "Comments": "comments", "Verdict": "verdict", "Ratio 72h": "ratio_72h", "Hook Pattern": "hook_pattern",
                "Hook Check": "hook_check", "Series": "series", "Hook": "hook", "Script": "script"}


def _keys(r: dict) -> dict:
    return {_NOTION_KEYS.get(k, k): v for k, v in r.items()}


def _has_stats(r: dict) -> bool:
    return r.get("views") is not None


def format_rows(rows: list[dict]) -> str:
    out = []
    rows = [_keys(r) for r in rows]
    for r in sorted(rows, key=lambda r: str(r.get("publish_at") or "")):
        head = " | ".join(f"{k}={r.get(k)}" for k in _ROW_KEYS if r.get(k) is not None)
        txt = " ".join(str(r.get("script") or r.get("script_text") or "").split())[:600]
        out.append(f"- {head}\n  script: {txt}")
    return "\n".join(out)


def analyze(cfg: dict, rows: list[dict], current_guidance: str, signals: str = "") -> str:
    """Performance rows (+ the deterministic scoreboard) -> concise markdown "What works" guidance."""
    rows = [_keys(r) for r in rows]
    with_stats = sum(1 for r in rows if _has_stats(r))
    small = ("FEWER THAN 5 VIDEOS HAVE STATS. This is far too little data for conclusions: say so in one "
             "line at the top, keep the current guidance almost unchanged, and add at most one or two "
             "clearly-labelled weak signals." if with_stats < 5 else "")
    duo = cfg["duo"]
    prompt = load_prompt("analyze", A=duo["asker"], B=duo["explainer"], videos_with_stats=with_stats,
                         videos_total=len(rows), small_sample_note=small, rows=format_rows(rows) or "(none)",
                         current=current_guidance.strip() or "(empty)",
                         signals=(signals or "").strip() or "(none yet)")
    return _claude(prompt, cfg, ANALYZE_SCHEMA)["guidance_markdown"].strip()


# ============================================================================ CLI
def _existing_titles(cfg: dict) -> list[str]:
    titles = []
    for p in sorted((cfg["_root"] / cfg["output_dir"]).glob("*/script.json")):
        try:
            titles.append(json.loads(p.read_text())["title"])
        except Exception:
            pass
    return titles


def _cmd_qa(a, cfg):
    r = qa_review(cfg, a.job.resolve())
    print(f"QA verdict: {r['verdict'].upper()}\n{r['notes']}")
    return 0 if r["verdict"] != "fail" else 1


def _cmd_ideas(a, cfg):
    for i, idea in enumerate(research_ideas(cfg, _existing_titles(cfg), a.n), 1):
        print(f"{i}. {idea['title']}\n   topic: {idea['topic']}\n   notes: {idea['notes']}\n")
    return 0


def register(subparsers) -> None:
    qa = subparsers.add_parser("qa", help="QA-check a finished job (writes <job>/qa.json)")
    qa.add_argument("--from", dest="job", type=Path, required=True)
    qa.set_defaults(func=_cmd_qa)
    ide = subparsers.add_parser("ideas", help="research video ideas (prints only)")
    ide.add_argument("--n", type=int, default=3)
    ide.set_defaults(func=_cmd_ideas)
