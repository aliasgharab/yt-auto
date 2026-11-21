"""Free helper LLM first, Claude as the fallback (saves Claude subscription usage).

call_json(prompt, schema, cfg, task) runs opencode's free model (no account, no key) and returns a
dict that matches `schema`, or None on ANY problem (opencode missing, timeout, rate limit, bad JSON,
schema mismatch, task not enabled), so callers do:   helper.call_json(...) or claude(...)

config.yaml:
  llm:
    helper:
      model: opencode/deepseek-v4.1-flash-free
      tasks: [editor, story_editor, research, analyze]     # [] = Claude only
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

DEFAULT_MODEL = "opencode/deepseek-v4.1-flash-free"
ASK = ("Follow the instructions in the attached file exactly. Reply with ONLY the JSON object it asks "
       "for: no prose, no explanation, no code fences.")


def _bin() -> str | None:
    for c in (os.environ.get("OPENCODE_BIN"), str(Path.home() / ".opencode/bin/opencode"), shutil.which("opencode")):
        if c and Path(c).is_file() and os.access(c, os.X_OK):
            return c
    return None


def _clean(out: str) -> str:
    out = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", out)
    return re.sub(r"<think>.*?</think>\s*", "", out, flags=re.S)


def extract_json(text: str) -> dict | None:
    """The first complete top-level JSON object in text (tolerates fences and chatter around it)."""
    dec = json.JSONDecoder()
    for m in re.finditer(r"\{", text):
        try:
            obj, _ = dec.raw_decode(text[m.start():])
        except ValueError:
            continue
        if isinstance(obj, dict):
            return obj
    return None


_TYPES = {"object": dict, "array": list, "string": str, "number": (int, float), "integer": int, "boolean": bool}


def valid(obj, schema: dict) -> bool:
    """Small JSON-schema subset: type, required, properties, items, enum, maxLength."""
    t = schema.get("type")
    types = t if isinstance(t, list) else [t] if t else []
    if types and not any(obj is None if x == "null" else isinstance(obj, _TYPES[x]) and not
                         (x in ("number", "integer") and isinstance(obj, bool)) for x in types):
        return False
    if "enum" in schema and obj not in schema["enum"]:
        return False
    if isinstance(obj, str) and len(obj) > schema.get("maxLength", 10**9):
        return False
    if isinstance(obj, dict):
        if any(k not in obj for k in schema.get("required", [])):
            return False
        return all(valid(obj[k], s) for k, s in schema.get("properties", {}).items() if k in obj)
    if isinstance(obj, list) and "items" in schema:
        return all(valid(x, schema["items"]) for x in obj)
    return True


def enabled(cfg: dict, task: str) -> bool:
    h = (cfg.get("llm") or {}).get("helper") or {}
    return task in (h.get("tasks") or []) and os.environ.get("YT_HELPER", "1") != "0"


def call_json(prompt: str, schema: dict, cfg: dict, task: str, timeout: int = 420) -> dict | None:
    if not enabled(cfg, task):
        return None
    oc = _bin()
    if not oc:
        print(f"[helper] {task}: opencode not installed -> Claude", flush=True)
        return None
    model = ((cfg.get("llm") or {}).get("helper") or {}).get("model") or DEFAULT_MODEL
    schema_note = "\n\nThe reply must be ONE JSON object matching this JSON schema:\n" + json.dumps(schema)
    t0 = time.time()
    with tempfile.TemporaryDirectory() as td:
        pf = Path(td) / "task.md"
        pf.write_text(prompt + schema_note)
        try:
            res = subprocess.run([oc, "run", "-m", model, "-f", str(pf), "--", ASK], cwd=td, stdin=subprocess.DEVNULL,
                                 capture_output=True, text=True, timeout=timeout)
        except (subprocess.TimeoutExpired, OSError) as e:
            print(f"[helper] {task}: {type(e).__name__} -> Claude", flush=True)
            return None
    obj = extract_json(_clean(res.stdout)) if res.returncode == 0 else None
    if obj is None or not valid(obj, schema):
        why = f"exit {res.returncode}" if res.returncode else ("no JSON" if obj is None else "schema mismatch")
        print(f"[helper] {task}: {why} after {time.time() - t0:.0f}s -> Claude", flush=True)
        return None
    print(f"[helper] {task}: done by {model} in {time.time() - t0:.0f}s (Claude saved)", flush=True)
    return obj
