"""Story-format test Short (DripDyl-style): one first-person narrator, 60-90 s, "In this world..."
premise built on a real tech concept, twist ending, one big yellow word on screen at a time.
Same visuals as the daily Shorts (gameplay, cards, character). Does not change the daily pipeline.

  .venv/bin/python tools/story_test.py ["topic"]        # write + render -> out/<date>-<slug>-story/
  .venv/bin/python tools/story_test.py --dripdyl        # full DripDyl format: 2.5 min, fast, "what if" world
  .venv/bin/python tools/story_test.py --from out/JOB   # re-render an existing story job
"""
import copy
import json
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from yt_auto import _slug, cards, duo, helper, script  # noqa: E402
from yt_auto.agents import load_prompt  # noqa: E402
from yt_auto.config import load_config  # noqa: E402

NARRATOR = "Hiro"
STYLES = {   # prompt, words, lines, tempo, max seconds
    "tech": dict(prompt="story_writer", words=(150, 200), lines=(12, 22), tempo=1.0, max_seconds=90),
    # DripDyl format: ~2.5 min, ~230 words/min (1.6x measured 275 wpm on the clone voice -> 1.35x), "what if" world
    "dripdyl": dict(prompt="story_dripdyl", words=(540, 620), lines=(50, 75), tempo=1.35, max_seconds=170),
}
STYLE = STYLES["dripdyl" if "--dripdyl" in sys.argv else "tech"]


def story_cfg(cfg):
    c = copy.deepcopy(cfg)
    c["duo"].update(max_seconds=STYLE["max_seconds"], tempo=STYLE["tempo"], captions="single")
    return c


def write_story(cfg, topic):
    ch = cfg["duo"]["characters"][NARRATOR]
    if STYLE["prompt"] == "story_dripdyl":
        topic_line = f"PREMISE IDEA: {topic}" if topic else "PREMISE: invent a fresh, original one."
    else:
        topic_line = (f"CONCEPT: {topic}" if topic else
                      f"CONCEPT: pick ONE specific concept from this niche: {cfg['channel']['niche']}")
    (lo_w, hi_w), (lo_l, hi_l) = STYLE["words"], STYLE["lines"]
    prompt = load_prompt(STYLE["prompt"], N=NARRATOR, N_personality=ch["personality"], topic_line=topic_line,
                         lo_w=lo_w, hi_w=hi_w, lo_l=lo_l, hi_l=hi_l, popup_guide=cards.POPUP_GUIDE)
    draft = script._call_claude(prompt, cfg, duo._schema([NARRATOR]))
    if STYLE["prompt"] != "story_dripdyl":
        return draft
    # editor pass: free helper model first (plot holes, twist clarity, safety), Claude as fallback
    schema = {"type": "object", "required": ["problems", "script"], "properties": {
        "problems": {"type": "array", "items": {"type": "object", "required": ["problem", "fix"], "properties": {
            "category": {"type": "string"}, "line": {"type": ["integer", "null"]},
            "problem": {"type": "string"}, "fix": {"type": "string"}}}},
        "script": duo._schema([NARRATOR])}}
    ep = load_prompt("story_editor", draft=json.dumps(draft, indent=1, ensure_ascii=False), lo_w=lo_w, hi_w=hi_w,
                     lo_l=lo_l, hi_l=hi_l, popup_guide=cards.POPUP_GUIDE)
    edited = helper.call_json(ep, schema, cfg, "story_editor", timeout=600)
    words = sum(len(ln["text"].split()) for ln in (edited or {}).get("script", {}).get("lines", []))
    if edited is None or not lo_w * 0.85 <= words <= hi_w * 1.15:
        edited = script._call_claude(ep, cfg, schema)
    for pr in edited.get("problems", []):
        print(f"  [editor] line {pr.get('line')}: {pr['problem'][:140]}")
    return edited.get("script") or draft


def main():
    cfg = load_config()
    if "--from" in sys.argv:
        job = Path(sys.argv[sys.argv.index("--from") + 1]).resolve()
        sc = json.loads((job / "script.json").read_text())
    else:
        topic = next((a for a in sys.argv[1:] if not a.startswith("--")), None)
        t0 = time.time()
        sc = write_story(cfg, topic)
        print(f"script in {time.time() - t0:.0f}s")
        job = cfg["_root"] / cfg["output_dir"] / f"{date.today():%Y%m%d}-{_slug(sc['title'])}-story"
        job.mkdir(parents=True, exist_ok=True)
        (job / "script.json").write_text(json.dumps(sc, indent=2, ensure_ascii=False))
        (job / "job.json").write_text(json.dumps({"format": "short", "style": "story", "created": time.time()}))
    words = sum(len(ln["text"].split()) for ln in sc["lines"])
    print(f"{sc['title']!r}: {len(sc['lines'])} lines, {words} words")
    for ln in sc["lines"]:
        print("   ", ln["text"])
    t0 = time.time()
    timing = duo.build_audio_and_video(sc, story_cfg(cfg), job)
    meta = {"title": sc["title"], "description": sc["description"], "tags": sc["tags"],
            "format": "short", "duration_s": round(timing[-1]["end"] + 0.6, 1)}
    if "#shorts" not in meta["description"].lower():
        meta["description"] += "\n#shorts"
    (job / "metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"rendered in {time.time() - t0:.0f}s -> {job / 'video.mp4'} ({meta['duration_s']}s)")


if __name__ == "__main__":
    main()
