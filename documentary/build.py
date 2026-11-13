"""Seerah documentaries: long-form, 16:9 YouTube episodes made from the Seerah chapters (seerah.py), which are
already checked word for word (every ayah and sahih hadith) and already narrated (seerah_audio/: English in Ryan,
Urdu in the Hayatus narrator). Nothing new is written here: an episode only joins chapters, adds a drawn map of the
real places for each chapter, and shows each ayah and hadith on a card with its reference while it is heard.
No people, prophets, Companions or angels are drawn: only places, land, sky and paper.

  python -m documentary list
  python -m documentary make battles --lang en       ->  output/documentary/<episode>-<lang>.mp4 (+ .txt with title,
                                                         description, YouTube chapters and every source)
"""
import json
import math
import random
import re
import shutil
import subprocess
from contextlib import contextmanager
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

import video
from video import font, shape, text_w, wrap
from qissa import art

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "documentary"
W, H = 1920, 1080
PAD = 1.10                                     # backgrounds drawn larger, for a slow pan
BW, BH = int(W * PAD), int(H * PAD)
GAP = 0.6                                      # silence after each narrated block
CARD_SECONDS, TITLE_SECONDS, END_SECONDS = 7.0, 7.0, 14.0     # the end screen needs 5-20 s for YouTube's end elements
SERIF, AR, UR = "Amiri-Regular.ttf", "AmiriQuran-Regular.ttf", "NotoNastaliqUrdu.ttf"
INK, CRIMSON, PARCH = art.INK, art.CRIMSON, art.PARCHMENT
SITE = "quranreelmaker.xyz"

EPISODES = {
    "makkah-early": {"chapters": [1, 2, 3], "en": "Makkah: The Early Years", "ur": "مکہ: ابتدائی سال"},
    "makkah-trials": {"chapters": [4, 5, 6], "en": "Makkah: Years of Trial", "ur": "مکہ: آزمائش کے سال"},
    "hijrah": {"chapters": [7, 8, 9, 10], "en": "The Hijrah and the New Community", "ur": "ہجرت اور مدینہ کا نیا معاشرہ"},
    "battles": {"chapters": [11, 12, 13], "en": "The Battles: Badr, Uhud and the Trench", "ur": "غزوات: بدر، احد اور خندق"},
    "treaty-to-victory": {"chapters": [14, 15, 16], "en": "From Hudaibiya to the Conquest of Makkah",
                          "ur": "حدیبیہ سے فتح مکہ تک"},
    "final-years": {"chapters": [17, 18, 19, 20], "en": "The Final Years", "ur": "آخری سال"},
    "character": {"chapters": [21, 22, 23, 24], "en": "His Character ﷺ", "ur": "آپ ﷺ کے اخلاق"},
}

# real places (lat, lon) and their names; the map is drawn from these, not imagined
PLACES = {"makkah": (21.42, 39.83, "Makkah", "مکہ"), "madinah": (24.47, 39.61, "Madinah", "مدینہ"),
          "badr": (23.78, 38.79, "Badr", "بدر"), "taif": (21.27, 40.42, "Ta'if", "طائف"),
          "hudaibiya": (21.44, 39.60, "Hudaibiya", "حدیبیہ"), "hunayn": (21.50, 40.06, "Hunayn", "حنین"),
          "tabuk": (28.38, 36.57, "Tabuk", "تبوک"), "khaybar": (25.70, 39.29, "Khaybar", "خیبر"),
          "jerusalem": (31.78, 35.23, "Jerusalem", "بیت المقدس")}
# chapter id -> (places marked, route from -> to, a note under the name)
MAPS = {"birth-and-early-life": (["makkah"], None), "the-first-revelation": (["makkah"], None),
        "the-call-in-public": (["makkah"], None), "persecution-in-makkah": (["makkah"], None),
        "the-year-of-sorrow-and-taif": (["makkah", "taif"], ("makkah", "taif")),
        "al-isra-wal-miraj": (["makkah", "jerusalem"], ("makkah", "jerusalem")),
        "the-pledges-of-aqabah": (["makkah", "madinah"], None), "the-hijrah": (["makkah", "madinah"], ("makkah", "madinah")),
        "building-the-community-in-madinah": (["madinah"], None), "the-change-of-the-qiblah": (["madinah", "makkah"], None),
        "the-battle-of-badr": (["madinah", "badr"], ("madinah", "badr")), "the-battle-of-uhud": (["madinah"], None),
        "the-battle-of-the-trench": (["madinah"], None),
        "the-treaty-of-hudaibiya": (["madinah", "hudaibiya", "makkah"], ("madinah", "hudaibiya")),
        "letters-to-the-kings": (["madinah"], None), "the-conquest-of-makkah": (["madinah", "makkah"], ("madinah", "makkah")),
        "the-battle-of-hunayn": (["makkah", "hunayn"], ("makkah", "hunayn")),
        "tabuk-and-kab-ibn-malik": (["madinah", "tabuk"], ("madinah", "tabuk")),
        "the-farewell-hajj": (["madinah", "makkah"], ("madinah", "makkah")), "his-illness-and-passing": (["madinah"], None)}
NOTE = {"the-battle-of-uhud": ("Mount Uhud, just north of Madinah", "جبلِ احد، مدینہ کے شمال میں"),
        "the-battle-of-the-trench": ("The trench was dug on Madinah's open side", "خندق مدینہ کی کھلی جانب کھودی گئی")}
# the Red Sea and the Gulf of Aqaba, from real coastal towns (Jeddah, Rabigh, Yanbu, Umluj, al-Wajh, Duba, Aqaba, Sinai)
COAST = [(19.13, 41.08), (20.15, 40.27), (21.49, 39.18), (22.80, 39.03), (24.09, 38.06), (25.02, 37.27), (26.24, 36.45),
         (27.35, 35.69), (28.05, 34.80), (29.29, 34.94), (29.53, 35.00), (29.49, 34.89), (28.97, 34.66), (28.50, 34.51),
         (27.91, 34.33), (27.73, 34.25), (28.24, 33.62), (29.60, 32.70), (29.97, 32.55), (29.60, 32.35), (29.10, 32.65),
         (28.35, 33.10), (27.26, 33.81), (26.73, 33.94), (26.10, 34.28), (25.07, 34.89), (23.95, 35.48), (22.22, 36.64),
         (19.60, 37.20), (17.0, 38.6), (17.0, 42.0)]           # the Red Sea, its gulfs and both shores (real towns)
MED = [(31.26, 32.30), (31.13, 33.80), (31.50, 34.45), (32.05, 34.75), (32.80, 34.95), (33.50, 35.30), (35.0, 35.6),
       (35.0, 28.0), (31.0, 28.0)]                             # the Mediterranean shore from Port Said to Lebanon
LAT0, LAT1, LON0, LON1 = 20.3, 32.3, 34.0, 41.2

TEXT = {"en": {"series": "SEERAH OF THE PROPHET ﷺ · A DOCUMENTARY", "chapter": "Chapter", "quran": "The Quran",
               "hadith": "Sahih hadith", "end1": "The full Seerah, to read and listen to:", "sub": "Subscribe for the next episode",
               "sources": "Every ayah and hadith is quoted word for word and checked on sunnah.com"},
        "ur": {"series": "سیرت النبی ﷺ · دستاویزی سلسلہ", "chapter": "باب", "quran": "قرآن مجید", "hadith": "صحیح حدیث",
               "end1": "مکمل سیرت پڑھیں اور سنیں:", "sub": "اگلی قسط کے لیے سبسکرائب کریں",
               "sources": "ہر آیت اور حدیث لفظ بہ لفظ، sunnah.com سے جانچی گئی"}}


# ---------- drawing ----------
def _draw_text(d, lines, f, x0, y, width, color, lang, lh, align="center"):
    rtl = lang in ("ur", "ar")
    for ln in lines:
        s = shape(ln) if rtl else ln
        w = text_w(f, s, rtl, lang if rtl else None)
        x = x0 + (width - w) / 2 if align == "center" else x0
        d.text((x, y), s, font=f, fill=color, **(dict(direction="rtl", language=lang) if rtl and video.RAQM else {}))
        y += int(f.size * lh)
    return y


def _fit(text, fname, width, height, size, min_size, lh, lang):
    rtl = lang in ("ur", "ar")
    while True:
        f = font(fname, size)
        lines = wrap(text, f, width, rtl, lang if rtl else None)
        if len(lines) * size * lh <= height or size <= min_size:
            return f, lines
        size -= 2


@contextmanager
def _wide_art():
    """The Qissa Paper Atlas drawings, drawn 16:9."""
    saved = art.W, art.H, art.BW, art.BH, art._wave.__defaults__
    art.W, art.H, art.BW, art.BH = W, H, BW, BH
    art._wave.__defaults__ = (BW, BH)
    try:
        yield
    finally:
        art.W, art.H, art.BW, art.BH, art._wave.__defaults__ = saved


def desert(seed, night=False):
    rnd = random.Random(seed)
    sky = ((22, 26, 44), (52, 46, 58)) if night else ((226, 186, 132), (238, 214, 170))
    img = art._paper(BW, BH, *sky, 0.12)
    d = ImageDraw.Draw(img)
    if night:
        for _ in range(140):
            x, y, r = rnd.uniform(0, BW), rnd.uniform(0, BH * 0.6), rnd.uniform(0.8, 2.4)
            d.ellipse([x - r, y - r, x + r, y + r], fill=(220, 214, 196))
        cx, cy = BW * rnd.uniform(0.62, 0.8), BH * 0.2               # a crescent
        d.ellipse([cx - 46, cy - 46, cx + 46, cy + 46], fill=(236, 226, 196))
        d.ellipse([cx - 28, cy - 54, cx + 58, cy + 38], fill=sky[0])
    else:
        sun = Image.new("L", img.size, 0)
        sx = BW * rnd.uniform(0.25, 0.75)
        ImageDraw.Draw(sun).ellipse([sx - 120, BH * 0.30, sx + 120, BH * 0.30 + 240], fill=210)
        img.paste((250, 228, 180), (0, 0), sun.filter(ImageFilter.GaussianBlur(30)))
    dunes = [(52, 44, 50), (40, 34, 40), (28, 24, 30)] if night else [(206, 160, 104), (186, 138, 86), (160, 114, 70)]
    for i, (y, col) in enumerate([(0.58, dunes[0]), (0.70, dunes[1]), (0.84, dunes[2])]):
        art._layer(img, art._wave(BH * y, 34 - i * 6, rnd.uniform(220, 360), rnd.uniform(0, 6), BW, BH), col, 18, rnd)
    return img


def _palm(img, x, base, h, rnd, color):
    d = ImageDraw.Draw(img)
    lean = rnd.uniform(-0.12, 0.12)
    top = (x + lean * h, base - h)
    d.line([(x, base), top], fill=color, width=max(6, int(h * 0.05)))
    for i in range(9):                                         # fronds: drooping arcs from the crown
        a = -math.pi * (0.05 + 0.9 * i / 8)
        pts = [(top[0] + h * 0.42 * t * math.cos(a), top[1] + h * 0.42 * t * math.sin(a) + h * 0.32 * t * t)
               for t in [j / 10 for j in range(11)]]
        d.line(pts, fill=color, width=max(4, int(h * 0.028)))


def oasis(seed):
    """Date palms by the wells: the land around Madinah (and Badr), no buildings, no people."""
    rnd = random.Random(seed)
    img = desert(seed)
    for i in range(rnd.randint(5, 8)):
        x = rnd.uniform(0.05, 0.95) * BW
        _palm(img, x, BH * rnd.uniform(0.70, 0.80), rnd.uniform(220, 380), rnd, (70 + rnd.randint(0, 20), 62, 40))
    art._layer(img, art._wave(BH * 0.86, 16, 300, rnd.uniform(0, 6), BW, BH), (150, 106, 64), 18, rnd)
    return img


def background(kind, seed):
    if kind in ("desert", "night"):
        return desert(seed, kind == "night")
    if kind == "oasis":
        return oasis(seed)
    with _wide_art():
        return art.draw(kind, seed)


def scene_for(text, k):
    t = text.lower()
    if re.search(r"night|dark|cave|slept|sleep|dawn prayer|tahajjud|رات|غار", t):
        return "night"
    if re.search(r"makkah|madinah|city|town|house|home|mosque|masjid|market|مکہ|مدینہ|مسجد|گھر", t):
        return "oasis"
    return "desert"


def _bounds(keys):
    """Map bounds around the places (at least 4.5 degrees tall), shaped to fill the left half of the frame."""
    lats = [PLACES[k][0] for k in keys] or [22.9]
    lons = [PLACES[k][1] for k in keys] or [39.7]
    clat, clon = (max(lats) + min(lats)) / 2, (max(lons) + min(lons)) / 2
    span_lat = max(4.5, (max(lats) - min(lats)) * 1.5)
    k = math.cos(math.radians(clat))
    aspect = (BW * 0.52 - 140) / (BH - 160)                  # box width / height
    span_lon = max(span_lat * aspect / k, (max(lons) - min(lons)) * 1.5)
    span_lat = max(span_lat, span_lon * k / aspect)
    return clat - span_lat / 2, clat + span_lat / 2, clon - span_lon / 2, clon + span_lon / 2


def _xy(lat, lon, box, b):
    x0, y0, w, h = box
    la0, la1, lo0, lo1 = b
    return x0 + (lon - lo0) / (lo1 - lo0) * w, y0 + (la1 - lat) / (la1 - la0) * h


def map_image(cid, lang):
    """A parchment map with the chapter's real places (and the journey, if there was one), zoomed to them."""
    rnd = random.Random(cid)
    img = art._paper(BW, BH, PARCH, (214, 198, 160), 0.14)
    places, route = MAPS.get(cid, ([], None))
    b = _bounds(places)
    box = (90, 80, BW * 0.52 - 140, BH - 160)
    sea = art._paper(BW, BH, PARCH, (214, 198, 160), 0.14)
    for shore in (COAST, MED):
        art._layer(sea, [_xy(la, lo, box, b) for la, lo in shore], art.SEA, 14, rnd)
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rectangle([box[0], box[1], box[0] + box[2], box[1] + box[3]], fill=255)
    img.paste(sea, (0, 0), mask)
    d = ImageDraw.Draw(img)
    d.rectangle([box[0], box[1], box[0] + box[2], box[1] + box[3]], outline=INK, width=3)
    if route:
        a, c = (_xy(*PLACES[p][:2], box, b) for p in route)
        bend = 0.15 * math.dist(a, c)
        pts = [(a[0] + (c[0] - a[0]) * t + bend * math.sin(math.pi * t), a[1] + (c[1] - a[1]) * t)
               for t in [i / 40 for i in range(41)]]
        for i in range(0, 40, 2):
            d.line([pts[i], pts[i + 1]], fill=CRIMSON, width=8)
    f = font(UR if lang == "ur" else SERIF, 46 if lang == "ur" else 50)
    small = font(UR if lang == "ur" else SERIF, 34 if lang == "ur" else 36)
    inside = lambda x, y: box[0] + 20 < x < box[0] + box[2] - 20 and box[1] + 20 < y < box[1] + box[3] - 20
    for key, (lat, lon, en, ur) in PLACES.items():
        x, y = _xy(lat, lon, box, b)
        if not inside(x, y):
            continue
        main = key in places
        r = 14 if main else 8
        if not main and any(math.dist((x, y), _xy(*PLACES[m][:2], box, b)) < 90 for m in places):
            continue                                          # a nearby context town would cover the chapter's place
        d.ellipse([x - r, y - r, x + r, y + r], fill=CRIMSON if main else INK, outline=INK, width=3)
        ff = f if main else small
        name = ur if lang == "ur" else en
        sh = shape(name) if lang == "ur" else name
        tw = text_w(ff, sh, lang == "ur", "ur" if lang == "ur" else None)
        tx = x + 26 if x + 26 + tw < box[0] + box[2] - 10 else x - 26 - tw
        d.text((tx, y - ff.size * (0.95 if lang == "ur" else 0.62)), sh, font=ff, fill=INK if main else (110, 86, 60),
               **(dict(direction="rtl", language="ur") if lang == "ur" and video.RAQM else {}))
    art._compass(img, box[0] + box[2] - 90, box[1] + 100, 60)
    return img


def strip(img, text, lang, y_top=None):
    """Narration subtitle on a torn parchment strip at the bottom (the Qissa Paper Atlas look)."""
    d = ImageDraw.Draw(img)
    fname, lh = (UR, 1.95) if lang == "ur" else (SERIF, 1.32)
    f, lines = _fit(text, fname, W - 360, 230, 50 if lang == "en" else 44, 34, lh, lang)
    hgt = len(lines) * f.size * lh + 60
    y0 = y_top or H - hgt - 70
    rnd = random.Random(text)
    top = [(x, y0 + rnd.uniform(-6, 6)) for x in range(120, W - 119, 40)]
    bot = [(x, y0 + hgt + rnd.uniform(-6, 6)) for x in range(W - 120, 119, -40)]
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).polygon([(x + 6, y + 10) for x, y in top + bot], fill=(0, 0, 0, 110))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
    d.polygon(top + bot, fill=(*PARCH, 244))
    _draw_text(d, lines, f, 180, y0 + 26, W - 360, INK, lang, lh)


def card(img, head, ref, body, lang, arabic=None):
    """An ayah or hadith on a parchment card in the middle, with its reference."""
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = 230, 110, W - 230, H - 120
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([x0 + 10, y0 + 14, x1 + 10, y1 + 14], 18, fill=(0, 0, 0, 130))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    d.rounded_rectangle([x0, y0, x1, y1], 18, fill=(*PARCH, 250), outline=(*art.GOLD_PAPER, 255), width=4)
    hf = font(UR if lang == "ur" else SERIF, 34 if lang == "ur" else 36)
    y = _draw_text(d, [head], hf, x0, y0 + 34, x1 - x0, CRIMSON, lang, 1.6)
    d.line([(W / 2 - 140, y + 6), (W / 2 + 140, y + 6)], fill=(*art.GOLD_PAPER, 255), width=3)
    y += 36
    room = y1 - 110 - y
    if arabic:
        f, lines = _fit(arabic, AR, x1 - x0 - 140, room * 0.45, 58, 36, 1.75, "ar")
        y = _draw_text(d, lines, f, x0 + 70, y, x1 - x0 - 140, INK, "ar", 1.75) + 14
        room = y1 - 110 - y
    fname, lh = (UR, 1.95) if lang == "ur" else (SERIF, 1.38)
    f, lines = _fit(body, fname, x1 - x0 - 160, room, 56 if lang == "en" else 48, 26, lh, lang)
    used = len(lines) * f.size * lh
    _draw_text(d, lines, f, x0 + 80, y + max(0, (room - used) / 2 - 10), x1 - x0 - 160, INK, lang, lh)
    rf = font(SERIF, 30)
    _draw_text(d, [ref], rf, x0, y1 - 74, x1 - x0, (120, 90, 60), "en", 1.3)


def label(img, text, lang):
    d = ImageDraw.Draw(img)
    f = font(UR if lang == "ur" else SERIF, 30 if lang == "ur" else 30)
    s = shape(text) if lang == "ur" else text
    tw = text_w(f, s, lang == "ur", "ur" if lang == "ur" else None)
    d.rounded_rectangle([40, 30, 40 + tw + 44, 30 + f.size * (2.0 if lang == "ur" else 1.6)], 10, fill=(20, 16, 12, 150))
    d.text((62, 36 if lang == "en" else 26), s, font=f, fill=(240, 226, 196),
           **(dict(direction="rtl", language="ur") if lang == "ur" and video.RAQM else {}))
    wf = font(SERIF, 28)
    d.text((W - text_w(wf, SITE, False, None) - 40, H - 52), SITE, font=wf, fill=(240, 226, 196, 200))


def title_overlay(lines, lang, dark=True, x0=0, width=W):
    """Big centred lines (episode / chapter / end titles), wrapped to fit, over a dimmed background."""
    img = Image.new("RGBA", (W, H), (10, 8, 6, 120) if dark else (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    blocks = []
    for text, size, color in lines:
        lg = "ur" if lang == "ur" and not text.isascii() else "en"
        lh = 1.9 if lg == "ur" else 1.3
        f, wl = _fit(text, UR if lg == "ur" else SERIF, width - 120, size * lh * 2.2, size, 26, lh, lg)
        blocks.append((f, wl, color, lg, lh))
    total = sum(len(wl) * f.size * lh + f.size * 0.35 for f, wl, _, _, lh in blocks)
    y = (H - total) / 2
    for f, wl, color, lg, lh in blocks:
        y = _draw_text(d, wl, f, x0 + 60, y, width - 120, color, lg, lh) + f.size * 0.35
    return img


# ---------- the episode ----------
def _pages(text, max_words):
    """Split a long text into pages at sentence ends (each page shown for its share of the narration)."""
    parts = re.split(r"(?<=[.?!۔؟:])\s+", text.strip())
    pages, cur = [], []
    for p in parts:
        if cur and len(" ".join(cur + [p]).split()) > max_words:
            pages.append(" ".join(cur))
            cur = []
        cur.append(p)
    if cur:
        pages.append(" ".join(cur))
    out = []
    for p in pages:                                       # one very long sentence: cut by words
        w = p.split()
        out += [" ".join(w[i:i + max_words]) for i in range(0, len(w), max_words)] if len(w) > max_words * 1.4 else [p]
    return out


def duration(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout)


def plan(eid, lang):
    """Every segment of the episode: (background, overlay, seconds, audio or None), plus YouTube chapters and sources."""
    import seerah
    import web
    ep = EPISODES[eid]
    T = TEXT[lang]
    by_n = {c["n"]: c for c in seerah.CHAPTERS}
    units, chapters, sources, groups, t = [], [], [], [], 0.0
    used_photos = {}

    def add(bg, ov, secs, audio=None, cut=None):
        nonlocal t
        units.append({"bg": bg, "ov": ov, "seconds": secs, "audio": audio, "audio_seconds": cut})
        t += secs

    first = by_n[ep["chapters"][0]]
    add(("map", first["id"]), ("title", [(T["series"], 40, art.GOLD_PAPER), (ep[lang], 92, (250, 240, 214))]),
        TITLE_SECONDS)
    for n in ep["chapters"]:
        c = by_n[n]
        name = c["ur"] if lang == "ur" else c["en"]
        chapters.append((t, f"{T['chapter']} {n}: {name}" if lang == "en" else f"{name}"))
        when = c.get("when") or ""
        note = NOTE.get(c["id"], ("", ""))[1 if lang == "ur" else 0]
        lines = [(f"{T['chapter']} {n}", 40, art.GOLD_PAPER), (name, 84, (250, 240, 214))]
        lines += [(when, 40, (226, 210, 180))] if when else []
        lines += [(note, 34, (226, 210, 180))] if note else []
        add(("map", c["id"]) if c["id"] in MAPS else ("night", n), ("title", lines), CARD_SECONDS)
        tag = f"{T['chapter']} {n} · {name}"
        for v in web.seerah_view(c):
            _, _, _, cid, l, kh = v[f"audio_{lang}"].split("/")
            audio = web.SEERAH_AUDIO / f"{cid}-{l}-{kh}"
            secs = duration(audio) + GAP
            text = v[lang]
            if v["kind"] == "ayah":
                ref = f"Quran {v['surah']}:{v['start']}" + (f"–{v['end']}" if v["end"] != v["start"] else "")
                sources.append(f"{ref} (Surah {v['surah_en']})")
                arabic = " ".join(f"{x['ar']} ﴿{x['n']}﴾" for x in v["verses"])
                pages = _pages(text, 70 if lang == "en" else 60)
                bodies = [(T["quran"], f"{ref} · Surah {v['surah_en']}", p, arabic if len(pages) == 1 and
                           len(arabic.split()) <= 45 else None) for p in pages]
            elif v["kind"] == "hadith":
                sources.append(f"{v['citation']} - {v['url']}")
                pages = _pages(text, 75 if lang == "en" else 65)
                bodies = [(T["hadith"], v["citation"] + (" (part of the narration)" if v.get("part") else ""), p, None)
                          for p in pages]
            else:
                pages = _pages(text, 34 if lang == "en" else 30)
                bodies = None
            words = [max(1, len(p.split())) for p in pages]
            if len(pages) > 1:                     # the real page turns are set below, from the narration itself
                groups.append({"units": list(range(len(units), len(units) + len(pages))), "audio": audio,
                               "pages": pages, "secs": secs, "words": words})
            for i, p in enumerate(pages):
                share = secs * words[i] / sum(words)
                if bodies:
                    bg, ov = ("paper", n * 10 + v["k"]), ("card", bodies[i], tag)
                else:
                    ph = photo_for(p, lang, used_photos)
                    bg = ("photo", ph) if ph else (scene_for(text, v["k"] + n), n * 10 + v["k"])
                    ov = ("say", p, tag, ph)
                add(bg, ov, share, audio if i == 0 else None, secs if i == 0 else None)
    add(("seal", 0), ("title", [(T["end1"], 46, (240, 226, 196)), (f"{SITE}/seerah", 64, (250, 240, 214)),
                                (T["sub"], 48, art.GOLD_PAPER), (T["sources"], 30, (210, 196, 170))]), END_SECONDS)
    page_turns(groups, units, lang)
    for key, idxs in used_photos.items():
        for i in sorted(set(idxs)):
            ph = PHOTOS[key]["photos"][i]
            sources.append(f"Photo: {ph['by']}, {ph['license']} - {ph['page']}")
    if any(u["bg"][0] == "map" for u in units):
        sources.append("Satellite image: NASA Blue Marble (public domain)")
    return units, chapters, sources


PHOTOS = json.loads((Path(__file__).with_name("photos.json")).read_text())
PHOTO_DIR = ROOT / "data" / "places"


def photo_for(text, lang, used):
    """A real photo of the place the narration names (each place's photos in turn), or None."""
    for key, ph in PHOTOS.items():
        if re.search(ph["match"], text, re.I):
            i = len(used.setdefault(key, [])) % len(ph["photos"])
            used[key].append(i)
            return (key, i)
    return None


def photo_image(key, i):
    import hashlib
    import urllib.request
    ph = PHOTOS[key]["photos"][i]
    f = PHOTO_DIR / (hashlib.md5(ph["url"].encode()).hexdigest()[:12] + ".jpg")
    if not f.exists():
        PHOTO_DIR.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(ph["url"], headers={"User-Agent": "QuranReelMaker/1.0 (https://quranreelmaker.xyz)"})
        f.write_bytes(urllib.request.urlopen(req, timeout=60).read())
    img = Image.open(f).convert("RGB")
    s = max(BW / img.width, BH / img.height)                    # cover the frame
    img = img.resize((int(img.width * s) + 1, int(img.height * s) + 1), Image.Resampling.LANCZOS)
    x, y = (img.width - BW) // 2, (img.height - BH) // 2
    img = img.crop((x, y, x + BW, y + BH))
    return Image.blend(img, Image.new("RGB", img.size, (12, 10, 8)), 0.12)


def photo_caption(img, key, i, lang):
    ph, place = PHOTOS[key]["photos"][i], PHOTOS[key]
    d = ImageDraw.Draw(img)
    f = font(UR if lang == "ur" else SERIF, 30 if lang == "ur" else 32)
    text = place["ur" if lang == "ur" else "en"]
    s = shape(text) if lang == "ur" else text
    kw = dict(direction="rtl", language="ur") if lang == "ur" and video.RAQM else {}
    tw = text_w(f, s, lang == "ur", "ur" if lang == "ur" else None)
    cf = font(SERIF, 22)
    credit = f"Photo: {ph['by']} ({ph['license']}), Wikimedia Commons"
    cw = text_w(cf, credit, False, None)
    d.rounded_rectangle([W - max(tw, cw) - 84, 30, W - 40, 30 + f.size * (2.0 if lang == "ur" else 1.5) + 34], 10,
                        fill=(14, 10, 8, 170))
    d.text((W - tw - 62, 36 if lang == "en" else 26), s, font=f, fill=(250, 240, 214), **kw)
    d.text((W - cw - 62, 36 + f.size * (2.0 if lang == "ur" else 1.5) - (10 if lang == "ur" else 4)), credit, font=cf,
           fill=(220, 210, 190))


PAGE_TIMES = Path(__file__).resolve().parent / "page_times.json"     # kept in git: Whisper runs once per block
OMNI_PYTHON = Path.home() / ".hayatus-voice" / "omni" / "bin" / "python"


def _key(g):
    import hashlib
    return f"{Path(g['audio']).name}|" + hashlib.md5("\n".join(g["pages"]).encode()).hexdigest()[:10]


def page_turns(groups, units, lang, log=print):
    """Each page of a long ayah/hadith/passage is shown from the moment its first words are spoken (Whisper),
    not by its share of the words: the voice says more than the screen shows (the salawat) and keeps its own pace.
    The block's total time does not change, so the episode's chapter times stay the same."""
    cache = json.loads(PAGE_TIMES.read_text()) if PAGE_TIMES.exists() else {}
    todo = [g for g in groups if _key(g) not in cache]
    if todo and OMNI_PYTHON.exists():
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            jobs = Path(tmp) / "jobs.json"
            jobs.write_text(json.dumps([{"key": _key(g), "audio": str(g["audio"]), "lang": lang, "pages": g["pages"]}
                                        for g in todo], ensure_ascii=False))
            log(f"Timing {len(todo)} page turns from the narration (Whisper)")
            subprocess.run([str(OMNI_PYTHON), str(Path(__file__).with_name("align.py")), str(jobs), str(Path(tmp) / "out.json")],
                           check=True)
            cache.update(json.loads((Path(tmp) / "out.json").read_text()))
        PAGE_TIMES.write_text(json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    elif todo:
        log(f"{len(todo)} blocks have no measured page turns (no Whisper here): their pages are timed by word count")
    for g in groups:
        heard = cache.get(_key(g))
        if not heard:
            continue
        n, secs, words = len(g["pages"]), g["secs"], g["words"]
        guess = [secs * sum(words[:i]) / sum(words) for i in range(n)]
        cuts = [0.0] + [h if h is not None else guess[i + 1] for i, h in enumerate(heard)] + [secs]
        if any(b - a < 1.0 for a, b in zip(cuts, cuts[1:])):          # a mismatch: keep the word-count timing
            continue
        for i, u in enumerate(g["units"]):
            units[u]["seconds"] = cuts[i + 1] - cuts[i]


def render_unit(u, i, work, lang):
    kind, seed = u["bg"]
    if kind == "map" and u["ov"][0] == "title":                 # the moving satellite map with the title
        from documentary import sat
        places, route = MAPS.get(seed, ([], None))
        nm = lambda k: PLACES[k][3 if lang == "ur" else 2]
        marks = [(PLACES[k][0], PLACES[k][1], nm(k), k in places) for k in PLACES]
        return sat.segment(work / f"seg-{i:04d}.mp4", u["seconds"], marks,
                           [PLACES[k][:2] for k in route] if route else None, u["ov"][1], lang, places)
    key = f"{kind}-{seed}"
    bg = work / f"bg-{key}.png"
    if not bg.exists():
        if kind == "photo":
            img = photo_image(*seed)
        else:
            img = map_image(seed, lang) if kind == "map" else background(kind, seed)
        img.convert("RGB").save(bg)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    o = u["ov"]
    if o[0] == "title":
        if kind == "map":                                   # the map stays readable: titles on the right
            ImageDraw.Draw(ov).rectangle([W * 0.52, 0, W, H], fill=(18, 14, 10, 210))
            ov.alpha_composite(title_overlay(o[1], lang, dark=False, x0=int(W * 0.52), width=int(W * 0.48)))
        else:
            ov = title_overlay(o[1], lang)
    elif o[0] == "card":
        head, ref, body, arabic = o[1]
        card(ov, head, ref, body, lang, arabic)
        label(ov, o[2], lang)
    else:
        strip(ov, o[1], lang)
        label(ov, o[2], lang)
        if len(o) > 3 and o[3]:
            photo_caption(ov, *o[3], lang)
    ovp = work / f"ov-{i:04d}.png"
    ov.save(ovp)
    d = u["seconds"]
    mp4 = work / f"seg-{i:04d}.mp4"
    pan = random.Random(i).choice(["(iw-ow)*t/{d}", "(iw-ow)*(1-t/{d})"]).format(d=d)
    vf = (f"[0:v]scale={BW}:{BH},crop={W}:{H}:x='{pan}':y='(ih-oh)/2',setsar=1[b];[b][1:v]overlay=0:0,"
          f"fade=t=in:st=0:d=0.35,fade=t=out:st={max(0, d - 0.35):.3f}:d=0.35,format=yuv420p[v]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-t", f"{d:.3f}", "-i", str(bg),
                    "-loop", "1", "-framerate", "30", "-t", f"{d:.3f}", "-i", str(ovp), "-filter_complex", vf, "-map", "[v]",
                    "-r", "30", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-t", f"{d:.3f}", str(mp4)], check=True)
    return mp4


def make(eid, lang="en", log=print, limit=None):
    units, chapters, sources = plan(eid, lang)
    if limit:
        units = units[:limit]
    OUT.mkdir(parents=True, exist_ok=True)
    work = OUT / f"work-{eid}-{lang}"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    log(f"{len(units)} segments, {sum(u['seconds'] for u in units) / 60:.1f} min")
    segs = []
    for i, u in enumerate(units):
        segs.append(render_unit(u, i, work, lang))
        if i % 20 == 0:
            log(f"  {i + 1}/{len(units)}")
    (work / "v.txt").write_text("".join(f"file '{s.name}'\n" for s in segs))
    # the sound: each block's narration at the start of its first page, silence (and a paper rustle at titles) elsewhere
    inputs, chains, t = [], [], 0.0
    rustle = ROOT / "qissa" / "rustle.wav"
    for u in units:
        src = u["audio"] or (rustle if u["ov"][0] == "title" and rustle.exists() else None)
        if src:
            inputs += ["-i", str(src)]
            k = len(inputs) // 2
            ms = int((t + (0.15 if u["audio"] else 0.4)) * 1000)
            vol = "" if u["audio"] else "volume=0.5,"
            chains.append(f"[{k}:a]{vol}aresample=44100,aformat=channel_layouts=stereo,adelay={ms}|{ms}[a{len(chains)}]")
        t += u["seconds"]
    mix = "".join(f"[a{i}]" for i in range(len(chains)))
    graph = ";".join(chains + [f"{mix}amix=inputs={len(chains)}:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=9,"
                               f"aresample=44100,apad,atrim=0:{t:.3f}[a]"])
    mp4 = OUT / f"{eid}-{lang}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(work / "v.txt"), *inputs,
                    "-filter_complex", graph, "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                    "-ar", "44100", "-movflags", "+faststart", "-t", f"{t:.3f}", str(mp4)], check=True)
    (OUT / f"{eid}-{lang}.txt").write_text(metadata(eid, lang, chapters, sources))
    shutil.rmtree(work, ignore_errors=True)
    log(f"made {mp4} ({t / 60:.1f} min)")
    return mp4


def metadata(eid, lang, chapters, sources):
    ep = EPISODES[eid]
    stamp = lambda s: f"{int(s // 60)}:{int(s % 60):02d}"
    if lang == "ur":
        title = f"{ep['ur']} | سیرت النبی ﷺ | دستاویزی"
        head = "سیرت النبی ﷺ: قرآن اور صحیح احادیث سے، لفظ بہ لفظ۔ کسی نبی، صحابی یا فرشتے کی تصویر نہیں بنائی گئی۔"
    else:
        title = f"{ep['en']} | The Seerah of Prophet Muhammad ﷺ | Documentary"
        head = ("The life of the Prophet ﷺ told from the Quran and sahih hadith, quoted word for word. "
                "No prophet, Companion or angel is shown: only the places, the land and the text.")
    lines = [head, "", "0:00 " + ep[lang]] + [f"{stamp(s)} {n}" for s, n in chapters] + [
        "", "Sources:"] + [f"• {s}" for s in dict.fromkeys(sources)] + [
        "", "The short linking passages are ours; everything the Prophet ﷺ said or did is quoted from the sources above.",
        "Narration: AI voices (English: Microsoft neural voice; Urdu: OmniVoice). Photos of the places as they are today.",
        f"Read and listen to the whole Seerah: https://{SITE}/seerah", "",
        "#Seerah #ProphetMuhammad #IslamicHistory #Documentary #Islam"]
    return json.dumps({"title": title[:100], "description": "\n".join(lines)[:4900]}, ensure_ascii=False, indent=1)
