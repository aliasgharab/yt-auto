"""Stage 1+2: topic selection, script writing and fact-check, via Claude."""

import json
import re
import subprocess

VISUAL_TYPES = ["title", "bullets", "code", "stat", "compare", "flow"]

SCRIPT_SCHEMA = {
    "type": "object",
    "required": ["topic", "title", "description", "tags", "thumbnail_text", "scenes"],
    "properties": {
        "topic": {"type": "string"},
        "title": {"type": "string", "maxLength": 100},
        "description": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "thumbnail_text": {"type": "string", "description": "2-5 punchy words for the thumbnail"},
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["narration", "visual"],
                "properties": {
                    "narration": {"type": "string"},
                    "visual": {
                        "type": "object",
                        "required": ["type"],
                        "properties": {
                            "type": {"enum": VISUAL_TYPES},
                            "heading": {"type": "string"},
                            "sub": {"type": "string"},
                            "bullets": {"type": "array", "items": {"type": "string"}},
                            "language": {"type": "string"},
                            "code": {"type": "string"},
                            "value": {"type": "string"},
                            "label": {"type": "string"},
                            "left": {"type": "object", "properties": {
                                "heading": {"type": "string"},
                                "points": {"type": "array", "items": {"type": "string"}}}},
                            "right": {"type": "object", "properties": {
                                "heading": {"type": "string"},
                                "points": {"type": "array", "items": {"type": "string"}}}},
                            "nodes": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
            },
        },
    },
}

VISUAL_GUIDE = """Visual types (pick the one that best SHOWS what the narration says; vary them):
- title:   {"type":"title","heading":"...","sub":"..."}            -- openers / section breaks
- bullets: {"type":"bullets","heading":"...","bullets":["..",".."]} -- 2-4 bullets, <= 7 words each; revealed one by one
- code:    {"type":"code","heading":"...","language":"c","code":"..."} -- <= 12 lines, <= 38 chars/line, real, correct code
- stat:    {"type":"stat","value":"3,000,000,000","label":"transistor switches per second"} -- one striking number
- compare: {"type":"compare","heading":"...","left":{"heading":"..","points":[..]},"right":{"heading":"..","points":[..]}}
- flow:    {"type":"flow","heading":"...","nodes":["Fetch","Decode","Execute"]} -- 2-5 steps of a process, <= 3 words each
"""


def _call_claude(prompt: str, cfg: dict, schema: dict | None = None) -> dict:
    llm = cfg["llm"]
    if llm["backend"] == "claude-cli":
        cmd = ["claude", "-p", "--output-format", "json", "--model", llm["model"],
               "--json-schema", json.dumps(schema or SCRIPT_SCHEMA), "--tools", "",
               "--no-session-persistence"]
        res = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=900)
        if res.returncode != 0:
            raise RuntimeError(f"claude CLI failed: {res.stderr[-2000:]}")
        out = json.loads(res.stdout)
        if isinstance(out.get("structured_output"), dict):
            return out["structured_output"]
        return _extract_json(out.get("result", ""))
    raise ValueError(f"unknown llm backend {llm['backend']}")


def _extract_json(text: str) -> dict:
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    return json.loads(m.group(1) if m else text[text.find("{"): text.rfind("}") + 1])


def write_script(cfg: dict, fmt: str, topic: str | None, past_titles: list[str]) -> dict:
    f = cfg["formats"][fmt]
    lo_w, hi_w = f["target_words"]
    lo_s, hi_s = f["scenes"]
    ch = cfg["channel"]
    topic_line = (f"TOPIC: {topic}" if topic else
                  "TOPIC: choose one specific, curiosity-driving topic yourself. Avoid these already-made videos:\n"
                  + "\n".join(f"- {t}" for t in past_titles[-60:]))
    kind = ("a YouTube Short (vertical, fast-paced, no intro, loopable ending)" if fmt == "short"
            else "a long-form YouTube video (horizontal; hook, then clear sections, recap, soft CTA)")
    prompt = f"""You write scripts for a faceless tech-explainer YouTube channel.
CHANNEL NICHE: {ch['niche']}
NARRATOR TONE: {ch['voice_tone']}

Write {kind}.
{topic_line}

Hard requirements:
- Total narration {lo_w}-{hi_w} words across {lo_s}-{hi_s} scenes.
- First scene's narration is a hook that creates a question in the first 3 seconds. No "In this video", no "Hey guys".
- Every claim must be technically accurate. Prefer concrete numbers, real mechanisms, real examples over vague hype.
- Narration is spoken by TTS: write numbers/units the way they should be SAID ("three gigahertz"), spell out
  symbols, avoid parentheses, avoid emoji, keep sentences under 25 words.
- Each scene's visual must directly illustrate that scene's narration. On-screen text is short; narration carries detail.
- Title: honest, curiosity-driven, <= 70 chars, no clickbait lies. Description: 2-3 sentences + 3 hashtags.
- 8-15 tags. thumbnail_text: 2-5 words.

{VISUAL_GUIDE}"""
    script = _call_claude(prompt, cfg)
    return fact_check(script, cfg, fmt)


def fact_check(script: dict, cfg: dict, fmt: str) -> dict:
    prompt = f"""You are a strict technical fact-checker and editor for a tech-explainer YouTube channel.
Review this {fmt} script JSON. Fix any factual errors, misleading simplifications, buggy code,
on-screen text that is too long, or narration that will sound awkward through text-to-speech.
Keep the structure, length and voice. Return the full corrected script JSON (same schema).

{json.dumps(script, indent=1)}"""
    return _call_claude(prompt, cfg)
