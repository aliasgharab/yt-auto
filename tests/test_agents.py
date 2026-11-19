import json
import subprocess
from pathlib import Path
from unittest import mock

import pytest

from yt_auto import agents, duo
from yt_auto.config import load_config


@pytest.fixture
def cfg():
    return load_config()


def _cp(stdout="", rc=0, stderr=""):
    return subprocess.CompletedProcess(args=[], returncode=rc, stdout=stdout, stderr=stderr)


def _claude_ok(obj):
    return _cp(json.dumps({"type": "result", "is_error": False, "result": "", "structured_output": obj}))


# ---------------------------------------------------------------- claude plumbing
def test_parse_structured_output():
    assert agents._parse_claude_output(_claude_ok({"a": 1})) == {"a": 1}


def test_parse_fallback_to_result_text():
    out = _cp(json.dumps({"result": "here:\n```json\n{\"b\": 2}\n```"}))
    assert agents._parse_claude_output(out) == {"b": 2}


def test_parse_errors():
    with pytest.raises(RuntimeError):
        agents._parse_claude_output(_cp("", rc=1, stderr="boom"))
    with pytest.raises(RuntimeError):
        agents._parse_claude_output(_cp(json.dumps({"is_error": True, "result": "limit"})))


def test_claude_read_only_flags(cfg, tmp_path):
    with mock.patch.object(agents.subprocess, "run", return_value=_claude_ok({"x": 1})) as run:
        agents._claude("hi", cfg, {"type": "object"}, tools="Read", add_dirs=[tmp_path], cwd=tmp_path)
    cmd = run.call_args.args[0]
    assert cmd[cmd.index("--tools") + 1] == "Read"
    assert cmd[cmd.index("--allowedTools") + 1] == "Read"
    assert cmd[cmd.index("--add-dir") + 1] == str(tmp_path)
    assert run.call_args.kwargs["cwd"] == str(tmp_path)
    assert "--dangerously-skip-permissions" not in cmd


def test_load_prompt_substitutes_and_keeps_braces():
    txt = agents.load_prompt("duo_writer", A="Hiro", B="Baymax", popup_guide='{"type":"title"}')
    assert '"Baymax, ..."' in txt and '{"type":"title"}' in txt


# ---------------------------------------------------------------- research
def test_format_signals_ranks_and_marks_missing():
    sig = [{"source": "hn", "title": "Low", "url": "u1", "score": 5, "comments": 1},
           {"source": "hn", "title": "High", "url": "u2", "score": 500, "comments": 90},
           {"source": "youtube", "title": "Vid", "url": "u3", "views": 1000, "duration": 40, "short": True}]
    txt = agents.format_signals(sig)
    assert txt.index("High") < txt.index("Low")
    assert "(no data: source unavailable)" in txt  # reddit
    assert "1000 views | Short" in txt


def test_dedupe_ideas():
    ideas = [{"title": "Baymax, why does my phone get hot?", "topic": "t", "notes": "n"},
             {"title": "Baymax, why does my phone get hot??", "topic": "t", "notes": "n"},
             {"title": "Baymax, why don't websites know my password?", "topic": "t", "notes": "n"},
             {"title": "Baymax, what is a watchdog?", "topic": "t", "notes": "n"}]
    out = agents.dedupe_ideas(ideas, ["Baymax, why don't websites know my password?"], 5)
    assert [i["title"] for i in out] == ["Baymax, why does my phone get hot?", "Baymax, what is a watchdog?"]
    assert len(agents.dedupe_ideas(ideas, [], 1)) == 1


def test_gather_signals_tolerates_failures(monkeypatch):
    monkeypatch.setattr(agents, "HN_KEYWORDS", ["a"])
    monkeypatch.setattr(agents, "SUBREDDITS", ["embedded"])
    monkeypatch.setattr(agents, "YT_QUERIES", ["q"])
    monkeypatch.setattr(agents, "_hn", lambda k: [{"source": "hn", "title": "T", "url": "u", "score": 1,
                                                   "comments": 0}] * 2)
    monkeypatch.setattr(agents, "_reddit", mock.Mock(side_effect=OSError("403")))
    monkeypatch.setattr(agents, "_youtube", mock.Mock(side_effect=subprocess.TimeoutExpired("x", 1)))
    sig, errs = agents.gather_signals(budget_s=5)
    assert len(sig) == 1 and len(errs) == 2


def test_research_ideas_end_to_end_mocked(cfg, monkeypatch):
    monkeypatch.setattr(agents, "gather_signals", lambda: ([], ["all down"]))
    ideas = [{"title": t, "topic": "x", "notes": "y"} for t in
             ["Baymax, why does my phone get hot?", "Baymax, what is a deadlock?", "Baymax, how do interrupts work?",
              "Baymax, why do games lag?", "Baymax, what is DMA?"]]
    with mock.patch.object(agents.subprocess, "run", return_value=_claude_ok({"ideas": ideas})) as run:
        out = agents.research_ideas(cfg, [], 3)
    assert len(out) == 3
    assert "all sources failed" in run.call_args.kwargs["input"]


# ---------------------------------------------------------------- QA
def test_word_overlap_and_caption_parsers():
    srt = "1\n00:00:00,000 --> 00:00:01,000\nWhy don't websites\n\n2\n00:00:01,000 --> 00:00:02,000\nknow it?\n"
    assert agents.srt_text(srt) == "Why don't websites know it?"
    assert agents.word_overlap("Baymax, why don't websites know it?", agents.srt_text(srt)) == pytest.approx(5 / 6)
    assert agents.word_overlap("", "x") == 0.0
    ass = "Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,{\\c&H00FFFF&}Hello\\Nworld, ok"
    assert agents.ass_text(ass) == "Hello world, ok"


def test_combine_qa():
    ok = [("ok", "fine")]
    assert agents.combine_qa(ok, {"verdict": "pass", "issues": [], "summary": ""})["verdict"] == "pass"
    r = agents.combine_qa(ok, {"verdict": "pass", "issues": [{"frame": "f1", "severity": "warn", "problem": "p"}]})
    assert r["verdict"] == "warn" and "f1: p" in r["notes"]
    assert agents.combine_qa([("fail", "no audio")], {"verdict": "pass", "issues": []})["verdict"] == "fail"
    assert agents.combine_qa([("warn", "x")], None)["verdict"] == "warn"
    assert agents.combine_qa(ok, None, "timeout")["verdict"] == "warn"
    assert agents.combine_qa(ok, {"verdict": "fail", "issues": []})["verdict"] == "fail"


def _fake_job(tmp_path: Path, popups=(0,), captions="Baymax why is the sky blue"):
    job = tmp_path / "job"
    job.mkdir()
    lines = [{"speaker": "Hiro", "text": "Baymax, why is the sky blue?", "popup": {"type": "title"} if 0 in popups else None},
             {"speaker": "Baymax", "text": "Light bounces.", "popup": {"type": "picture"} if 1 in popups else None}]
    (job / "script.json").write_text(json.dumps({"title": "t", "lines": lines}))
    (job / "timing.json").write_text(json.dumps([{"start": 0, "end": 10}, {"start": 10, "end": 24.5}]))
    (job / "captions.srt").write_text(f"1\n00:00:00,000 --> 00:00:01,000\n{captions}\n")
    (job / "video.mp4").write_bytes(b"\0" * 20000)
    (job / "popup_00.png").write_bytes(b"png")
    return job


def _probe(dur=25.0, w=1080, h=1920, audio=True):
    st = [{"codec_type": "video", "width": w, "height": h}] + ([{"codec_type": "audio"}] if audio else [])
    return {"format": {"duration": str(dur)}, "streams": st}


def test_deterministic_checks(tmp_path, monkeypatch):
    job = _fake_job(tmp_path, popups=(0, 1), captions="Baymax why is the sky blue light bounces")
    monkeypatch.setattr(agents, "ffprobe", lambda p: _probe())
    monkeypatch.setattr(agents, "volumedetect", lambda p: {"mean_volume": -20.0, "max_volume": -3.0})
    checks, facts = agents.deterministic_checks(job)
    sev = dict((m.split()[0], s) for s, m in checks)
    assert all(s == "ok" for s, m in checks if not m.startswith("missing")), checks
    assert ("fail", "missing popup images: popup for line 1 (popup_01.png or cards/01/)") in checks
    assert facts["caption_overlap"] == 1.0 and sev["resolution"] == "ok"


def test_deterministic_checks_failures(tmp_path, monkeypatch):
    job = _fake_job(tmp_path, captions="something else entirely")
    monkeypatch.setattr(agents, "ffprobe", lambda p: _probe(dur=70, w=1920, h=1080, audio=True))
    monkeypatch.setattr(agents, "volumedetect", lambda p: {"mean_volume": -91.0, "max_volume": -91.0})
    checks, _ = agents.deterministic_checks(job)
    fails = [m for s, m in checks if s == "fail"]
    assert any("outside 15-60s" in m for m in fails)
    assert any("resolution" in m for m in fails)
    assert any("silent" in m for m in fails)
    assert any("captions cover" in m for m in fails)
    assert any(s == "warn" and "differs from timing.json" in m for s, m in checks)


def test_popup_refs_from_ffmpeg_cmd(tmp_path):
    job = _fake_job(tmp_path)
    (job / "cards" / "00").mkdir(parents=True)
    (job / "cards" / "00" / "0000.png").write_bytes(b"x")
    (job / "ffmpeg_cmd.txt").write_text(
        f"ffmpeg -i /old/place/{job.name}/cards/00/%04d.png -i /old/place/{job.name}/cards/03/%04d.png "
        f"-i /repo/assets/characters/hiro.png")
    refs, missing = agents._popup_refs(job, json.loads((job / "script.json").read_text()))
    assert len(refs) == 2 and missing == ["cards/03/0000.png"]


def test_qa_review_writes_json_and_hard_fail_wins(cfg, tmp_path, monkeypatch):
    job = _fake_job(tmp_path)
    monkeypatch.setattr(agents, "deterministic_checks",
                        lambda j: ([("fail", "no audio stream")], {"duration_s": 25.0}))
    monkeypatch.setattr(agents, "extract_frames", lambda j, d: [(j / "qa_frames" / "frame_01.jpg", 2.0)])
    monkeypatch.setattr(agents, "vision_check", lambda *a: {"verdict": "pass", "issues": [], "summary": "ok"})
    r = agents.qa_review(cfg, job)
    assert r["verdict"] == "fail"
    saved = json.loads((job / "qa.json").read_text())
    assert saved["verdict"] == "fail" and saved["vision"]["summary"] == "ok"


def test_qa_review_vision_error_is_warn(cfg, tmp_path, monkeypatch):
    job = _fake_job(tmp_path)
    monkeypatch.setattr(agents, "deterministic_checks", lambda j: ([("ok", "fine")], {"duration_s": 25.0}))
    monkeypatch.setattr(agents, "extract_frames", lambda j, d: [(j / "f.jpg", 1.0)])
    monkeypatch.setattr(agents, "vision_check", mock.Mock(side_effect=subprocess.TimeoutExpired("claude", 600)))
    r = agents.qa_review(cfg, job)
    assert r["verdict"] == "warn" and "visual check unavailable" in r["notes"]


def test_frame_context():
    sc = {"lines": [{"speaker": "Hiro", "text": "Q?", "popup": {"type": "title"}},
                    {"speaker": "Baymax", "text": "A.", "popup": None}]}
    timing = [{"start": 0, "end": 2}, {"start": 2.1, "end": 5}]
    ctx = agents._frame_context([(Path("frame_01.jpg"), 3.0)], sc, timing)
    assert 'Baymax says "A."' in ctx and "from line 0" in ctx


# ---------------------------------------------------------------- analyze
def test_analyze_small_sample_note(cfg):
    rows = [{"title": "a", "topic": "t", "script": "x y", "duration_s": 25, "views": 100, "likes": 3,
             "avg_view_pct": 80, "avg_view_s": 20, "publish_at": "2026-11-01"},
            {"title": "b", "topic": "t", "script": "x", "duration_s": 30, "views": None}]
    with mock.patch.object(agents.subprocess, "run",
                           return_value=_claude_ok({"guidance_markdown": "## Hooks\n- keep\n"})) as run:
        out = agents.analyze(cfg, rows, "## Hooks\n- keep")
    assert out == "## Hooks\n- keep"
    prompt = run.call_args.kwargs["input"]
    assert "1 of 2 videos have stats" in prompt and "FEWER THAN 5" in prompt and "views=100" in prompt


def test_analyze_enough_data_no_note(cfg):
    rows = [{"title": str(i), "views": 10 * i} for i in range(6)]
    with mock.patch.object(agents.subprocess, "run", return_value=_claude_ok({"guidance_markdown": "g"})) as run:
        agents.analyze(cfg, rows, "")
    assert "FEWER THAN 5" not in run.call_args.kwargs["input"]


# ---------------------------------------------------------------- writer + editor
def _script(n_words_per_line=5):
    return {"topic": "t", "title": "Baymax, why?", "description": "d #shorts", "tags": ["a"],
            "lines": [{"speaker": "Hiro", "text": " ".join(["word"] * n_words_per_line), "popup": {"type": "title"}},
                      {"speaker": "Baymax", "text": "short", "popup": None}]}


def test_write_script_two_separate_passes(cfg):
    draft, fixed = _script(20), _script(5)
    editor = {"problems": [{"category": "line_length", "line": 0, "problem": "20 words", "fix": "cut"}],
              "script": fixed}
    with mock.patch("yt_auto.script._call_claude", side_effect=[draft, editor]) as call:
        sc = duo.write_script(cfg, "watchdogs", ["Old title"], guidance="- name a device",
                              feedback=["too much jargon"])
    assert call.call_count == 2
    writer_prompt, editor_prompt = call.call_args_list[0].args[0], call.call_args_list[1].args[0]
    assert "name a device" in writer_prompt and "too much jargon" in writer_prompt
    assert "tough, experienced script editor" in editor_prompt
    assert "line 0 (20 words)" in editor_prompt  # deterministic facts reach the editor
    assert "required" in call.call_args_list[1].args[2] and "problems" in call.call_args_list[1].args[2]["properties"]
    assert sc["lines"] == fixed["lines"]
    assert sc["editor_notes"] == ["[line_length] line 0: 20 words -> cut"]


def test_write_script_backward_compatible_three_args(cfg):
    with mock.patch("yt_auto.script._call_claude", side_effect=[_script(), {"problems": [], "script": _script()}]):
        sc = duo.write_script(cfg, None, ["A", "B"])
    assert sc["editor_notes"] == []


def test_script_facts_flags_out_of_range(cfg):
    facts = duo.script_facts(_script(20), cfg)
    assert "OUT OF RANGE" in facts and "line 0 (20 words)" in facts
