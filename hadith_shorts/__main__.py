"""Daily Sahih Hadith Shorts.

  python -m hadith_shorts make --ref bukhari:1      make (and check) one video, no upload
  python -m hadith_shorts make --ref bukhari:1 --upload   ... and upload it with the configured privacy
  python -m hadith_shorts daily                     the daily job: pick, verify, make, check, upload (if enabled)
  python -m hadith_shorts status                    recent videos and log
  python -m hadith_shorts resolve <day> <youtube id | none>   settle an upload whose result is unknown
"""
import argparse
import json
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from hadith_shorts import publish, render, settings, source, store, themes, validate


def today():
    return datetime.now(ZoneInfo(settings.TIMEZONE)).date().isoformat()


def check_source(db, h):
    """Verify against sunnah.com once per hadith (remembered); every failure is recorded."""
    row = store.checked(db, h.ref)
    if row and row["verified"]:
        return True
    problems = validate.content(h)
    ok, detail = (False, "; ".join(problems)) if problems else source.verify(h)
    store.save_check(db, h.ref, h.citation, h.url, themes.detect(h.english), ok, detail)
    store.log(db, "info" if ok else "warning", f"source check {'passed' if ok else 'FAILED'}: {detail}", h.ref)
    return ok


def make(db, h, day, upload=False):
    out = settings.OUTPUT_DIRECTORY / day.replace("#", "_")
    out.mkdir(parents=True, exist_ok=True)
    problems = validate.arabic_shaping()
    if problems:
        raise RuntimeError("; ".join(problems))
    res = render.build(h, out, log=lambda m: print("  " + m))
    problems = validate.media(res["video"])
    if problems:
        raise RuntimeError("video check failed: " + "; ".join(problems))
    title, desc, tags = publish.metadata(h, res["title"])
    meta = {"ref": h.ref, "citation": h.citation, "url": h.url, "book": h.book, "narrator": h.narrator,
            "translator": h.translator, "source": h.source, "arabic_shown": h.arabic, "arabic_is_excerpt": h.arabic_is_excerpt,
            "english": h.english, "theme": res["theme"], "seconds": round(res["seconds"], 2), "youtube_title": title,
            "youtube_description": desc, "tags": tags, "plan": res["plan"]}
    res["video"].with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    vid = store.add_video(db, day, h.ref, title, res["video"], "rendered")
    store.log(db, "info", f"rendered {res['video'].name} ({res['seconds']:.1f}s), all checks passed", h.ref)
    if upload:
        do_upload(db, vid, day, res["video"], res["thumbnail"], title, desc, tags, h.ref)
    return res


def do_upload(db, vid, day, path, thumb, title, desc, tags, ref):
    if store.for_day(db, day) and any(r["status"] in ("uploading", "uploaded") for r in store.for_day(db, day)):
        store.log(db, "warning", f"{day} already has an upload: not uploading again", ref)
        return
    when = publish.publish_at(day)
    store.update_video(db, vid, status="uploading", privacy=settings.YOUTUBE_PRIVACY_STATUS, publish_at=when)
    try:
        yid = publish.upload(path, title, desc, tags, thumb, when)
    except Exception as e:
        # the result is unknown only if the upload may have reached YouTube; an error before that is safe to retry
        msg = f"{e.__class__.__name__}: {e}"
        store.update_video(db, vid, status="failed", error=msg[:500])
        store.log(db, "error", f"upload failed (will retry next run): {msg}", ref)
        raise
    store.update_video(db, vid, status="uploaded", youtube_id=yid)
    store.log(db, "info", f"uploaded https://youtube.com/shorts/{yid} ({settings.YOUTUBE_PRIVACY_STATUS}"
                          f"{', publishes ' + when if when else ''})", ref)


def slot_key(date, slot):
    """The day's n-th video: '2026-10-22' for the first (as before), '2026-10-22#2' for the second..."""
    return date if slot == 1 else f"{date}#{slot}"


def daily(db):
    """Make (and upload) the next of today's VIDEOS_PER_DAY videos; run it once per slot (e.g. 12:00 and 20:00)."""
    date = today()
    for slot in range(1, settings.VIDEOS_PER_DAY + 1):
        day = slot_key(date, slot)
        if not any(r["status"] == "uploaded" for r in store.for_day(db, day)):
            break
    else:
        print(f"{date}: all {settings.VIDEOS_PER_DAY} videos are uploaded, nothing to do.")
        return 0
    return daily_slot(db, day)


def daily_slot(db, day):
    rows = store.for_day(db, day)
    if any(r["status"] == "uploading" for r in rows):
        store.log(db, "error", f"{day}: an earlier upload's result is unknown. Check YouTube Studio, then run "
                               f"'python -m hadith_shorts resolve {day} <video id or none>'.")
        return 1
    # retry only the upload when today's video was already made
    done = next((r for r in rows if r["status"] in ("rendered", "failed") and r["path"]), None)
    if done and settings.ENABLE_PUBLICATION:
        from pathlib import Path
        path = Path(done["path"])
        if path.exists() and not validate.media(path):
            h = source.get(done["ref"])
            title, desc, tags = publish.metadata(h, themes.theme(themes.detect(h.english))[0])
            thumb = path.with_name(path.stem + "_thumbnail.jpg")
            do_upload(db, done["id"], day, path, thumb if thumb.exists() else None, title, desc, tags, h.ref)
            return 0
    if done and not settings.ENABLE_PUBLICATION:
        print(f"{day}: already made ({done['ref']}); publication is off.")
        return 0
    for ref in source.candidates(settings.HADITH_COLLECTIONS):
        if store.used(db, ref):
            continue
        row = store.checked(db, ref)
        if row and not row["verified"]:
            continue                                   # failed before: recorded, never used
        h = source.get(ref)
        if not check_source(db, h):
            continue
        make(db, h, day, upload=settings.ENABLE_PUBLICATION)
        return 0
    store.log(db, "error", "no eligible hadith left")
    return 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m hadith_shorts")
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("--ref", required=True, help="e.g. bukhari:1 or muslim:5218")
    m.add_argument("--upload", action="store_true")
    sub.add_parser("daily")
    sub.add_parser("status")
    r = sub.add_parser("resolve")
    r.add_argument("day"), r.add_argument("youtube_id")
    a = ap.parse_args(argv)
    db = store.connect()
    if a.cmd == "make":
        h = source.get(a.ref)
        if not check_source(db, h):
            return 1
        res = make(db, h, today(), upload=a.upload)
        print(f"Video: {res['video']}\nThumbnail: {res['thumbnail']}")
        return 0
    if a.cmd == "daily":
        return daily(db)
    if a.cmd == "status":
        for r in db.execute("SELECT day, ref, status, youtube_id, privacy, error FROM videos ORDER BY id DESC LIMIT 15"):
            print(dict(r))
        for r in db.execute("SELECT at, level, ref, message FROM log ORDER BY id DESC LIMIT 15"):
            print(f"{r['at']} [{r['level']}] {r['ref'] or ''} {r['message']}")
        return 0
    if a.cmd == "resolve":
        rows = [r for r in store.for_day(db, a.day) if r["status"] == "uploading"]
        for r in rows:
            if a.youtube_id.lower() == "none":
                store.update_video(db, r["id"], status="failed", error="resolved by hand: not on YouTube")
            else:
                store.update_video(db, r["id"], status="uploaded", youtube_id=a.youtube_id)
        print(f"resolved {len(rows)} upload(s)")
        return 0


if __name__ == "__main__":
    sys.exit(main())
