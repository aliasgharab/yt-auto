import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import httplib2
import pytest
from googleapiclient.errors import HttpError

from yt_auto import youtube as yt


def _http_error(status):
    return HttpError(httplib2.Response({"status": status}), b"{}")


@pytest.fixture
def job(tmp_path):
    (tmp_path / "video.mp4").write_bytes(b"\x00" * 16)
    (tmp_path / "metadata.json").write_text(json.dumps({
        "title": "Why your <code> needs a watchdog timer",
        "description": "A watchdog resets a stuck MCU.\n#shorts",
        "tags": ["embedded", "watchdog timer", "mcu"],
        "format": "short", "duration_s": 29.4,
    }))
    return tmp_path


# --------------------------------------------------------------- body

def test_body_from_metadata(job):
    meta = json.loads((job / "metadata.json").read_text())
    body = yt.build_body(meta, None)
    sn, st = body["snippet"], body["status"]
    assert sn["title"] == "Why your code needs a watchdog timer"  # angle brackets stripped
    assert sn["description"].endswith("#shorts")
    assert sn["tags"] == ["embedded", "watchdog timer", "mcu"]
    assert sn["categoryId"] == "28" and sn["defaultLanguage"] == "en"
    assert st == {"privacyStatus": "private", "selfDeclaredMadeForKids": False,
                  "containsSyntheticMedia": True}


def test_title_truncated_to_100():
    body = yt.build_body({"title": "x" * 150, "description": "", "tags": []}, None)
    assert len(body["snippet"]["title"]) == 100


def test_description_byte_limit():
    body = yt.build_body({"title": "t", "description": "é" * 4000, "tags": []}, None)
    assert len(body["snippet"]["description"].encode()) <= 5000


def _tag_len(tags):
    return sum(len(t) + (2 if " " in t else 0) for t in tags) + max(len(tags) - 1, 0)


def test_tag_budget_trimming():
    tags = [f"tag number {i:03d}" for i in range(100)]  # 14 chars + 2 quotes each
    out = yt.trim_tags(tags)
    assert _tag_len(out) <= 500
    assert out == tags[:len(out)] and len(out) == 29  # 29*16 + 28 = 492; a 30th would be 509


def test_tag_trimming_dedupes_and_skips_oversize():
    out = yt.trim_tags(["RTOS", "rtos", "a" * 600, "", "a,b", "gpio"])
    assert out == ["RTOS", "a b", "gpio"]


def test_publish_at_format():
    dt = datetime(2026, 11, 20, 9, 30, tzinfo=timezone(timedelta(hours=-5)))
    assert yt.format_publish_at(dt) == "2026-11-20T14:30:00Z"
    body = yt.build_body({"title": "t", "tags": []}, dt)
    assert body["status"]["publishAt"] == "2026-11-20T14:30:00Z"
    assert body["status"]["privacyStatus"] == "private"


# --------------------------------------------------------------- upload

class FakeInsert:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)

    def next_chunk(self):
        o = self.outcomes.pop(0)
        if isinstance(o, Exception):
            raise o
        return o


def _fake_service(insert_request):
    svc = MagicMock()
    svc.videos.return_value.insert.return_value = insert_request
    return svc


def test_upload_writes_record_and_is_idempotent(job, monkeypatch):
    req = FakeInsert([(SimpleNamespace(progress=lambda: 0.5), None), (None, {"id": "abc123"})])
    svc = _fake_service(req)
    monkeypatch.setattr(yt, "_youtube", lambda: svc)
    monkeypatch.setattr("googleapiclient.http.MediaFileUpload", MagicMock())
    when = datetime(2026, 11, 21, 15, 0, tzinfo=timezone.utc)

    assert yt.upload(job, when) == "abc123"
    rec = json.loads((job / "upload.json").read_text())
    assert rec == {"video_id": "abc123", "url": "https://www.youtube.com/watch?v=abc123",
                   "publish_at": "2026-11-21T15:00:00Z"}
    kw = svc.videos.return_value.insert.call_args.kwargs
    assert kw["part"] == "snippet,status" and kw["body"]["status"]["publishAt"] == "2026-11-21T15:00:00Z"

    monkeypatch.setattr(yt, "_youtube", lambda: pytest.fail("must not call API again"))
    assert yt.upload(job, when) == "abc123"


def test_thumbnail_only_for_long(job, monkeypatch):
    (job / "thumbnail.jpg").write_bytes(b"jpg")
    monkeypatch.setattr("googleapiclient.http.MediaFileUpload", MagicMock())

    svc = _fake_service(FakeInsert([(None, {"id": "s1"})]))
    monkeypatch.setattr(yt, "_youtube", lambda: svc)
    yt.upload(job, None)
    svc.thumbnails.return_value.set.assert_not_called()
    assert json.loads((job / "upload.json").read_text())["publish_at"] is None

    (job / "upload.json").unlink()
    meta = json.loads((job / "metadata.json").read_text())
    meta["format"] = "long"
    (job / "metadata.json").write_text(json.dumps(meta))
    svc = _fake_service(FakeInsert([(None, {"id": "l1"})]))
    monkeypatch.setattr(yt, "_youtube", lambda: svc)
    yt.upload(job, None)
    svc.thumbnails.return_value.set.assert_called_once()


def test_resumable_retries_5xx_then_succeeds():
    req = FakeInsert([_http_error(503), httplib2.ServerNotFoundError("dns"), (None, {"id": "v"})])
    sleeps = []
    assert yt._execute_resumable(req, sleep=sleeps.append)["id"] == "v"
    assert len(sleeps) == 2


def test_resumable_raises_on_4xx():
    with pytest.raises(HttpError):
        yt._execute_resumable(FakeInsert([_http_error(403)]), sleep=lambda s: None)


# --------------------------------------------------------------- stats

def test_stats_merge_with_missing_analytics(monkeypatch):
    ytsvc = MagicMock()
    ytsvc.videos.return_value.list.return_value.execute.return_value = {"items": [
        {"id": "a", "statistics": {"viewCount": "120", "likeCount": "9"}},
        {"id": "b", "statistics": {"viewCount": "5"}},  # likes hidden
    ]}
    an = MagicMock()
    an.reports.return_value.query.return_value.execute.return_value = {
        "columnHeaders": [{"name": "video"}, {"name": "views"},
                          {"name": "averageViewDuration"}, {"name": "averageViewPercentage"}],
        "rows": [["a", 118, 21, 72.5]],  # b too new for analytics; c unknown
    }
    monkeypatch.setattr(yt, "_youtube", lambda: ytsvc)
    monkeypatch.setattr(yt, "_analytics", lambda: an)

    out = yt.fetch_stats(["a", "b", "c"])
    assert out["a"] == {"views": 120, "likes": 9, "avg_view_pct": 72.5, "avg_view_s": 21.0}
    assert out["b"] == {"views": 5, "likes": None, "avg_view_pct": None, "avg_view_s": None}
    assert out["c"] == {"views": None, "likes": None, "avg_view_pct": None, "avg_view_s": None}
    q = an.reports.return_value.query.call_args.kwargs
    assert q["ids"] == "channel==MINE" and q["dimensions"] == "video"
    assert q["filters"] == "video==a,b,c"


def test_stats_never_crash(monkeypatch):
    def boom():
        raise RuntimeError("no creds")
    monkeypatch.setattr(yt, "_youtube", boom)
    monkeypatch.setattr(yt, "_analytics", boom)
    assert yt.fetch_stats(["a"]) == {"a": {"views": None, "likes": None,
                                           "avg_view_pct": None, "avg_view_s": None}}
    assert yt.fetch_stats([]) == {}


def test_analytics_filter_rejected_falls_back(monkeypatch):
    monkeypatch.setattr(yt, "_youtube", lambda: MagicMock(**{
        "videos.return_value.list.return_value.execute.return_value": {"items": []}}))
    an = MagicMock()
    resp = {"columnHeaders": [{"name": "video"}, {"name": "averageViewDuration"},
                              {"name": "averageViewPercentage"}], "rows": [["a", 10, 50.0]]}
    an.reports.return_value.query.return_value.execute.side_effect = [_http_error(400), resp]
    monkeypatch.setattr(yt, "_analytics", lambda: an)
    assert yt.fetch_stats(["a"])["a"]["avg_view_pct"] == 50.0
    assert "filters" not in an.reports.return_value.query.call_args.kwargs


# --------------------------------------------------------------- config

def test_is_configured(tmp_path, monkeypatch):
    monkeypatch.setattr(yt, "CLIENT_SECRET", tmp_path / "client_secret.json")
    monkeypatch.setattr(yt, "TOKEN", tmp_path / "youtube_token.json")
    assert not yt.is_configured()
    (tmp_path / "client_secret.json").write_text("{}")
    assert not yt.is_configured()
    (tmp_path / "youtube_token.json").write_text("{}")
    assert yt.is_configured()


def test_cli_registers():
    import argparse
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    yt.register(sub)
    assert ap.parse_args(["youtube-check"]).cmd == "youtube-check"
    assert yt.run("make") is False
