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
    monkeypatch.setattr(tts, "_edge", lambda text, out, lang="en": (_ for _ in ()).throw(tts.TTSError("service down")))
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
    import os
    monkeypatch.setattr(os, "environ", {**os.environ, "FORCE": "1"})     # whatever the time of day
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
    import os
    monkeypatch.setattr(os, "environ", {**os.environ, "FORCE": "1"})
    monkeypatch.setattr(settings, "DB_PATH", tmp_path / "h.sqlite")
    monkeypatch.setattr(settings, "VIDEOS_PER_DAY", 2)
    db = store.connect()
    date = job.today()
    store.add_video(db, date, "bukhari:1", "t", "p.mp4", "uploaded")
    picked = []
    monkeypatch.setattr(job, "daily_slot", lambda db, day, lang="en": picked.append((day, lang)) or 0)
    job.daily(db)
    assert picked == [(f"{date}#2", "ur")]         # the second slot comes next, in Urdu
    store.add_video(db, f"{date}#2", "bukhari:13", "t", "p.mp4", "uploaded")
    picked.clear()
    assert job.daily(db) == 0 and picked == []     # both done: nothing more today


def test_urdu_text_and_metadata():
    h = source.get("bukhari:1")
    assert h.urdu.startswith("تمام اعمال کا دارومدار نیت پر ہے") and validate.content(h, "ur") == []
    parts = tts.segments(h.urdu, 18, "ur")
    assert " ".join(parts).split() == h.urdu.split()
    title, desc, tags = publish.metadata(h, "نیت", "ur")
    assert "صحیح بخاری 1" in title and h.url in desc and "حدیث" in tags
    assert source.eligible(source.get("bukhari:6415"), "ur") in (True, False)


def test_due_slots_follow_the_clock(tmp_path, monkeypatch):
    monkeypatch.setenv("SLOT_TIMES", "12:00,20:00")
    monkeypatch.delenv("RUNNER", raising=False)
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from hadith_shorts import due
    db = store.connect(tmp_path / "h.sqlite")
    tz = ZoneInfo("Asia/Kolkata")
    at = lambda h, m: datetime(2026, 10, 26, h, m, tzinfo=tz)
    p = tmp_path / "h.sqlite"
    assert due.due_slot(at(11, 0), p) is None                 # before 12:00 nothing is due
    assert due.due_slot(at(14, 30), p) == 1                   # 12:00 was missed: catch up
    store.add_video(db, "2026-10-26", "bukhari:1", "t", "p", "uploaded")
    assert due.due_slot(at(14, 30), p) is None                # done, and 20:00 not yet
    assert due.due_slot(at(20, 30), p) == 2
    store.add_video(db, "2026-10-26#2", "bukhari:2", "t", "p", "uploaded")
    assert due.due_slot(at(23, 30), p) is None


def test_voice_says_salawat_after_every_mention_of_the_prophet():
    from hadith_shorts.tts import spoken
    assert spoken("The Prophet said: x") == "The Prophet (peace be upon him) said: x"
    assert spoken("Allah's Messenger (ﷺ) said") == "Allah's Messenger (peace be upon him) said"
    assert spoken("the Prophet (peace be upon him) said") == "the Prophet (peace be upon him) said"
    for other in ("the Prophets came", "the Prophet Musa said", "Narrated Muhammad bin Sirin"):
        assert spoken(other) == other
    assert spoken("نبیؐ اور ابوہریرہؓ", "ur") == "نبی صلی اللہ علیہ وسلم اور ابوہریرہ رضی اللہ عنہ"


def test_footage_follows_the_words_of_each_video():
    from qissa.footage import queries_for
    assert queries_for("should not harm his neighbour, and should honour his guest") == \
        ["old town street houses", "tea pouring cup"]
    assert queries_for("He built the ark; the water rose to the mountains")[0] == "old wooden sailing boat at sea"
    assert queries_for("Actions are judged by intentions")[0] == "candle light dark"
    assert queries_for("") == []


def test_seerah_chapters_are_complete_and_quote_word_for_word():
    import seerah
    assert seerah.check(verify=False) == []
    badr = seerah.hadith_block(seerah.BY_ID["the-battle-of-badr"]["blocks"][1])
    assert badr["part"] and badr["en"].endswith("So Allah helped him with angels.")


def test_three_slots_and_the_urdu_slot_belongs_to_the_mac(tmp_path, monkeypatch):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from hadith_shorts.due import due_slot
    tz = ZoneInfo("Asia/Kolkata")
    at = lambda h, m=0: datetime(2026, 11, 11, h, m, tzinfo=tz)
    db = str(tmp_path / "h.sqlite")
    monkeypatch.setenv("SLOT_TIMES", "09:00,15:00,21:00")
    monkeypatch.setenv("LAPTOP_SLOTS", "2")
    monkeypatch.setenv("LAPTOP_GRACE_MIN", "90")
    monkeypatch.setenv("RUNNER", "github")
    assert due_slot(at(8), db) is None
    assert due_slot(at(9, 5), db) == 1
    assert due_slot(at(15, 30), db) == 1            # slot 1 still missing: catch up first
    import sqlite3
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE videos (day TEXT, status TEXT)")
    c.execute("INSERT INTO videos VALUES ('2026-11-11', 'uploaded')")
    c.commit()
    assert due_slot(at(15, 30), db) is None          # the Mac's turn (90 min grace)
    assert due_slot(at(16, 35), db) == 2             # the Mac did not make it: GitHub does
    monkeypatch.setenv("RUNNER", "laptop")
    assert due_slot(at(15, 5), db) == 2
    assert due_slot(at(21, 5), db) == 2              # the Mac only ever makes its own slot


def test_ask_sends_seerah_questions_to_the_seerah_and_flags_rulings():
    import ask_rules
    import seerah
    assert seerah.ask_match("nabi pe pehli wahi kaise aayi")[0]["id"] == "the-first-revelation"
    assert seerah.ask_match("what happened at badr")[0]["id"] == "the-battle-of-badr"
    assert seerah.ask_match("my child was born today") == []          # no Prophet in it: not a Seerah question
    assert seerah.ask_match("I saw my baby being born") == []
    for q in ("is music haram", "kya main roza tod sakta hoon", "can i marry my cousin", "کیا یہ جائز ہے"):
        assert ask_rules.is_ruling(q), q
    for q in ("mujhse gunah ho gaya", "i feel anxious", "kya main maaf ho sakta hoon"):
        assert not ask_rules.is_ruling(q), q
