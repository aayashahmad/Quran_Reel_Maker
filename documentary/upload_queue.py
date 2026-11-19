"""Upload the next documentary episodes to YouTube (public), in story order, and record them in published.json.

YouTube's API allows about six uploads a day and the daily hadith Shorts and Qissa need four of them, so this posts
at most N a day (default 2), just after the quota resets (00:00 Pacific = 13:30 IST). Run by queue.sh from launchd.

  python -m documentary.upload_queue [N]
"""
import datetime
import json
import subprocess
import sys
import time
from pathlib import Path

from documentary import build

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "documentary"
PUB = ROOT / "documentary" / "published.json"
TAGS = {"en": ["Seerah", "Prophet Muhammad", "Seerah documentary", "Islamic history", "Life of the Prophet",
               "Sahih hadith", "Quran", "Islam", "Islamic documentary", "Makkah", "Madinah"],
        "ur": ["سیرت النبی", "سیرت", "نبی کریم", "اسلامی تاریخ", "Seerah in Urdu", "Seerah Urdu", "Islamic history Urdu",
               "Prophet Muhammad", "صحیح حدیث", "Islam", "Seerah documentary"]}


def pending():
    pub = json.loads(PUB.read_text())
    for eid in build.EPISODES:
        for lang in ("en", "ur"):
            if not pub.get(eid, {}).get(lang):
                yield eid, lang


def main(n=2):
    from googleapiclient.errors import HttpError
    from hadith_shorts import publish
    done = 0
    for eid, lang in pending():
        if done >= n:
            break
        mp4, txt = OUT / f"{eid}-{lang}.mp4", OUT / f"{eid}-{lang}.txt"
        if not mp4.exists() or not txt.exists() or time.time() - mp4.stat().st_mtime < 600:
            print(f"{eid}-{lang}: not rendered yet (or still rendering); stopping so the order is kept")
            break
        meta = json.loads(txt.read_text())
        thumb = OUT / f"{eid}-{lang}-thumb.jpg"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "5", "-i", str(mp4), "-frames:v", "1",
                        "-vf", "scale=1280:720", "-q:v", "3", str(thumb)], check=True)
        try:
            vid = publish.upload(mp4, meta["title"], meta["description"], TAGS[lang], thumbnail=thumb)
        except HttpError as e:
            print(f"{eid}-{lang}: upload refused ({e}); trying again tomorrow")
            break
        pub = json.loads(PUB.read_text())
        pub.setdefault(eid, {})[lang] = vid
        pub.setdefault("_dates", {})[vid] = datetime.date.today().isoformat()
        PUB.write_text(json.dumps(pub, ensure_ascii=False, indent=1) + "\n")
        print(f"uploaded {eid}-{lang}: https://youtu.be/{vid}", flush=True)
        done += 1
    left = len(list(pending()))
    print(f"{done} uploaded, {left} left")
    return done


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2)
