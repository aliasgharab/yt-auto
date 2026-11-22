import json
from pathlib import Path

from yt_auto import film, pipeline


def test_minutes_rounds_up():
    assert film.minutes_for(163) == 3
    assert film.minutes_for(119.5) == 2
    assert film.minutes_for(120) == 3      # exactly 2:00 is not 'under 2 minutes'
    assert film.minutes_for(40) == 1


def test_title_pattern():
    assert film.make_title("The Enigma Machine", 3) == "The Enigma Machine Explained in Under 3 Minutes"
    assert film.make_title("  Y2K. ", 1) == "Y2K Explained in Under 1 Minute"


def test_description_has_summary_sources_disclosure_hashtags():
    d = film.make_description(
        "How Britain broke the 'unbreakable' Enigma.",
        [{"title": "Enigma machine (Wikipedia)", "url": "https://en.wikipedia.org/wiki/Enigma_machine"}],
        ["Enigma", "#Alan Turing", "TechHistory", "Enigma", "!!", "Cryptography", "WW2", "extra"])
    parts = d.split("\n\n")
    assert parts[0] == "How Britain broke the 'unbreakable' Enigma."
    assert parts[1] == "Sources:\n• Enigma machine (Wikipedia): https://en.wikipedia.org/wiki/Enigma_machine"
    assert parts[2] == film.DISCLOSURE
    assert parts[3] == "#Enigma #AlanTuring #TechHistory #Cryptography #WW2"   # deduped, cleaned, max 5


class _Resp:
    def __init__(self, status):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _Opener:
    def __init__(self, good):
        self.good, self.seen = good, []

    def open(self, req, timeout=None):
        self.seen.append((req.get_method(), req.full_url, req.get_header("User-agent")))
        if req.full_url in self.good:
            return _Resp(200)
        raise OSError("404")


def test_check_sources_drops_broken_and_invalid():
    op = _Opener({"https://ok.example/a"})
    kept = film.check_sources([{"title": " A ", "url": "https://ok.example/a"},
                               {"title": "B", "url": "https://bad.example/b"},
                               {"title": "C", "url": "ftp://x"}], opener=op)
    assert kept == [{"title": "A", "url": "https://ok.example/a"}]
    assert ("GET", "https://bad.example/b") in [(m, u) for m, u, _ in op.seen]   # HEAD failed -> GET tried
    assert all("@" not in (ua or "") for _, _, ua in op.seen)                    # no personal details sent


def test_srt_from_timings(tmp_path: Path):
    tim = {"lines": [{"text": "In 1939.", "start": 0.0, "end": 1.5}, {"text": "They were wrong.", "start": 2.0, "end": 3.25}]}
    film.write_srt(tim, tmp_path / "c.srt")
    srt = (tmp_path / "c.srt").read_text()
    assert "1\n00:00:00,667 --> 00:00:02,167\nIn 1939." in srt
    assert "2\n00:00:02,667 --> 00:00:03,917\nThey were wrong." in srt


def test_composition_id():
    assert film.composition_id("enigma") == "FilmEnigma"
    assert film.composition_id("morris-worm") == "FilmMorrisWorm"


def test_builder_registry_and_urls():
    assert pipeline.builder_for("film") is film.build_film
    assert pipeline.builder_for("short").__name__ == "build_short"
    assert pipeline.youtube_url("abc", "film") == "https://youtu.be/abc"
    assert pipeline.youtube_url("abc", "short") == "https://youtube.com/shorts/abc"
    assert pipeline.per_night({"publish": {"videos_per_night": 1, "shorts_per_night": 5}}) == 1


def test_qa_film_duration_and_resolution(tmp_path: Path, monkeypatch):
    from yt_auto import agents
    (tmp_path / "job.json").write_text(json.dumps({"format": "film"}))
    (tmp_path / "script.json").write_text(json.dumps({"lines": [{"text": "hello there"}]}))
    (tmp_path / "video.mp4").write_bytes(b"0" * 20000)
    (tmp_path / "captions.srt").write_text("1\n00:00:00,667 --> 00:00:02,000\nhello there\n")
    monkeypatch.setattr(agents, "ffprobe", lambda v: {"format": {"duration": "163.0"}, "streams": [
        {"codec_type": "video", "width": 1920, "height": 1080}, {"codec_type": "audio"}]})
    monkeypatch.setattr(agents, "volumedetect", lambda v: {"mean_volume": -18.0, "max_volume": -1.2})
    checks, facts = agents.deterministic_checks(tmp_path)
    fails = [m for s, m in checks if s == "fail"]
    assert not fails, fails
