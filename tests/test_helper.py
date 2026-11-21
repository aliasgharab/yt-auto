"""Free helper LLM: JSON extraction, schema check, and falling back (None) on any problem."""
import stat

from yt_auto import helper

SCHEMA = {"type": "object", "required": ["ideas"], "properties": {"ideas": {"type": "array", "items": {
    "type": "object", "required": ["title"], "properties": {"title": {"type": "string", "maxLength": 20}}}}}}
CFG = {"llm": {"helper": {"tasks": ["research"]}}}


def test_extract_json_tolerates_chatter_and_fences():
    assert helper.extract_json('Sure!\n```json\n{"a": {"b": 1}}\n```\nDone') == {"a": {"b": 1}}
    assert helper.extract_json("no json here") is None


def test_valid_schema_subset():
    assert helper.valid({"ideas": [{"title": "x"}]}, SCHEMA)
    assert not helper.valid({"ideas": [{}]}, SCHEMA)                      # missing required
    assert not helper.valid({"ideas": [{"title": "x" * 30}]}, SCHEMA)     # too long
    assert not helper.valid({"ideas": "x"}, SCHEMA)                       # wrong type
    assert helper.valid({"v": None}, {"properties": {"v": {"type": ["integer", "null"]}}})


def _fake_opencode(tmp_path, monkeypatch, output, rc=0):
    exe = tmp_path / "opencode"
    exe.write_text(f"#!/bin/sh\ncat <<'X'\n{output}\nX\nexit {rc}\n")
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("OPENCODE_BIN", str(exe))
    monkeypatch.setenv("YT_HELPER", "1")


def test_call_json_success(tmp_path, monkeypatch):
    _fake_opencode(tmp_path, monkeypatch, '> build · model\n{"ideas": [{"title": "DMA"}]}')
    assert helper.call_json("p", SCHEMA, CFG, "research") == {"ideas": [{"title": "DMA"}]}


def test_call_json_falls_back(tmp_path, monkeypatch):
    _fake_opencode(tmp_path, monkeypatch, '{"ideas": [{"nope": 1}]}')
    assert helper.call_json("p", SCHEMA, CFG, "research") is None           # schema mismatch
    _fake_opencode(tmp_path, monkeypatch, 'rate limited', rc=1)
    assert helper.call_json("p", SCHEMA, CFG, "research") is None           # failure
    assert helper.call_json("p", SCHEMA, CFG, "analyze") is None            # task not enabled
    monkeypatch.setenv("YT_HELPER", "0")
    _fake_opencode(tmp_path, monkeypatch, '{"ideas": []}')
    monkeypatch.setenv("YT_HELPER", "0")
    assert helper.call_json("p", SCHEMA, CFG, "research") is None           # switched off
