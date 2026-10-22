"""History in SQLite (hadith_shorts/history.sqlite, kept in git so the daily job remembers between runs):
which hadith were checked, which videos were made and uploaded, and a log."""
import sqlite3
import time

from hadith_shorts import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS hadith (
  ref TEXT PRIMARY KEY,            -- e.g. bukhari:1
  citation TEXT, url TEXT, theme TEXT,
  verified INTEGER,                -- 1 = matches its sunnah.com page, 0 = failed (never used)
  detail TEXT, checked_at TEXT);
CREATE TABLE IF NOT EXISTS videos (
  id INTEGER PRIMARY KEY,
  day TEXT,                        -- the publishing day (local date)
  ref TEXT, title TEXT, path TEXT,
  status TEXT,                     -- rendered | uploading | uploaded | failed
  youtube_id TEXT, privacy TEXT, publish_at TEXT, error TEXT,
  created TEXT, updated TEXT);
CREATE UNIQUE INDEX IF NOT EXISTS one_video_per_day ON videos(day) WHERE status IN ('uploading', 'uploaded');
CREATE TABLE IF NOT EXISTS log (id INTEGER PRIMARY KEY, at TEXT, level TEXT, ref TEXT, message TEXT);
"""


def now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def connect(path=None):
    db = sqlite3.connect(path or settings.DB_PATH)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db


def log(db, level, message, ref=None):
    db.execute("INSERT INTO log(at, level, ref, message) VALUES (?, ?, ?, ?)", (now(), level, ref, message[:1000]))
    db.commit()
    print(f"[{level}] {ref + ': ' if ref else ''}{message}")


def checked(db, ref):
    return db.execute("SELECT * FROM hadith WHERE ref = ?", (ref,)).fetchone()


def save_check(db, ref, citation, url, theme, ok, detail):
    db.execute("INSERT OR REPLACE INTO hadith VALUES (?, ?, ?, ?, ?, ?, ?)", (ref, citation, url, theme, int(ok), detail, now()))
    db.commit()


def used(db, ref):
    """Already published or being published (never repeat a hadith)."""
    return db.execute("SELECT 1 FROM videos WHERE ref = ? AND status IN ('uploading', 'uploaded')", (ref,)).fetchone()


def for_day(db, day):
    return db.execute("SELECT * FROM videos WHERE day = ? ORDER BY id DESC", (day,)).fetchall()


def add_video(db, day, ref, title, path, status, privacy=None, publish_at=None):
    cur = db.execute("INSERT INTO videos(day, ref, title, path, status, privacy, publish_at, created, updated) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (day, ref, title, str(path), status, privacy, publish_at, now(), now()))
    db.commit()
    return cur.lastrowid


def update_video(db, vid, **fields):
    sets = ", ".join(f"{k} = ?" for k in fields)
    db.execute(f"UPDATE videos SET {sets}, updated = ? WHERE id = ?", (*fields.values(), now(), vid))
    db.commit()
