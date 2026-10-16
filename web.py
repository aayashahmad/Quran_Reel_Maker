"""Local website: pick a surah, ayah range and translation language, generate a reel, download it.
Run with:  ./run.sh web   then open http://localhost:5050"""
import hashlib
import io
import os
import pathlib
import re
import shutil
import socket
import subprocess
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
import seo
import stats
import donation
import live
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
    reach the backup through the Cloudflare Worker, which adds X-Visitor-IP to its requests. /robots.txt stays
    open for keep-awake pings and health checks."""
    if (os.getenv("RENDER") and request.host.endswith(".onrender.com") and request.path != "/robots.txt"
            and "X-Visitor-IP" not in request.headers):
        resp = redirect("https://quranreelmaker.xyz" + request.full_path.rstrip("?"), 302)
        resp.headers["Cache-Control"] = "no-store"     # never remembered by browsers or Cloudflare
        return resp


BOTS = ("bot", "crawl", "spider", "slurp", "preview", "headless", "curl", "python-requests", "monitor")


@app.after_request
def counted(resp):
    """Anonymous daily totals for the admin dashboard (stats.py): no addresses, no typed text."""
    if resp.status_code != 200 or request.method not in ("GET", "POST"):
        return resp
    p, a = request.path, request.args
    if p == "/" or p in ("/surah", "/ask") or p.startswith(("/surah/", "/ask/")):
        ua = (request.headers.get("User-Agent") or "").lower()
        if any(b in ua for b in BOTS):
            stats.count("bot")
        else:
            stats.count("page")
            stats.count("home" if p == "/" else "surah_page" if p.startswith("/surah") else "ask_page")
    elif p == "/api/generate":
        d = request.get_json(silent=True) or {}
        stats.count("reel_cloud", surah=d.get("surah"), lang=d.get("lang"))
    elif p == "/api/meta":
        stats.count("reel_device", surah=a.get("surah"), lang=a.get("lang"))
    elif p == "/api/guide":
        d = resp.get_json(silent=True) or {}
        stats.count("ask" if d.get("found") else "ask_nomatch", topic=d.get("id"))
    elif p.startswith("/api/surah/"):
        stats.count("surah_loads", lang=a.get("lang"))
    return resp


@app.post("/api/ping")
def ping():
    """'This tab is open' from static/live.js, for the anonymous active-now count (live.py)."""
    d = request.get_json(silent=True, force=True) or {}
    live.ping(str(d.get("sid", "")), str(d.get("where", "")), str(d.get("act", "")), bool(d.get("leave")))
    return "", 204


@app.get("/api/public-config")
def public_config():
    """What the backup server copies from the main site: the switches and the donation box (no secrets)."""
    resp = jsonify(settings=site_settings.get(), donation=donation.get())
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.get("/donation-qr.png")
def donation_qr():
    if not donation.QR.exists():
        abort(404)
    return send_file(donation.QR, mimetype="image/png", max_age=300)


if os.getenv("RENDER"):                     # the backup copies the main site's switches and donation box
    donation.sync_from_main(seo.SITE, lambda values: site_settings.save(values) if values else None)


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
                           bgs=[{"style": s, "name": backgrounds.NAMES[s]} for s in backgrounds.STYLES],
                           jsonld=[seo.ld(j) for j in seo.home_ld()], faq=seo.HOME_FAQ,
                           donation=donation.get() if site_settings.get()["donation"] else None,
                           popular=[{"path": seo.surah_path(n), "name": seo.surah_names(n)} for n in seo.POPULAR],
                           topic_links=[{"path": seo.topic_path(t["id"]), "title": t["en"]} for t in public_topics()][:14])


FINISH_MAX = 150 * 1024 * 1024
FINISH_SLOTS = threading.Semaphore(2)


@app.post("/api/finish-video")
def finish_video():
    """A reel recorded in the browser (Android/Chrome: WebM, or MP4 without its length) made into a proper MP4
    that Instagram, WhatsApp and galleries read in full. H.264 video is only re-packed (seconds); other video
    is converted, which the small backup server can't do."""
    if (request.content_length or 0) > FINISH_MAX:
        return jsonify(error="This video is too big to finish here."), 413
    f = request.files.get("video")
    if not f:
        return jsonify(error="No video received."), 400
    if not FINISH_SLOTS.acquire(timeout=60):
        return jsonify(error="Busy, please try again in a minute."), 503
    work = WEB_OUT / f"finish_{uuid.uuid4().hex}"
    try:
        work.mkdir(parents=True)
        src, out = work / "in", work / "reel.mp4"
        f.save(src)
        codec = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name",
                                "-of", "csv=p=0", str(src)], capture_output=True, text=True, timeout=60).stdout.strip()
        if not codec:
            return jsonify(error="That is not a video we can read."), 400
        if codec == "h264":
            video = ["-c:v", "copy"]
        elif CLOUD_RENDER:
            video = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p"]
        else:
            return jsonify(error="convert-unavailable"), 503
        r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-fflags", "+genpts", "-i", str(src), *video,
                            "-r", "30", "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-movflags", "+faststart", str(out)],
                           capture_output=True, text=True, timeout=900)
        if r.returncode or not out.exists():
            return jsonify(error="Could not finish this video."), 500
        resp = send_file(io.BytesIO(out.read_bytes()), mimetype="video/mp4")
        resp.headers["Cache-Control"] = "no-store"
        return resp
    finally:
        FINISH_SLOTS.release()
        shutil.rmtree(work, ignore_errors=True)


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
    """Every page search engines should index: home, the 114 surahs, the Ask the Quran topics."""
    lastmod = time.strftime("%Y-%m-%d", time.gmtime(max(pathlib.Path(__file__).stat().st_mtime,
                                                        pathlib.Path(guidance.__file__).stat().st_mtime)))
    xml = ('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
           + seo.sitemap_urls(guidance.TOPICS, lastmod) + "</urlset>")
    return app.response_class(xml, mimetype="application/xml")


@app.get("/llms.txt")
def llms():
    """A plain summary of the site for AI assistants (llmstxt.org)."""
    return app.response_class(seo.llms_txt(guidance.TOPICS), mimetype="text/plain")


@app.get("/<key>.txt")
def indexnow_key(key):
    if key != seo.INDEXNOW_KEY:
        abort(404)
    return app.response_class(key, mimetype="text/plain")


@app.get("/favicon.ico")
def favicon():
    return send_from_directory(app.static_folder, "favicon.ico", max_age=604800)


def page(template, title, description, path, jsonld=(), **kw):
    resp = app.make_response(render_template(template, title=title, description=description, path=path,
                                             site=seo.SITE, jsonld=[seo.ld(j) for j in jsonld], static_v=STATIC_V, **kw))
    resp.headers["Cache-Control"] = "public, max-age=3600"
    return resp


EN_TR = []


def english():
    if not EN_TR:
        EN_TR.extend(texts("en", QURAN, log=lambda m: None))
    return EN_TR


@app.get("/surah")
def surah_index():
    item = lambda n: {"path": seo.surah_path(n), "name": seo.surah_names(n), "number": n, "ar": seo.BY_NUMBER[n]["name"],
                      "ayat": seo.BY_NUMBER[n]["numberOfAyahs"], "meaning": seo.BY_NUMBER[n]["englishNameTranslation"]}
    return page("surahs.html", "All 114 Surahs of the Quran with Urdu & English Translation | Quran Reel Maker",
                "Read all 114 surahs of the Quran in Arabic with Urdu and English translation, listen to Mishary "
                "Alafasy's recitation with word-by-word highlighting, and make Quran reels for free.", "/surah",
                [seo.breadcrumbs(("Home", "/"), ("Surahs", "/surah"))],
                popular=[item(n) for n in seo.POPULAR], surahs=[item(s["number"]) for s in seo.SURAHS])


@app.get("/surah/<int:n>")
@app.get("/surah/<int:n>-<name>")
def surah_page(n, name=None):
    if n not in seo.BY_NUMBER:
        abort(404)
    path = seo.surah_path(n)
    if request.path != path:
        return redirect(path, 301)
    s, en = seo.BY_NUMBER[n], english()
    s0, s1 = RANGES[n]
    ayat = [{"n": q["ayah"], "ar": q["ar"], "ur": q["ur"], "en": en[s0 + i]} for i, q in enumerate(QURAN[s0:s1])]
    names = seo.surah_names(n)
    other = lambda k: {"path": seo.surah_path(k), "name": seo.surah_names(k)} if k in seo.BY_NUMBER else None
    title = f"Surah {seo.ALIASES.get(n, s['englishName'])} with Urdu & English Translation | Read & Listen"
    first = " ".join(en[s0].split()[:22])
    desc = (f"Surah {s['englishName']} ({s['englishNameTranslation']}), surah {n}, {s['numberOfAyahs']} ayat: Arabic text "
            f"with Urdu and English translation and Mishary Alafasy's recitation. \u201c{first}…\u201d")
    chapter = {"@context": "https://schema.org", "@type": "Chapter", "name": f"Surah {s['englishName']}",
               "alternateName": [s["name"], f"Surah {seo.ALIASES.get(n, s['englishName'])}"],
               "position": n, "inLanguage": ["ar", "ur", "en"], "url": seo.SITE + path,
               "isPartOf": {"@type": "Book", "name": "The Holy Quran", "alternateName": "القرآن الكريم"},
               "description": f"{s['englishNameTranslation']}. {s['numberOfAyahs']} ayat, revealed in "
                              f"{'Makkah' if s['revelationType'] == 'Meccan' else 'Madinah'}."}
    return page("surah.html", title, desc[:300], path,
                [chapter, seo.breadcrumbs(("Home", "/"), ("Surahs", "/surah"), (f"Surah {s['englishName']}", path))],
                og_type="article", s=s, names=names, ayat=ayat, bismillah=n not in (1, 9),
                prev=other(n - 1), next=other(n + 1))


def public_topics():
    return [t for t in guidance.TOPICS if t["id"] not in seo.PRIVATE_TOPICS]


@app.get("/ask")
def topic_index():
    topics = [{"path": seo.topic_path(t["id"]), "q": seo.question(t), "title_ur": t["ur"]} for t in public_topics()]
    return page("topics.html", "What Does the Quran Say? Ayat & Sahih Hadith for Life's Problems | Quran Reel Maker",
                "What the Quran and authentic hadith say about anxiety, anger, grief, marriage, money, exams, guilt, "
                "hope and more, with every reference checked. In English and Urdu.", "/ask",
                [seo.breadcrumbs(("Home", "/"), ("Ask the Quran", "/ask"))], topics=topics)


@app.get("/ask/<tid>")
def topic_page(tid):
    t = guidance.BY_ID.get(tid)
    if not t or tid in seo.PRIVATE_TOPICS:
        abort(404)
    en, ur = english(), texts("ur", QURAN, log=lambda m: None)
    data = guidance.answer(tid, QURAN, RANGES, en, "en")
    for p in data["ayat"]:
        s0 = RANGES[p["surah"]][0]
        p["surah_path"] = seo.surah_path(p["surah"])
        for v in p["verses"]:
            v.update(en=en[s0 + v["n"] - 1], ur=ur[s0 + v["n"] - 1])
    hadith = [{"ref": f"{h['collection']} {h['number']}", "url": h["url"], "en": h["en"], "ur": h["ur"]} for h in t["hadith"]]
    data["hadith"] = hadith
    q, path = seo.question(t), seo.topic_path(tid)
    answer = t["guide_en"] + " " + " ".join(f"Quran {p['surah']}:{p['from']}" + (f"-{p['to']}" if p["to"] != p["from"] else "")
                                            + ": " + " ".join(v["en"] for v in p["verses"]) for p in data["ayat"][:2])
    faq = {"@context": "https://schema.org", "@type": "FAQPage",
           "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": answer}}]}
    others = [x for x in public_topics() if x["id"] != tid]
    ranked = [x for _, x in sorted(((len(set(x["words"].split()) & set(t["words"].split())), x) for x in others),
                                   key=lambda r: -r[0])][:4]
    return page("topic.html", f"{q} | Quran & Sahih Hadith", (t["guide_en"])[:300], path,
                [faq, seo.breadcrumbs(("Home", "/"), ("Ask the Quran", "/ask"), (t["en"], path))],
                og_type="article", t=data, q=q, guide_en=t["guide_en"], guide_ur=t["guide_ur"],
                related=[{"path": seo.topic_path(x["id"]), "q": seo.question(x)} for x in ranked])


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
