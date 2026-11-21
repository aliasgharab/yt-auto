import sys
import types
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


class FakeNotion:
    """In-memory stand-in for yt_auto.notion.Notion (rows keyed by property name)."""

    def __init__(self, rows=None):
        self.rows = []
        self.page = ""
        self.log = []
        for r in rows or []:
            self.create_row(r)

    def query(self, statuses=None, filter=None, newest_first=False):
        if isinstance(statuses, str):
            statuses = [statuses]
        rows = [dict(r) for r in self.rows if not statuses or r.get("Status") in statuses]
        return rows[::-1] if newest_first else rows

    def create_row(self, values):
        rid = uuid.uuid4().hex
        row = {"_id": rid, "_url": f"https://notion.so/{rid}", "Approve": False, "Reject": False, **values}
        self.rows.append(row)
        self.log.append(("create", rid, dict(values)))
        return dict(row)

    def update_row(self, rid, values):
        row = next(r for r in self.rows if r["_id"] == rid)
        row.update(values)
        self.log.append(("update", rid, dict(values)))
        return dict(row)

    def read_page_text(self, page_id=None):
        return self.page

    def replace_page_text(self, text, page_id=None):
        self.page = text


@pytest.fixture
def fake_notion():
    return FakeNotion


@pytest.fixture(autouse=True)
def no_push(monkeypatch):
    from yt_auto import notify
    sent = []
    monkeypatch.setattr(notify, "send", lambda *a, **k: sent.append((a, k)) or True)
    return sent


@pytest.fixture
def cfg(tmp_path):
    return {"_root": tmp_path, "output_dir": "out",
            "publish": {"timezone": "America/Toronto", "slots": ["12:00", "19:00"], "min_lead_hours": 1,
                        "auto_approve": False, "shorts_per_night": 2}}


@pytest.fixture
def fake_module(monkeypatch):
    def install(name, **attrs):
        m = types.ModuleType(f"yt_auto.{name}")
        for k, v in attrs.items():
            setattr(m, k, v)
        monkeypatch.setitem(sys.modules, f"yt_auto.{name}", m)
        return m
    return install


@pytest.fixture(autouse=True)
def _no_real_helper(monkeypatch):
    """Never call the real free-model helper (opencode) from tests."""
    monkeypatch.setenv("YT_HELPER", "0")
