"""Local website: pick a surah, ayah range and translation language, generate a reel, download it.
Run with:  ./run.sh web   then open http://localhost:5050"""
import hashlib
import os
import pathlib
import re
import shutil
import socket
import threading
import time
import uuid

from flask import Flask, abort, jsonify, redirect, render_template, request, send_file, send_from_directory

from config import WEB_OUT, READ_URDU, CLOUD_RENDER
from quran_data import load_quran, surah_ranges, audio_url, LOCAL_AUDIO, local_audio_complete
from content import reel_info, metadata
from main import build_reel, TooLong
from quran_data import get_audio
import admin
import backgrounds
import guidance
import quran_search
import protect
import site_settings
from translations import LANGS, NO_SPACES, texts

app = Flask(__name__)
admin.setup(app)
protect.setup(app)
QURAN = load_quran()
RANGES = surah_ranges(QURAN)
SURAHS = [{"n": s, "en": QURAN[a]["surah_en"], "ar": QURAN[a]["surah_ar"], "count": b - a}
          for s, (a, b) in sorted(RANGES.items())]


def voice(lang):
    """The translation recording used for this language now, or None (the owner can switch off
    Kashmiri's AI voice on the admin page)."""
    rec = LANGS[lang]["audio"]
    if lang == "ks" and not site_settings.get()["kashmiri_audio"]:
        return None
    if rec in LOCAL_AUDIO and not _complete(rec):   # used only once every ayah has been made
        return None
    return rec


_done = {}


def _complete(edition):
    """local_audio_complete, re-checked at most once a minute (it lists 6,236 files)."""
    ok, at = _done.get(edition, (False, 0))
    if not ok and time.time() - at > 60:
        ok = local_audio_complete(edition)
        _done[edition] = (ok, time.time())
    return ok


def lang_options():
    return [{"code": c, "badge": "RU" if c == "ur-roman" else c, "name": l["name"], "native": l["native"], "translator": l["translator"],
             "audio": bool(voice(c)), "reader": l["reader"]} for c, l in LANGS.items()]
JOBS = {}
RENDER_LOCK = threading.Lock()      # one render at a time
JOB_ID = re.compile(r"^[0-9a-f]{12}$")
SERVER = os.getenv("SERVER_NAME") or ("render-backup" if os.getenv("RENDER") else socket.gethostname())
# version tag for static files, from their contents: a changed file gets a new URL, so browsers and
# Cloudflare (which keep static files for hours) never run an old copy
STATIC_V = hashlib.sha256(b"".join(p.read_bytes() for p in sorted(pathlib.Path(app.static_folder).glob("*")))).hexdigest()[:10]
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


def clean_question(q):
    """A visitor's question for the reel's title card: one line of plain text, at most 140 characters."""
    q = re.sub(r"[\x00-\x1f\x7f]", " ", str(q or ""))
    return re.sub(r"\s+", " ", q).strip()[:140]


def run_job(jid, surah, first, last, lang, read_aloud, bg, question=""):
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
                max_seconds=WEB_MAX_SECONDS, lang=lang, bg=bg, question=question)
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


@app.before_request
def only_through_the_domain():
    """The backup's own address (quran-reel-maker.onrender.com) sends people to quranreelmaker.xyz: visitors
    reach the backup through the Cloudflare Worker, which marks its requests with CF-Worker. /robots.txt stays
    open for keep-awake pings and health checks."""
    if (os.getenv("RENDER") and request.host.endswith(".onrender.com") and request.path != "/robots.txt"
            and request.headers.get("CF-Worker") != "quranreelmaker.xyz"):
        return redirect("https://quranreelmaker.xyz" + request.full_path.rstrip("?"), 301)


@app.after_request
def served_by(resp):
    resp.headers["X-Served-By"] = SERVER     # which computer answered (main or backup)
    return resp


@app.get("/")
def index():
    return render_template("index.html", surahs=SURAHS, langs=lang_options(), read_urdu=READ_URDU,
                           device_generation=site_settings.get()["device_generation"], static_v=STATIC_V,
                           cloud_generation=CLOUD_RENDER,
                           ask_quran=site_settings.get()["ask_quran"], guide_topics=guidance.topic_list(),
                           bgs=[{"style": s, "name": backgrounds.NAMES[s]} for s in backgrounds.STYLES])


@app.post("/api/generate")
def generate():
    if not CLOUD_RENDER:
        return jsonify(error="Cloud reels are paused for a while. Please use Generate on this device."), 503
    d = request.get_json(force=True)
    p = pick(d)
    if isinstance(p, str):
        return jsonify(error=p), 400
    lang = d.get("lang", "ur")
    if lang not in LANGS:
        return jsonify(error="Unknown translation language."), 400
    bg = d.get("bg") or None                  # None = pick from the surah and ayah
    if bg is not None and bg not in backgrounds.STYLES:
        return jsonify(error="Unknown background."), 400
    read = bool(d.get("read", d.get("urdu", True))) and voice(lang) is not None
    return start_job(run_job, *p, lang, read, bg, clean_question(d.get("question")))


@app.get("/api/surah/<int:surah>")
def surah_data(surah):
    """A whole surah for reading and listening in the browser: Arabic words with their timings,
    the translation, and where each ayah's audio is online (the browser plays it from there)."""
    lang = request.args.get("lang", "ur")
    if surah not in RANGES or lang not in LANGS:
        abort(404)
    tr = texts(lang, QURAN, log=lambda m: None)
    rec = voice(lang)
    s0, s1 = RANGES[surah]

    def ayah(it):
        return {"n": it["ayah"], "words": it["words"], "segments": it["segments"], "audio": audio_url(it),
                "tr": tr[it["n"] - 1], "tr_audio": audio_url(it, rec) if rec else None,
                "sajda": it["sajda"], "gn": it["n"],
                # same audio through this server, for making a reel on the device (islamic.network
                # doesn't allow other sites to read its files; Quran.com does)
                "tr_audio_local": f"/api/audio/{rec}/{it['n']}" if rec else None}
    first = QURAN[s0]
    return jsonify(surah=surah, en=first["surah_en"], ar=first["surah_ar"], lang=lang,
                   rtl=LANGS[lang]["rtl"], spaced=lang not in NO_SPACES,
                   bismillah=ayah(QURAN[0]) if first["bismillah"] else None,
                   ayat=[ayah(it) for it in QURAN[s0:s1]], styles=backgrounds.STYLES,
                   translator=LANGS[lang]["translator"], name=LANGS[lang]["name"], native=LANGS[lang]["native"],
                   font=LANGS[lang]["font"], shape=LANGS[lang]["shape"] or lang)


VOICES = {l["audio"] for l in LANGS.values() if l["audio"]}


@app.get("/api/audio/<edition>/<int:n>")
def audio(edition, n):
    """A translation recording, served from here (downloaded once and kept)."""
    if edition not in VOICES or not 1 <= n <= len(QURAN):
        abort(404)
    try:
        path = get_audio(QURAN[n - 1], edition)
    except FileNotFoundError:            # a local recording not made yet
        abort(404)
    return send_file(path, mimetype="audio/mpeg", max_age=86400)


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
    read = request.args.get("read") == "1" and voice(lang) is not None
    title, desc, tags = metadata(items, info, read, lang)
    return jsonify(title=title, desc=desc, tags=", ".join(tags), name=file_name(surah, first, last, lang))


SITE = "https://quranreelmaker.xyz"


@app.get("/privacy")
@app.get("/terms")
def legal():
    return render_template("legal.html", page=request.path.strip("/"))


@app.get("/sitemap.xml")
def sitemap():
    """The pages search engines should index."""
    urls = "".join(f"<url><loc>{SITE}{path}</loc></url>" for path in ["/", "/privacy", "/terms"])
    xml = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'
    return app.response_class(xml, mimetype="application/xml")


@app.get("/robots.txt")
def robots():
    """Allow everything and point to the sitemap (Cloudflare adds its own lines above these)."""
    rules = "User-agent: *\nAllow: /\nDisallow: /api/\nDisallow: /files/\nDisallow: /bg/\nDisallow: /admin\n"
    return app.response_class(f"{rules}\nSitemap: {SITE}/sitemap.xml\n", mimetype="text/plain")


@app.get("/api/guide")
def guide():
    """Ask the Quran: ?q=<the visitor's words> or ?topic=<id>, &lang=<translation>."""
    if not site_settings.get()["ask_quran"]:
        abort(404)
    lang = request.args.get("lang", "en")
    if lang not in LANGS:
        lang = "en"
    q, topic = (request.args.get("q") or "")[:500], request.args.get("topic")
    tr = texts(lang, QURAN, log=lambda m: None)
    data = None
    if topic not in guidance.BY_ID:
        ranked = guidance.match(q)
        best, topic = ranked[0] if ranked else (0, None)
        # an explained topic answers when it covers most of the question; otherwise search the whole Quran
        # and Sahih al-Bukhari / Muslim, and offer the nearest topics as related
        if best < 100 and not (best >= 2 and guidance.coverage(quran_search.content_words(q), topic) >= 0.6):
            data = quran_search.search(q, QURAN, RANGES, tr, lang)
            related = [t for s, t in ranked[:2] if s >= 3 and t != "crisis"]
        if data is None:
            if best < 2:
                return jsonify(found=False, topics=guidance.topic_list())
            related = [t for s, t in ranked[1:3] if s >= 2 and t != "crisis"]
    else:
        related = []
    data = data or guidance.answer(topic, QURAN, RANGES, tr, lang)
    rec = voice(lang)
    for p in data["ayat"]:                  # audio + word timings, so each passage can play in its own card
        s0 = RANGES[p["surah"]][0]
        for v in p["verses"]:
            it = QURAN[s0 + v["n"] - 1]
            v.update(words=it["words"], segments=it["segments"], audio=audio_url(it),
                     tr_audio=audio_url(it, rec) if rec else None)
    data["related"] = [{"id": t, "title": guidance.BY_ID[t]["en"]} for t in related]
    data["spaced"] = lang not in NO_SPACES       # translation can be highlighted word by word
    return jsonify(found=True, **data)


@app.get("/admin/guidance")
def guidance_review():
    """Owner-only list of every topic with its full ayat, hadith and guidance, for checking."""
    if not admin.is_admin():
        return redirect("/admin", code=303)
    tr = texts("ur", QURAN, log=lambda m: None)
    en = texts("en", QURAN, log=lambda m: None)
    items = []
    for t in guidance.TOPICS:
        a = guidance.answer(t["id"], QURAN, RANGES, en, "en")
        for p in a["ayat"]:
            s0 = RANGES[p["surah"]][0]
            for v in p["verses"]:
                v["ur"] = tr[s0 + v["n"] - 1]
        items.append(dict(a, words=t["words"], guide_en=t["guide_en"], guide_ur=t["guide_ur"],
                          hadith_full=t["hadith"]))
    return render_template("guidance_review.html", items=items), 200, {"Cache-Control": "no-store",
                                                                      "X-Robots-Tag": "noindex"}


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
