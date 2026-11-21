"""The rvc voice backend must fall back to clone whenever anything it needs is missing or broken."""
import subprocess

import numpy as np

from yt_auto import duo


def _cfg(root, backend="rvc"):
    chars = {n: {"rvc_model": f"assets/voices/rvc/{n}.pth"} for n in ("Hiro", "Baymax")}
    return {"_root": root, "duo": {"voice_backend": backend, "tempo": 1.0, "characters": chars}}


def _install(root, models=True, venv=True):
    if models:
        (root / "assets/voices/rvc").mkdir(parents=True)
        for n in ("Hiro", "Baymax"):
            (root / f"assets/voices/rvc/{n}.pth").write_bytes(b"x")
    if venv:
        (root / "tools/rvc/Applio/.venv/bin").mkdir(parents=True)
        (root / "tools/rvc/Applio/.venv/bin/python").write_text("")


def test_rvc_ready_needs_models_and_env(tmp_path):
    assert not duo._rvc_ready(_cfg(tmp_path))
    _install(tmp_path, venv=False)
    assert not duo._rvc_ready(_cfg(tmp_path))          # models but no Applio env
    _install(tmp_path, models=False)
    assert duo._rvc_ready(_cfg(tmp_path))


def test_failed_conversion_falls_back_to_clone(tmp_path, monkeypatch):
    _install(tmp_path)
    used = []

    def boom(*a):
        raise subprocess.CalledProcessError(1, "rvc_convert.py")

    def clone(sc, cfg, job):
        used.append("clone")
        tone = 0.5 * np.sin(np.arange(duo.SR // 2) * 0.05).astype(np.float32)
        return [(tone, duo.SR) for _ in sc["lines"]]

    monkeypatch.setattr(duo, "_rvc_lines", boom)
    monkeypatch.setattr(duo, "_clone_lines", clone)
    sc = {"lines": [{"speaker": "Hiro", "text": "hi"}, {"speaker": "Baymax", "text": "hello"}]}
    timing = duo.voice_lines(sc, _cfg(tmp_path), tmp_path)
    assert used == ["clone"] and len(timing) == 2
