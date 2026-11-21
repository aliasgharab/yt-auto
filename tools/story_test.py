"""Story-format test Short (DripDyl-style): one first-person narrator, 60-90 s, "In this world..."
premise built on a real tech concept, twist ending, one big yellow word on screen at a time.
Same visuals as the daily Shorts (gameplay, cards, character). Does not change the daily pipeline.

  .venv/bin/python tools/story_test.py ["topic"]        # write + render -> out/<date>-<slug>-story/
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

from yt_auto import _slug, cards, duo, script  # noqa: E402
from yt_auto.agents import load_prompt  # noqa: E402
from yt_auto.config import load_config  # noqa: E402

NARRATOR = "Hiro"
WORDS, LINES = (150, 200), (12, 22)


def story_cfg(cfg):
    c = copy.deepcopy(cfg)
    c["duo"].update(max_seconds=90, captions="single")
    return c


def write_story(cfg, topic):
    ch = cfg["duo"]["characters"][NARRATOR]
    topic_line = (f"CONCEPT: {topic}" if topic else
                  f"CONCEPT: pick ONE specific concept from this niche: {cfg['channel']['niche']}")
    prompt = load_prompt("story_writer", N=NARRATOR, N_personality=ch["personality"], topic_line=topic_line,
                         lo_w=WORDS[0], hi_w=WORDS[1], lo_l=LINES[0], hi_l=LINES[1],
                         popup_guide=cards.POPUP_GUIDE)
    return script._call_claude(prompt, cfg, duo._schema([NARRATOR]))


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
