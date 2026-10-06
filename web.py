"""Local website: pick a surah, ayah range and translation language, generate a reel, download it.
Run with:  ./run.sh web   then open http://localhost:5050"""
import re
import shutil
import threading
import time
import uuid

from flask import Flask, abort, jsonify, render_template, request, send_from_directory

from config import WEB_OUT, READ_URDU
from quran_data import load_quran, surah_ranges
from content import reel_info
from main import build_reel, TooLong
from translations import LANGS

app = Flask(__name__)
QURAN = load_quran()
RANGES = surah_ranges(QURAN)
SURAHS = [{"n": s, "en": QURAN[a]["surah_en"], "ar": QURAN[a]["surah_ar"], "count": b - a}
          for s, (a, b) in sorted(RANGES.items())]
LANG_OPTIONS = [{"code": c, "name": l["name"], "native": l["native"], "translator": l["translator"],
                 "audio": bool(l["audio"]), "reader": l["reader"]} for c, l in LANGS.items()]
JOBS = {}
RENDER_LOCK = threading.Lock()      # one render at a time
JOB_ID = re.compile(r"^[0-9a-f]{12}$")
WEB_MAX_SECONDS = 10 * 60           # longer selections get a list of reel-sized parts instead
KEEP_SECONDS = 60 * 60              # made files are deleted after this, nothing is kept


def pick(d):
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
    return surah, first, last


def file_name(surah, first, last, lang="ur"):
    """Download name, e.g. Surah-Yusuf_12_1-5 (Urdu) or Surah-Yusuf_12_1-5_English."""
    en = re.sub(r"[^A-Za-z0-9-]+", "-", QURAN[RANGES[surah][0]]["surah_en"]).strip("-")
    return f"Surah-{en}_{surah}_{first}-{last}" + ("" if lang == "ur" else f"_{LANGS[lang]['name']}")


def cleanup():
    """Delete made files older than KEEP_SECONDS, and forget their jobs."""
    if not WEB_OUT.exists():
        return
    cutoff = time.time() - KEEP_SECONDS
    for d in WEB_OUT.iterdir():
        if d.is_dir() and d.stat().st_mtime < cutoff:
            shutil.rmtree(d, ignore_errors=True)
            JOBS.pop(d.name, None)


def start_job(target, *args):
    cleanup()
    jid = uuid.uuid4().hex[:12]
    JOBS[jid] = {"status": "running", "msg": "Queued"}
    threading.Thread(target=target, args=(jid, *args), daemon=True).start()
    return jsonify(id=jid)


def run_job(jid, surah, first, last, lang, read_aloud):
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
            name = file_name(surah, first, last, lang)
            mp4, thumb, title, desc, tags, secs = build_reel(
                items, info, WEB_OUT / jid, name, read_aloud=read_aloud, log=log,
                max_seconds=WEB_MAX_SECONDS, lang=lang)
        result = dict(video=mp4.name, thumb=thumb.name, title=title, desc=desc,
                      tags=", ".join(tags), seconds=round(secs))
        job.update(status="done", msg=f"Done: {int(secs // 60)} min {int(secs % 60)} s", **result)
    except TooLong as e:
        job.update(status="toolong", surah=surah,
                   msg=(f"This selection is about {e.seconds / 60:.0f} minutes long, too long for one reel. "
                        "Pick one of these parts (each ends at a ruku, up to 3 minutes):"),
                   parts=[{"from": a, "to": b, "seconds": round(s)} for a, b, s in e.parts])
    except Exception as e:  # show the error on the page
        job.update(status="error", msg=f"Failed: {e}")


@app.get("/")
def index():
    return render_template("index.html", surahs=SURAHS, langs=LANG_OPTIONS, read_urdu=READ_URDU)


@app.post("/api/generate")
def generate():
    d = request.get_json(force=True)
    p = pick(d)
    if isinstance(p, str):
        return jsonify(error=p), 400
    lang = d.get("lang", "ur")
    if lang not in LANGS:
        return jsonify(error="Unknown translation language."), 400
    return start_job(run_job, *p, lang, bool(d.get("read", d.get("urdu", True))))


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
