import io
import stat

import yt_auto.notify as notify_mod


def test_topic_created_private_and_stable(tmp_path):
    p = tmp_path / "ntfy.json"
    s1 = notify_mod.settings(p)
    assert stat.S_IMODE(p.stat().st_mode) == 0o600
    assert s1["topic"].startswith("yt-auto-") and len(s1["topic"]) > 25
    assert notify_mod.settings(p) == s1


def test_send_headers(tmp_path, monkeypatch):
    monkeypatch.undo()  # undo the autouse stub so the real send() runs
    reqs = []

    def opener(req, timeout=None):
        reqs.append(req)
        return io.BytesIO(b"{}")
    p = tmp_path / "ntfy.json"
    assert notify_mod.send("New Short ready, approve?", "body", click="https://notion.so/x",
                           tags=["clapper"], path=p, opener=opener)
    r = reqs[0]
    assert r.full_url == "https://ntfy.sh/" + notify_mod.settings(p)["topic"]
    assert r.get_header("Title") == "New Short ready, approve?"
    assert r.get_header("Click") == "https://notion.so/x" and r.get_header("Tags") == "clapper"
    assert r.data == b"body"
    assert notify_mod.send("Café ✓", "x", path=p, opener=opener)
    assert reqs[1].get_header("Title").startswith("=?UTF-8?B?")


def test_send_never_raises(tmp_path, monkeypatch):
    monkeypatch.undo()

    def opener(req, timeout=None):
        raise OSError("offline")
    assert notify_mod.send("t", "m", path=tmp_path / "n.json", opener=opener) is False
