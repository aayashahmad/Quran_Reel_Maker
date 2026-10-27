"""The daily Qissa job: each run makes the next video in the queue (stories in order of their number, part by part,
English then Hinglish), uploads it private and schedules it to go public QISSA_DELAY_HOURS (5) hours later, so
the owner can watch it and delete it first if anything is wrong. Two runs a day = two videos a day.
Progress is kept in qissa/published.json (committed by the workflow)."""
import json
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from qissa import build

STATE = build.STORIES.parent / "published.json"
PER_DAY = int(os.getenv("QISSA_PER_DAY", "2"))
DELAY_HOURS = float(os.getenv("QISSA_DELAY_HOURS", "5"))
PUBLISH = os.getenv("QISSA_PUBLISH", "false").lower() in ("1", "true", "yes")
TZ = ZoneInfo(os.getenv("TIMEZONE", "Asia/Kolkata"))
HASHTAGS = {"en": "#QuranStories #ProphetStories #Islam #IslamicStories #Quran #Shorts",
            "hi": "#QuranKiKahani #IslamicStory #Hinglish #Islam #Quran #Shorts"}


def load_state():
    return json.loads(STATE.read_text()) if STATE.exists() else []


def save_state(state):
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1))


LANG_OF_SLOT = [x.strip() for x in os.getenv("QISSA_LANGS", "en,hi").split(",") if x.strip()]


def stories():
    return sorted((build.load(f.stem) for f in build.STORIES.glob("*.json")), key=lambda s: s.get("number", 999))


def queue(lang="en"):
    """Every (story, part, lang) of one language in publishing order: stories in order, each part by part.
    Each language starts at a different story (Hinglish from the middle), so the day's two videos differ."""
    ss = stories()
    k = LANG_OF_SLOT.index(lang) if lang in LANG_OF_SLOT else 0
    shift = (len(ss) * k) // max(1, len(LANG_OF_SLOT))
    for s in ss[shift:] + ss[:shift]:
        for part, _ in build.parts_of(s):
            yield s, part, lang


def metadata(story, part, parts, lang, credits):
    title = story["title"][lang] + (f" (Part {part}/{parts})" if parts > 1 else "")
    yt_title = f"{title} | Qissa #{story.get('number', 0):03d} #Shorts"[:100]
    lines = [story["title"][lang] + (f", part {part} of {parts}" if parts > 1 else ""), "",
             "Sources (every ayah and hadith on screen is taken from the verified text):"]
    lines += [f"• {src}" for src in story.get("sources", [])]
    lines += ["", "Narration: AI voice (Microsoft Edge neural text-to-speech)."]
    if credits:
        lines.append("Footage: " + ", ".join(f"{c['by']} on Pexels" for c in credits if c.get("by")) + ".")
    lines += ["This is a story from the Quran and sahih hadith, not a fatwa. For rulings, ask a qualified scholar.", "",
              "Make your own Quran reels, free: https://quranreelmaker.xyz", "", HASHTAGS[lang]]
    tags = ["Quran stories", "Prophet stories", "Islamic stories", "Qissa", "Quran", "Islam",
            "Hinglish Islamic story" if lang == "hi" else "Stories of the prophets"]
    return yt_title, "\n".join(lines)[:4900], tags


def run(out_dir, log=print):
    state = load_state()
    today = datetime.now(TZ).date().isoformat()
    if any(e["status"] == "uploading" for e in state):
        log("An earlier upload's result is unknown: check YouTube Studio, then fix qissa/published.json.")
        return 1
    if sum(1 for e in state if e["day"] == today and e["status"] == "uploaded") >= PER_DAY:
        log(f"{today}: {PER_DAY} Qissa videos already uploaded.")
        return 0
    from qissa.due import is_due
    if os.getenv("FORCE") != "1" and not is_due():
        log("No Qissa video is due yet.")
        return 0
    done = {(e["story"], e["part"], e["lang"]) for e in state if e["status"] == "uploaded"}
    todays = [e for e in state if e["day"] == today and e["status"] == "uploaded"]
    lang = LANG_OF_SLOT[len(todays) % len(LANG_OF_SLOT)]
    busy = {e["story"] for e in todays}                  # never the same story twice in one day
    started = {e["story"] for e in state if e["status"] == "uploaded" and e["lang"] == lang}
    items = [(s, k, l) for s, k, l in queue(lang) if (s["id"], k, l) not in done]
    # finish a story that is half told (part by part) before starting a new one
    item = next((it for it in items if it[0]["id"] in started and it[0]["id"] not in busy), None) \
        or next((it for it in items if it[0]["id"] not in busy), None)
    if not item:
        log(f"The Qissa queue ({lang}) is empty: write new stories (qissa-writer agent).")
        return 0
    story, part, lang = item
    log(f"Making {story['id']} part {part} ({lang})")
    res = build.make(story["id"], lang, out_dir, log=lambda m: log("  " + m), part=part,
                     use_footage=bool(os.getenv("PEXELS_API_KEY")))
    if not PUBLISH:
        log(f"Made {res['video']} ({res['seconds']:.0f}s); publishing is off (QISSA_PUBLISH).")
        return 0
    from hadith_shorts.publish import upload
    title, desc, tags = metadata(story, part, res["parts"], lang, res["credits"])
    when = (datetime.now(timezone.utc) + timedelta(hours=DELAY_HOURS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = {"story": story["id"], "part": part, "lang": lang, "day": today, "status": "uploading",
             "title": title, "publish_at": when}
    state.append(entry)
    save_state(state)
    try:
        entry["youtube_id"] = upload(res["video"], title, desc, tags, None, when)
        entry["status"] = "uploaded"
    except Exception as e:
        entry["status"] = "failed"
        entry["error"] = f"{e.__class__.__name__}: {e}"[:400]
        save_state(state)
        raise
    save_state(state)
    log(f"Uploaded https://youtube.com/shorts/{entry['youtube_id']} (private, public at {when} UTC)")
    return 0
