"""Local website: pick a surah, ayah range and translation language, generate a reel, download it.
Run with:  ./run.sh web   then open http://localhost:5050"""
import re
import shutil
import socket
import threading
import time
import uuid

from flask import Flask, abort, jsonify, render_template, request, send_file, send_from_directory

from config import WEB_OUT, READ_URDU
from quran_data import load_quran, surah_ranges, audio_url
from content import reel_info, metadata
from main import build_reel, TooLong
from quran_data import get_audio
import backgrounds
from translations import LANGS, NO_SPACES, texts

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
SERVER = socket.gethostname()
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
    return f"Surah-{en}_{surah}_{first}-{last}" + ("" if lang == "ur" else "_" + LANGS[lang]["name"].replace(" ", "-"))


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


@app.after_request
def served_by(resp):
    resp.headers["X-Served-By"] = SERVER     # which computer answered (main or backup)
    return resp


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


@app.get("/api/surah/<int:surah>")
def surah_data(surah):
    """A whole surah for reading and listening in the browser: Arabic words with their timings,
    the translation, and where each ayah's audio is online (the browser plays it from there)."""
    lang = request.args.get("lang", "ur")
    if surah not in RANGES or lang not in LANGS:
        abort(404)
    tr = texts(lang, QURAN, log=lambda m: None)
    voice = LANGS[lang]["audio"]
    s0, s1 = RANGES[surah]

    def ayah(it):
        return {"n": it["ayah"], "words": it["words"], "segments": it["segments"], "audio": audio_url(it),
                "tr": tr[it["n"] - 1], "tr_audio": audio_url(it, voice) if voice else None,
                "sajda": it["sajda"], "gn": it["n"],
                # same audio through this server, for making a reel on the device (islamic.network
                # doesn't allow other sites to read its files; Quran.com does)
                "tr_audio_local": f"/api/audio/{voice}/{it['n']}" if voice else None}
    first = QURAN[s0]
    return jsonify(surah=surah, en=first["surah_en"], ar=first["surah_ar"], lang=lang,
                   rtl=LANGS[lang]["rtl"], spaced=lang not in NO_SPACES,
                   bismillah=ayah(QURAN[0]) if first["bismillah"] else None,
                   ayat=[ayah(it) for it in QURAN[s0:s1]], styles=backgrounds.STYLES,
                   translator=LANGS[lang]["translator"], name=LANGS[lang]["name"], native=LANGS[lang]["native"],
                   font=LANGS[lang]["font"])


VOICES = {l["audio"] for l in LANGS.values() if l["audio"]}


@app.get("/api/audio/<edition>/<int:n>")
def audio(edition, n):
    """A translation recording, served from here (downloaded once and kept)."""
    if edition not in VOICES or not 1 <= n <= len(QURAN):
        abort(404)
    return send_file(get_audio(QURAN[n - 1], edition), mimetype="audio/mpeg", max_age=86400)


@app.get("/bg/<style>.mp4")
def background_loop(style):
    """A moving background loop, for reels made on the device."""
    if style not in backgrounds.STYLES:
        abort(404)
    return send_file(backgrounds.loop(style), mimetype="video/mp4", max_age=86400)


@app.get("/api/meta")
def meta():
    """Title, description and tags for a reel made on the device."""
    p = pick(request.args)
    lang = request.args.get("lang", "ur")
    if isinstance(p, str) or lang not in LANGS:
        return jsonify(error=p if isinstance(p, str) else "Unknown translation language."), 400
    surah, first, last = p
    s0, s1 = RANGES[surah]
    tr = texts(lang, QURAN, log=lambda m: None)
    items = [dict(it, tr=tr[it["n"] - 1]) for it in QURAN[s0 + first - 1:s0 + last]]
    info = reel_info(items, 1, 1, first == 1 and last == s1 - s0)
    read = request.args.get("read") == "1" and bool(LANGS[lang]["audio"])
    title, desc, tags = metadata(items, info, read, lang)
    return jsonify(title=title, desc=desc, tags=", ".join(tags), name=file_name(surah, first, last, lang))


SITE = "https://quranreelmaker.xyz"


@app.get("/sitemap.xml")
def sitemap():
    """The pages search engines should index."""
    urls = "".join(f"<url><loc>{SITE}{path}</loc></url>" for path in ["/"])
    xml = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'
    return app.response_class(xml, mimetype="application/xml")


@app.get("/robots.txt")
def robots():
    """Allow everything and point to the sitemap (Cloudflare adds its own lines above these)."""
    return app.response_class(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n", mimetype="text/plain")


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
