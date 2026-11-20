import socket
import urllib.error

import pytest

from yt_auto import heal


def test_is_transient_true():
    assert heal.is_transient(TimeoutError("x"))
    assert heal.is_transient(urllib.error.URLError("unreachable"))
    assert heal.is_transient(RuntimeError("503 Service Unavailable"))
    assert heal.is_transient(RuntimeError(
        "HTTPSConnectionPool(host='cdn-lfs.huggingface.co'): Max retries exceeded with url /x"))
    assert heal.is_transient(socket.timeout("slow"))
    try:
        try:
            raise ConnectionResetError("peer reset")
        except OSError as inner:
            raise RuntimeError("build blew up") from inner
    except RuntimeError as chained:
        assert heal.is_transient(chained)


def test_is_transient_false():
    assert not heal.is_transient(ValueError("bad value"))
    assert not heal.is_transient(RuntimeError("invalid_grant: Token has been expired"))
    assert not heal.is_transient(RuntimeError("403 Forbidden"))


def test_retry_succeeds_after_transient_failures():
    n = {"c": 0}
    sleeps = []

    def fn():
        n["c"] += 1
        if n["c"] < 3:
            raise TimeoutError("timed out")
        return "done"
    assert heal.retry(fn, tries=3, base=1, sleep=sleeps.append) == "done"
    assert n["c"] == 3 and len(sleeps) == 2 and sleeps[1] > sleeps[0] * 0.9


def test_retry_does_not_retry_permanent():
    n = {"c": 0}

    def fn():
        n["c"] += 1
        raise ValueError("nope")
    with pytest.raises(ValueError):
        heal.retry(fn, tries=3, sleep=lambda s: None)
    assert n["c"] == 1


def test_retry_gives_up_after_tries():
    n = {"c": 0}

    def fn():
        n["c"] += 1
        raise TimeoutError("timed out")
    with pytest.raises(TimeoutError):
        heal.retry(fn, tries=3, sleep=lambda s: None)
    assert n["c"] == 3


def test_preflight_all_ok(cfg, no_push):
    res = heal.preflight(cfg, {"a": lambda c: "fine", "b": lambda c: "ok"}, sleep=lambda s: None)
    assert res == {"a": (True, "fine"), "b": (True, "ok")}
    assert no_push == []


def test_preflight_failure_pushes_once(cfg, no_push):
    def bad(c):
        raise ValueError("login revoked")
    res = heal.preflight(cfg, {"a": lambda c: "fine", "b": bad, "c": bad}, sleep=lambda s: None)
    assert res["a"][0] is True and res["b"][0] is False and "login revoked" in res["b"][1]
    assert len(no_push) == 1
