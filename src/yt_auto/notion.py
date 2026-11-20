"""Tiny Notion REST client (stdlib only) for the "Content Pipeline" database + "What Works" page.

Config: ~/.config/yt-auto/notion.json  {token, database_id, data_source_id, what_works_page_id, parent_page_id}
The token is never printed or logged.

Rows are plain dicts keyed by the exact Notion property names, with friendly Python values
(str / bool / float / datetime / date / None), plus "_id" (page id) and "_url" (page link).
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

from .config import config_dir

log = logging.getLogger(__name__)

API = "https://api.notion.com/v1"
VERSION = "2022-06-28"
CONFIG_PATH = config_dir() / "notion.json"   # YT_AUTO_CONFIG_DIR overrides the dir
TEXT_LIMIT = 2000          # Notion rich_text content limit per element
MAX_RETRIES = 5

STATUSES = ["Idea", "Scripted", "Rendered", "Needs Approval", "Scheduled", "Live", "Rejected", "Failed"]

# exact property names -> Notion property type
PROPS: dict[str, str] = {
    "Title": "title",
    "Status": "select",
    "Approve": "checkbox",
    "Reject": "checkbox",
    "Topic": "rich_text",
    "Format": "select",
    "Source": "select",
    "Idea Notes": "rich_text",
    "Job": "rich_text",
    "QA": "select",
    "QA Notes": "rich_text",
    "Duration (s)": "number",
    "Feedback": "rich_text",
    "Publish At": "date",
    "YouTube URL": "url",
    "Video ID": "rich_text",
    "Views": "number",
    "Likes": "number",
    "Avg View %": "number",
    "Avg View (s)": "number",
    "Stats Updated": "date",
    "Created": "created_time",
}

NOT_CONNECTED = (
    "Notion returned 404 object_not_found: the yt-auto integration is not connected to the database/page. "
    "In Notion open the \"YouTube Automation\" page -> ••• (top right) -> Connections -> add the yt-auto "
    "integration, then retry."
)


class NotionError(RuntimeError):
    pass


class NotionNotConnected(NotionError):
    pass


def load_settings(path: Path = CONFIG_PATH) -> dict:
    if not path.exists():
        raise NotionError(f"missing Notion config {path} (keys: token, database_id, what_works_page_id)")
    return json.loads(path.read_text())


# ---------------------------------------------------------------- value mapping

def _rich_text(s: str | None) -> list[dict]:
    s = "" if s is None else str(s)
    return [{"type": "text", "text": {"content": s[i:i + TEXT_LIMIT]}} for i in range(0, len(s), TEXT_LIMIT)]


def _plain(rt: list[dict] | None) -> str:
    return "".join(r.get("plain_text") or r.get("text", {}).get("content", "") for r in rt or [])


def _date_out(v) -> dict | None:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        if v.tzinfo is None:
            v = v.astimezone()   # treat naive as local time
        return {"start": v.isoformat(timespec="seconds")}
    if isinstance(v, date):
        return {"start": v.isoformat()}
    return {"start": str(v)}


def parse_date(s: str | None) -> datetime | date | None:
    if not s:
        return None
    if "T" not in s:
        return date.fromisoformat(s)
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def to_props(values: dict) -> dict:
    """Friendly {name: value} -> Notion `properties` payload. Unknown names raise KeyError."""
    out = {}
    for name, v in values.items():
        if name.startswith("_"):
            continue
        t = PROPS[name]
        if t == "title":
            out[name] = {"title": _rich_text(v)}
        elif t == "rich_text":
            out[name] = {"rich_text": _rich_text(v)}
        elif t == "select":
            out[name] = {"select": {"name": str(v)} if v not in (None, "") else None}
        elif t == "checkbox":
            out[name] = {"checkbox": bool(v)}
        elif t == "number":
            out[name] = {"number": None if v is None else float(v)}
        elif t == "date":
            out[name] = {"date": _date_out(v)}
        elif t == "url":
            out[name] = {"url": v or None}
        else:
            raise ValueError(f"property {name!r} ({t}) is read-only")
    return out


def from_page(page: dict) -> dict:
    """Notion page object -> friendly dict."""
    row = {"_id": page["id"], "_url": page.get("url", "")}
    for name, p in page.get("properties", {}).items():
        t = p.get("type")
        v = p.get(t)
        if t in ("title", "rich_text"):
            row[name] = _plain(v)
        elif t == "select":
            row[name] = v["name"] if v else None
        elif t == "checkbox":
            row[name] = bool(v)
        elif t == "number":
            row[name] = v
        elif t == "date":
            row[name] = parse_date(v["start"]) if v else None
        elif t == "url":
            row[name] = v
        elif t == "created_time":
            row[name] = parse_date(v)
        else:
            row[name] = v
    return row


# ---------------------------------------------------------------- page body <-> text

_BLOCK_PREFIX = [("heading_1", "# "), ("heading_2", "## "), ("heading_3", "### "),
                 ("bulleted_list_item", "- "), ("numbered_list_item", "1. "), ("quote", "> ")]


def blocks_to_text(blocks: list[dict]) -> str:
    lines = []
    for b in blocks:
        t = b.get("type")
        body = b.get(t, {}) or {}
        text = _plain(body.get("rich_text"))
        prefix = dict(_BLOCK_PREFIX).get(t)
        if prefix:
            lines.append(prefix + text)
        elif t == "to_do":
            lines.append(("- [x] " if body.get("checked") else "- [ ] ") + text)
        elif t == "code":
            lines.append("```\n" + text + "\n```")
        elif t == "divider":
            lines.append("---")
        elif t == "paragraph":
            lines.append(text)
    return "\n".join(lines).strip() + "\n" if lines else ""


def _block(t: str, text: str, **extra) -> dict:
    return {"object": "block", "type": t, t: {"rich_text": _rich_text(text), **extra}}


def text_to_blocks(text: str) -> list[dict]:
    blocks, code = [], None
    for line in text.splitlines():
        if code is not None:
            if line.strip().startswith("```"):
                blocks.append(_block("code", "\n".join(code), language="plain text"))
                code = None
            else:
                code.append(line)
            continue
        s = line.rstrip()
        if not s.strip():
            continue
        if s.strip().startswith("```"):
            code = []
        elif s.strip() == "---":
            blocks.append({"object": "block", "type": "divider", "divider": {}})
        elif s.startswith("### "):
            blocks.append(_block("heading_3", s[4:]))
        elif s.startswith("## "):
            blocks.append(_block("heading_2", s[3:]))
        elif s.startswith("# "):
            blocks.append(_block("heading_1", s[2:]))
        elif s.lstrip().startswith(("- [ ] ", "- [x] ")):
            st = s.lstrip()
            blocks.append(_block("to_do", st[6:], checked=st.startswith("- [x]")))
        elif s.lstrip().startswith(("- ", "* ")):
            blocks.append(_block("bulleted_list_item", s.lstrip()[2:]))
        elif s.lstrip()[:1].isdigit() and ". " in s.lstrip()[:5]:
            st = s.lstrip()
            blocks.append(_block("numbered_list_item", st[st.index(". ") + 2:]))
        elif s.startswith("> "):
            blocks.append(_block("quote", s[2:]))
        else:
            blocks.append(_block("paragraph", s))
    if code is not None:
        blocks.append(_block("code", "\n".join(code), language="plain text"))
    return blocks


# ---------------------------------------------------------------- client

class Notion:
    def __init__(self, settings: dict | None = None, opener=None, sleep=time.sleep):
        self.s = settings if settings is not None else load_settings()
        self._open = opener or urllib.request.urlopen
        self._sleep = sleep

    def __repr__(self):  # never expose the token
        return f"<Notion db={self.s.get('database_id', '?')[:8]}…>"

    @property
    def database_id(self) -> str:
        return self.s["database_id"]

    def request(self, method: str, path: str, body: dict | None = None) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        for attempt in range(MAX_RETRIES + 1):
            req = urllib.request.Request(API + path, data=data, method=method, headers={
                "Authorization": f"Bearer {self.s['token']}",
                "Notion-Version": VERSION,
                "Content-Type": "application/json",
            })
            try:
                with self._open(req, timeout=60) as r:
                    raw = r.read()
                    return json.loads(raw) if raw else {}
            except urllib.error.HTTPError as e:
                try:
                    err = json.loads(e.read() or b"{}")
                except ValueError:
                    err = {}
                code = err.get("code", "")
                if e.code == 429 or (e.code >= 500 and attempt < MAX_RETRIES):
                    if attempt >= MAX_RETRIES:
                        raise NotionError(f"Notion {method} {path}: rate limited, gave up") from None
                    wait = float(e.headers.get("Retry-After") or 0) if e.headers else 0
                    wait = wait or min(2 ** attempt, 30)
                    log.warning("Notion %s %s -> %s, retrying in %.0fs", method, path, e.code, wait)
                    self._sleep(wait)
                    continue
                if e.code == 404 and code == "object_not_found":
                    raise NotionNotConnected(NOT_CONNECTED) from None
                raise NotionError(f"Notion {method} {path} -> {e.code} {code}: {err.get('message', '')}") from None
            except urllib.error.URLError as e:
                if attempt >= MAX_RETRIES:
                    raise NotionError(f"Notion {method} {path}: {e.reason}") from None
                self._sleep(min(2 ** attempt, 30))
        raise NotionError("unreachable")

    # ---- database rows
    def query(self, statuses: list[str] | str | None = None, filter: dict | None = None,
              newest_first: bool = False) -> list[dict]:
        if isinstance(statuses, str):
            statuses = [statuses]
        f = filter
        if statuses:
            sf = [{"property": "Status", "select": {"equals": s}} for s in statuses]
            sf = sf[0] if len(sf) == 1 else {"or": sf}
            f = {"and": [sf, filter]} if filter else sf
        body: dict = {"page_size": 100, "sorts": [
            {"timestamp": "created_time", "direction": "descending" if newest_first else "ascending"}]}
        if f:
            body["filter"] = f
        rows = []
        while True:
            res = self.request("POST", f"/databases/{self.database_id}/query", body)
            rows += [from_page(p) for p in res.get("results", [])]
            if not res.get("has_more"):
                return rows
            body["start_cursor"] = res["next_cursor"]

    def create_row(self, values: dict) -> dict:
        page = self.request("POST", "/pages", {"parent": {"database_id": self.database_id},
                                               "properties": to_props(values)})
        return from_page(page)

    def update_row(self, page_id: str, values: dict) -> dict:
        page = self.request("PATCH", f"/pages/{page_id}", {"properties": to_props(values)})
        return from_page(page)

    def ensure_props(self, props: dict[str, str]) -> list[str]:
        """Add missing database columns {name: type} (number / rich_text / select / checkbox / date / url).
        Existing columns are never changed. Returns the names added."""
        PROPS.update({k: v for k, v in props.items() if k not in PROPS})
        if getattr(self, "_ensured", None) is not None and set(props) <= self._ensured:
            return []
        have = set(self.request("GET", f"/databases/{self.database_id}").get("properties", {}))
        missing = {k: {t: {}} for k, t in props.items() if k not in have}
        if missing:
            self.request("PATCH", f"/databases/{self.database_id}", {"properties": missing})
            log.info("Notion: added columns %s", ", ".join(missing))
        self._ensured = have | set(props)
        return list(missing)

    def check(self) -> dict:
        """One real read; raises NotionNotConnected with instructions if the integration lacks access."""
        return self.request("GET", f"/databases/{self.database_id}")

    # ---- page body
    def _children(self, block_id: str) -> list[dict]:
        out, cursor = [], None
        while True:
            q = f"/blocks/{block_id}/children?page_size=100" + (f"&start_cursor={cursor}" if cursor else "")
            res = self.request("GET", q)
            out += res.get("results", [])
            if not res.get("has_more"):
                return out
            cursor = res["next_cursor"]

    def read_page_text(self, page_id: str | None = None) -> str:
        return blocks_to_text(self._children(page_id or self.s["what_works_page_id"]))

    def replace_page_text(self, text: str, page_id: str | None = None) -> None:
        pid = page_id or self.s["what_works_page_id"]
        for b in self._children(pid):
            if b.get("type") in ("child_page", "child_database"):
                continue  # never delete sub-pages
            self.request("DELETE", f"/blocks/{b['id']}")
        blocks = text_to_blocks(text)
        for i in range(0, len(blocks), 100):
            self.request("PATCH", f"/blocks/{pid}/children", {"children": blocks[i:i + 100]})
