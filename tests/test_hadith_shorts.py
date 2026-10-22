"""Tests for the Daily Sahih Hadith Shorts. Run:  .venv/bin/python -m pytest tests -q
(network tests are skipped unless RUN_NETWORK_TESTS=1)."""
import os
import subprocess
from pathlib import Path

import pytest

from hadith_shorts import publish, settings, source, store, themes, tts, validate

NET = pytest.mark.skipif(os.getenv("RUN_NETWORK_TESTS") != "1", reason="needs the internet")


def test_reference_parsing_and_errors():
    assert source.get("bukhari:1").citation == "Sahih al-Bukhari 1"
    for bad in ("bukhari", "tirmidhi:1", "bukhari:x", "bukhari:999999"):
        with pytest.raises(source.SourceError):
            source.get(bad)


def test_arabic_excerpt_is_original_text():
    h = source.get("bukhari:1")
    assert h.arabic_is_excerpt and source.plain(h.arabic).startswith(source.plain("إِنَّمَا الْأَعْمَالُ بِالنِّيَّاتِ"))
    assert validate.content(h) == []


def test_malformed_source_is_caught():
    h = source.get("bukhari:1")
    h.arabic = "نص مختلق"                     # not in the narration
    h.url = "https://example.com/x"
    problems = validate.content(h)
    assert any("not part of the source" in p for p in problems) and any("sunnah.com" in p for p in problems)


def test_translation_attribution_in_metadata():
    h = source.get("bukhari:1")
    title, desc, tags = publish.metadata(h, "On Intentions")
    assert "Sahih al-Bukhari 1" in title and len(title) <= 100
    assert h.url in desc and "Muhsin Khan" in desc and h.english in desc


def test_theme_and_plan():
    h = source.get("bukhari:1")
    tid = themes.detect(h.english)
    assert tid == "intention"
    plan = themes.scene_plan(h, tid, [{"text": "x", "seconds": 2.0}], 3, 4)
    assert plan["scenes"][0]["scene"] == "opening" and plan["scenes"][-1]["scene"] == "closing"


def test_caption_segments_cover_text():
    h = source.get("bukhari:1")
    parts = tts.segments(h.english)
    assert " ".join(parts).split() == h.english.split()
    assert all(len(p.split()) <= 24 for p in parts)    # whole sentences without commas may run a little over 16


def test_tts_failure_is_reported(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "TTS_ENGINE", "edge")
    monkeypatch.setattr(tts, "_edge", lambda text, out: (_ for _ in ()).throw(tts.TTSError("service down")))
    with pytest.raises(tts.TTSError):
        tts.speak("hello", tmp_path / "x.mp3")


def test_arabic_shaping_available():
    assert validate.arabic_shaping() == []


def test_duplicate_prevention(tmp_path):
    db = store.connect(tmp_path / "h.sqlite")
    vid = store.add_video(db, "2026-10-22", "bukhari:1", "t", "p.mp4", "uploading")
    assert store.used(db, "bukhari:1")
    with pytest.raises(Exception):               # a second upload on the same day is refused by the database
        store.add_video(db, "2026-10-22", "bukhari:2", "t", "p.mp4", "uploaded")
    store.update_video(db, vid, status="uploaded", youtube_id="abc")
    assert store.used(db, "bukhari:1")


def test_crash_during_upload_blocks_reupload(tmp_path, monkeypatch):
    from hadith_shorts import __main__ as job
    monkeypatch.setattr(settings, "DB_PATH", tmp_path / "h.sqlite")
    db = store.connect()
    store.add_video(db, job.today(), "bukhari:1", "t", "p.mp4", "uploading")     # crashed mid-upload
    assert job.daily(db) == 1                     # refuses, asks for 'resolve'
    job.main(["resolve", job.today(), "none"])
    assert all(r["status"] != "uploading" for r in store.for_day(store.connect(), job.today()))


def test_upload_failure_is_recorded(tmp_path, monkeypatch):
    from hadith_shorts import __main__ as job
    db = store.connect(tmp_path / "h.sqlite")
    vid = store.add_video(db, "2026-10-22", "bukhari:1", "t", "p.mp4", "rendered")

    def boom(*a, **k):
        raise RuntimeError("invalid_grant: Token has been expired or revoked")
    monkeypatch.setattr(publish, "upload", boom)
    with pytest.raises(RuntimeError):
        job.do_upload(db, vid, "2026-10-22", "p.mp4", None, "t", "d", [], "bukhari:1")
    row = db.execute("SELECT status, error FROM videos WHERE id = ?", (vid,)).fetchone()
    assert row["status"] == "failed" and "invalid_grant" in row["error"]


def test_media_validation(tmp_path):
    bad = tmp_path / "bad.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "color=black:s=640x360:d=3",
                    "-c:v", "libx264", str(bad)], check=True)
    problems = validate.media(bad)
    assert any("size" in p for p in problems) and any("audio" in p for p in problems)


def test_rendered_day1_video_if_present():
    v = sorted(Path(settings.OUTPUT_DIRECTORY).glob("*/bukhari_1.mp4"))
    if not v:
        pytest.skip("make it first: python -m hadith_shorts make --ref bukhari:1")
    assert validate.media(v[-1]) == []


@NET
def test_sunnah_verification():
    ok, detail = source.verify(source.get("bukhari:1"))
    assert ok, detail


def test_two_videos_a_day(tmp_path, monkeypatch):
    from hadith_shorts import __main__ as job
    monkeypatch.setattr(settings, "DB_PATH", tmp_path / "h.sqlite")
    monkeypatch.setattr(settings, "VIDEOS_PER_DAY", 2)
    db = store.connect()
    date = job.today()
    store.add_video(db, date, "bukhari:1", "t", "p.mp4", "uploaded")
    picked = []
    monkeypatch.setattr(job, "daily_slot", lambda db, day: picked.append(day) or 0)
    job.daily(db)
    assert picked == [f"{date}#2"]                 # the second slot comes next
    store.add_video(db, f"{date}#2", "bukhari:13", "t", "p.mp4", "uploaded")
    picked.clear()
    assert job.daily(db) == 0 and picked == []     # both done: nothing more today
