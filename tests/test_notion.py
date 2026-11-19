import io
import json
import urllib.error
from datetime import date, datetime, timezone

import pytest

from yt_auto import notion
from yt_auto.notion import Notion, from_page, to_props

SETTINGS = {"token": "secret_TOKEN", "database_id": "db1", "what_works_page_id": "ww1"}


def test_to_props_mapping():
    p = to_props({"Title": "Hi", "Status": "Idea", "Approve": True, "Topic": "x", "Duration (s)": 27,
                  "Publish At": datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc), "YouTube URL": None,
                  "QA": None, "Stats Updated": date(2026, 11, 19), "_id": "ignored"})
    assert p["Title"] == {"title": [{"type": "text", "text": {"content": "Hi"}}]}
    assert p["Status"] == {"select": {"name": "Idea"}}
    assert p["Approve"] == {"checkbox": True}
    assert p["Topic"]["rich_text"][0]["text"]["content"] == "x"
    assert p["Duration (s)"] == {"number": 27.0}
    assert p["Publish At"] == {"date": {"start": "2026-11-20T12:00:00+00:00"}}
    assert p["YouTube URL"] == {"url": None}
    assert p["QA"] == {"select": None}
    assert p["Stats Updated"] == {"date": {"start": "2026-11-19"}}
    assert "_id" not in p
    with pytest.raises(KeyError):
        to_props({"Nope": 1})
    with pytest.raises(ValueError):
        to_props({"Created": "x"})


def test_rich_text_chunked_at_2000():
    p = to_props({"QA Notes": "a" * 4500})["QA Notes"]["rich_text"]
    assert [len(x["text"]["content"]) for x in p] == [2000, 2000, 500]
    assert to_props({"Feedback": ""})["Feedback"] == {"rich_text": []}


def test_from_page_roundtrip():
    values = {"Title": "T", "Status": "Scheduled", "Reject": False, "Video ID": "abc", "Views": 12.0,
              "Publish At": datetime(2026, 11, 20, 17, 0, tzinfo=timezone.utc), "Feedback": "b" * 2500}
    props = to_props(values)
    for v in props.values():  # Notion adds `type` and plain_text in responses
        v["type"] = next(iter(v))
        for rt in v.get("title") or v.get("rich_text") or []:
            rt["plain_text"] = rt["text"]["content"]
    props["Created"] = {"type": "created_time", "created_time": "2026-11-19T07:00:00.000Z"}
    row = from_page({"id": "p1", "url": "https://notion.so/p1", "properties": props})
    assert row["_id"] == "p1" and row["_url"] == "https://notion.so/p1"
    for k, v in values.items():
        assert row[k] == v, k
    assert row["Created"] == datetime(2026, 11, 19, 7, 0, tzinfo=timezone.utc)


class FakeHTTP:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, req, timeout=None):
        self.requests.append(req)
        status, body = self.responses.pop(0)
        if status != 200:
            raise urllib.error.HTTPError(req.full_url, status, "err", {"Retry-After": "0"},
                                         io.BytesIO(json.dumps(body).encode()))
        return io.BytesIO(json.dumps(body).encode())


def page(i, status="Idea"):
    return {"id": f"p{i}", "url": f"u{i}", "properties": {
        "Title": {"type": "title", "title": [{"plain_text": f"t{i}"}]},
        "Status": {"type": "select", "select": {"name": status}}}}


def test_query_paginates_and_filters():
    http = FakeHTTP([(200, {"results": [page(1)], "has_more": True, "next_cursor": "c2"}),
                     (200, {"results": [page(2)], "has_more": False})])
    rows = Notion(SETTINGS, opener=http, sleep=lambda s: None).query(["Idea", "Scheduled"])
    assert [r["Title"] for r in rows] == ["t1", "t2"]
    b1, b2 = (json.loads(r.data) for r in http.requests)
    assert b1["filter"] == {"or": [{"property": "Status", "select": {"equals": "Idea"}},
                                   {"property": "Status", "select": {"equals": "Scheduled"}}]}
    assert "start_cursor" not in b1 and b2["start_cursor"] == "c2"
    req = http.requests[0]
    assert req.full_url.endswith("/databases/db1/query")
    assert req.get_header("Notion-version") == "2022-06-28"


def test_429_retry():
    sleeps = []
    http = FakeHTTP([(429, {"code": "rate_limited"}), (200, {"results": [], "has_more": False})])
    assert Notion(SETTINGS, opener=http, sleep=sleeps.append).query("Idea") == []
    assert len(http.requests) == 2 and len(sleeps) == 1


def test_404_means_not_connected_and_token_hidden():
    http = FakeHTTP([(404, {"code": "object_not_found", "message": "Could not find database"})])
    nc = Notion(SETTINGS, opener=http, sleep=lambda s: None)
    with pytest.raises(notion.NotionNotConnected) as e:
        nc.check()
    assert "Connections" in str(e.value) and "secret_TOKEN" not in str(e.value)
    assert "secret_TOKEN" not in repr(nc)


def test_update_row_patch():
    http = FakeHTTP([(200, page(1, "Rejected"))])
    row = Notion(SETTINGS, opener=http).update_row("p1", {"Status": "Rejected"})
    assert row["Status"] == "Rejected"
    assert http.requests[0].get_method() == "PATCH" and http.requests[0].full_url.endswith("/pages/p1")


def test_page_text_roundtrip():
    text = "# What Works\n## Hooks\n- Ask a question first\n- [ ] try longer\n1. step\nPlain para\n> quote\n---\n"
    blocks = notion.text_to_blocks(text)
    for b in blocks:  # mimic API response plain_text
        for rt in b[b["type"]].get("rich_text", []):
            rt["plain_text"] = rt["text"]["content"]
    assert notion.blocks_to_text(blocks) == text


def test_replace_page_text_deletes_then_appends():
    old = {"results": [{"id": "b1", "type": "paragraph"}, {"id": "b2", "type": "child_page"}], "has_more": False}
    http = FakeHTTP([(200, old), (200, {}), (200, {})])
    Notion(SETTINGS, opener=http).replace_page_text("# New\n- one")
    methods = [(r.get_method(), r.full_url.split("/v1")[1]) for r in http.requests]
    assert methods == [("GET", "/blocks/ww1/children?page_size=100"), ("DELETE", "/blocks/b1"),
                       ("PATCH", "/blocks/ww1/children")]
    assert len(json.loads(http.requests[2].data)["children"]) == 2
