"""Local website: pick a surah and ayah range, generate a reel or a status/story image, download it.
Run with:  ./run.sh web   then open http://localhost:5050"""
import json
import re
import threading
import uuid

from flask import Flask, abort, jsonify, render_template, request, send_from_directory

from config import WEB_OUT, READ_URDU
from quran_data import load_quran, surah_ranges
from content import reel_info
from main import build_reel, TooLong
import reflect
import video

app = Flask(__name__)
QURAN = load_quran()
RANGES = surah_ranges(QURAN)
SURAHS = [{"n": s, "en": QURAN[a]["surah_en"], "ar": QURAN[a]["surah_ar"], "count": b - a}
          for s, (a, b) in sorted(RANGES.items())]
JOBS = {}
RENDER_LOCK = threading.Lock()      # one render at a time
JOB_ID = re.compile(r"^[0-9a-f]{12}$")
STORY_MAX_AYAT = 3
WEB_MAX_SECONDS = 10 * 60           # longer selections get a list of reel-sized parts instead


def pick(d, limit=None):
    """Validate surah/from/to from a request. Returns (surah, first, last) or an error string."""
    try:
        surah, first, last = int(d["surah"]), int(d["from"]), int(d["to"])
    except (KeyError, TypeError, ValueError):
        return "Choose a surah and ayah numbers."
    if surah not in RANGES:
        return "Unknown surah."
    count = RANGES[surah][1] - RANGES[surah][0]
    if not 1 <= first <= last <= count:
        return f"Ayah numbers must be between 1 and {count}, and From must not be after To."
    if limit and last - first + 1 > limit:
        return f"A story fits up to {limit} ayat. Make From and To closer together."
    return surah, first, last


def start_job(target, *args):
    jid = uuid.uuid4().hex[:12]
    JOBS[jid] = {"status": "running", "msg": "Queued"}
    threading.Thread(target=target, args=(jid, *args), daemon=True).start()
    return jsonify(id=jid)


def run_job(jid, surah, first, last, urdu):
    job = JOBS[jid]

    def log(msg):
        job["msg"] = msg

    try:
        log("Waiting for another video to finish" if RENDER_LOCK.locked() else "Starting")
        with RENDER_LOCK:
            s0, s1 = RANGES[surah]
            items = QURAN[s0 + first - 1:s0 + last]
            full = first == 1 and last == s1 - s0
            info = reel_info(items, 1, 1, full)
            name = f"surah_{surah}_{first}-{last}"
            mp4, thumb, title, desc, tags, secs = build_reel(
                items, info, WEB_OUT / jid, name, read_urdu=urdu, log=log,
                max_seconds=WEB_MAX_SECONDS)
        result = dict(video=mp4.name, thumb=thumb.name, title=title, desc=desc,
                      tags=", ".join(tags), seconds=round(secs))
        (WEB_OUT / jid / "meta.json").write_text(json.dumps(result, ensure_ascii=False))
        job.update(status="done", msg=f"Done: {int(secs // 60)} min {int(secs % 60)} s", **result)
    except TooLong as e:
        job.update(status="toolong", surah=surah,
                   msg=(f"This selection is about {e.seconds / 60:.0f} minutes long, too long for one reel. "
                        "Pick one of these parts (each ends at a ruku, up to 3 minutes):"),
                   parts=[{"from": a, "to": b, "seconds": round(s)} for a, b, s in e.parts])
    except Exception as e:  # show the error on the page
        job.update(status="error", msg=f"Failed: {e}")


def run_story(jid, surah, first, last, language):
    job = JOBS[jid]
    try:
        s0, s1 = RANGES[surah]
        items = QURAN[s0 + first - 1:s0 + last]
        info = reel_info(items, 1, 1, first == 1 and last == s1 - s0)
        job["msg"] = "Writing the reflection"
        data = reflect.generate(items, info, language)
        job["msg"] = "Drawing the story image"
        out = WEB_OUT / jid
        out.mkdir(parents=True, exist_ok=True)
        img = video.make_story(items, info, data, out / f"story_{surah}_{first}-{last}.png", language)
        caption = data["caption"] + "\n\n" + " ".join("#" + h for h in data["hashtags"])
        job.update(status="done", msg="Done", image=img.name, headline=data["headline"],
                   reflection=data["reflection"], action=data["action"], caption=caption)
    except reflect.ReflectionError as e:
        job.update(status="error", msg=str(e))
    except Exception as e:
        job.update(status="error", msg=f"Failed: {e}")


@app.get("/")
def index():
    return render_template("index.html", surahs=SURAHS, read_urdu=READ_URDU, story_max=STORY_MAX_AYAT)


@app.post("/api/generate")
def generate():
    d = request.get_json(force=True)
    p = pick(d)
    if isinstance(p, str):
        return jsonify(error=p), 400
    return start_job(run_job, *p, bool(d.get("urdu", True)))


@app.post("/api/story")
def story():
    d = request.get_json(force=True)
    if not reflect.available():
        return jsonify(error="Stories need a Claude API key. Set ANTHROPIC_API_KEY and restart the website."), 400
    p = pick(d, STORY_MAX_AYAT)
    if isinstance(p, str):
        return jsonify(error=p), 400
    lang = d.get("language") if d.get("language") in reflect.LANGUAGES else "roman"
    return start_job(run_story, *p, lang)


@app.get("/api/recent")
def recent():
    """Finished reels, newest first (survives page reloads and server restarts)."""
    out = []
    for meta in sorted(WEB_OUT.glob("*/meta.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:30]:
        d = json.loads(meta.read_text())
        d["id"] = meta.parent.name
        out.append(d)
    return jsonify(out)


@app.get("/api/job/<jid>")
def job(jid):
    if jid not in JOBS:
        abort(404)
    return jsonify(JOBS[jid])


@app.get("/files/<jid>/<path:name>")
def files(jid, name):
    if not JOB_ID.match(jid):
        abort(404)
    return send_from_directory(WEB_OUT / jid, name, as_attachment="dl" in request.args)
