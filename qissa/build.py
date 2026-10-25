"""Turns a story script (qissa/stories/<id>.json) into a vertical video, in English or Hinglish.

Every ayah and hadith on screen comes from the verified data (Quran text from Quran.com, translations from the
site's sources, hadith from Sahih al-Bukhari / Muslim checked against sunnah.com); the script only names
references, so nothing quoted can be mistyped or invented."""
import asyncio
import json
import random
import re
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

import video
from video import font, shape, text_w, wrap
from qissa import art

ROOT = Path(__file__).resolve().parent.parent
STORIES = Path(__file__).resolve().parent / "stories"
W, H = art.W, art.H
HEAD, MONO, AR, SERIF, UR = "Anton-Regular.ttf", "CourierPrime-Bold.ttf", "Amiri-Regular.ttf", "Amiri-Regular.ttf", "NotoNastaliqUrdu.ttf"
CREAM, INK, RED, GOLD, WHITE = (236, 226, 204), (40, 34, 28), (186, 40, 36), (212, 175, 95), (246, 242, 232)
VOICES = {"en": ("en-US-AndrewMultilingualNeural", "-6%"), "hi": ("hi-IN-MadhurNeural", "-4%")}
TR = {"en": "en", "hi": "ur-roman"}          # the translation shown on Hinglish cards: Roman Urdu
CLEAR = ("highpass=f=70,lowpass=f=11000,equalizer=f=180:t=q:w=1:g=-2,equalizer=f=3200:t=q:w=1.2:g=3,"
         "acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120:makeup=2,loudnorm=I=-14:TP=-1.5:LRA=9")


class StoryError(Exception):
    pass


def load(story_id):
    f = STORIES / f"{story_id}.json"
    if not f.exists():
        raise StoryError(f"no story {f}")
    return json.loads(f.read_text(encoding="utf-8"))


# ---- verified sources ----
_Q = {}


def quran():
    if not _Q:
        from quran_data import load_quran, surah_ranges
        _Q["q"] = load_quran()
        _Q["r"] = surah_ranges(_Q["q"])
    return _Q["q"], _Q["r"]


def ayah_card(ref, lang, part=None):
    """Arabic, translation and reference for 's:a' or 's:a-b', straight from the data."""
    from translations import texts
    from seo import BY_NUMBER
    q, r = quran()
    m = re.fullmatch(r"(\d+):(\d+)(?:-(\d+))?", ref)
    if not m:
        raise StoryError(f"bad ayah reference {ref!r}")
    s, a, b = int(m.group(1)), int(m.group(2)), int(m.group(3) or m.group(2))
    if s not in r or not 1 <= a <= b <= r[s][1] - r[s][0]:
        raise StoryError(f"ayah {ref} does not exist")
    rows = q[r[s][0] + a - 1:r[s][0] + b]
    tr = texts(TR[lang], q, log=lambda m: None)
    arabic = " ".join(x["ar"] for x in rows)
    meaning = " ".join(tr[x["n"] - 1] for x in rows)
    if part == "dua":                                   # the quoted words inside the ayah
        words = arabic.split()
        norm = lambda w: re.sub("[أإآٱ]", "ا", re.sub("[\u064B-\u065F\u0670\u06D6-\u06ED\u0640]", "", w))
        plain = [norm(w) for w in words]
        i = next((k for k, w in enumerate(plain) if w == "لا" and k + 1 < len(plain) and plain[k + 1] == "اله"), None)
        if i is None:
            raise StoryError(f"{ref}: no quoted dua found")
        arabic = " ".join(words[i:])
        qm = re.search(r'["“]([^"”]+)["”]', meaning)
        meaning = qm.group(1) if qm else meaning
    elif part == "start":
        arabic = " ".join(arabic.split()[:9]) + " …"
        meaning = " ".join(meaning.split()[:16]) + " …"
    name = BY_NUMBER[s]["englishName"]
    return {"arabic": arabic, "meaning": meaning, "ref": f"{name.upper()} · {s}:{a}" + (f"-{b}" if b != a else "")}


def hadith_card(ref, lang, verify=True):
    from hadith_shorts import source
    h = source.get(ref)
    if verify:
        ok, detail = source.verify(h)
        if not ok:
            raise StoryError(f"{ref} failed the sunnah.com check: {detail}")
    quote = re.search(r'"([^"]+)', h.english)
    meaning = (h.urdu or h.english) if lang == "hi" and False else (quote.group(1).strip() if quote else h.english)
    return {"arabic": h.arabic, "meaning": meaning, "ref": h.citation.upper(), "url": h.url}


def check(story, verify=True):
    """Problems with a story script (empty = ready): languages, art, references, and that every source exists."""
    problems = []
    for k in ("id", "title", "scenes"):
        if k not in story:
            problems.append(f"missing {k}")
    for i, sc in enumerate(story.get("scenes", []), 1):
        for lang in ("en", "hi"):
            if not sc.get("say", {}).get(lang):
                problems.append(f"scene {i}: no {lang} narration")
            if not sc.get("heading", {}).get(lang):
                problems.append(f"scene {i}: no {lang} heading")
        if sc.get("art") not in art.ARTS:
            problems.append(f"scene {i}: art {sc.get('art')!r} is not one of {', '.join(art.ARTS)}")
        card = sc.get("card") or {}
        try:
            if "ayah" in card:
                ayah_card(card["ayah"], "en", card.get("part"))
            if "hadith" in card:
                hadith_card(card["hadith"], "en", verify)
        except Exception as e:
            problems.append(f"scene {i}: {e}")
        if "fact" in card and not card.get("ref"):
            problems.append(f"scene {i}: a fact card needs its source (ref)")
    return problems


# ---- drawing ----
def _text(d, xy, s, f, fill, rtl=False, lang="ar"):
    d.text(xy, shape(s) if rtl else s, font=f, fill=fill, **(dict(direction="rtl", language=lang) if rtl and video.RAQM else {}))


def heading(d, text, y, size=96):
    """Big condensed capitals; *words* in red. Lines split at '|'."""
    for line in [l.strip() for l in text.split("|")]:
        accent = line.startswith("*") and line.endswith("*")
        line = line.strip("*")
        f = font(HEAD, size)
        while text_w(f, line, False) > W - 120 and f.size > 48:
            f = font(HEAD, f.size - 4)
        x = 60
        for k, piece in enumerate(line.split("ﷺ")):        # the heading font has no ﷺ: draw it in Amiri
            if k:
                fa = font(AR, int(f.size * 0.9))
                d.text((x + 6, y + f.size * 0.08), "ﷺ", font=fa, fill=GOLD)
                x += text_w(fa, "ﷺ", False) + 12
            d.text((x, y), piece, font=f, fill=RED if accent else WHITE)
            x += text_w(f, piece, False)
        y += int(f.size * 1.08)
    return y


def label(img, text, y=170):
    d = ImageDraw.Draw(img)
    f = font(MONO, 30)
    w = text_w(f, text, False)
    rnd = random.Random(text)
    tag = Image.new("RGBA", (int(w + 36), 52), (0, 0, 0, 0))
    td = ImageDraw.Draw(tag)
    td.polygon([(2, 3), (w + 33, 0), (w + 35, 49), (0, 51)], fill=CREAM + (255,))
    td.text((18, 10), text, font=f, fill=INK)
    tag = tag.rotate(rnd.uniform(-2, 2), expand=True, resample=Image.BICUBIC)
    img.alpha_composite(tag, (56, y))


def card(img, c, lang, y):
    """A torn cream paper card with the Arabic, its meaning and the reference (or a fact)."""
    rnd = random.Random(str(c))
    cw, pad = W - 150, 46
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    inner = cw - 2 * pad
    blocks = []
    if "fact" in c:
        blocks.append(("fact", c["fact"]))
        blocks.append(("mono", c["fact_label"][lang]))
    else:
        f_ar = font(AR, 58)
        lines = wrap(c["arabic"], f_ar, inner, True, "ar")
        while len(lines) > 4 and f_ar.size > 36:
            f_ar = font(AR, f_ar.size - 4)
            lines = wrap(c["arabic"], f_ar, inner, True, "ar")
        blocks.append(("ar", (f_ar, lines)))
        f_m = font(SERIF, 34)
        mlines = wrap(c["meaning"], f_m, inner, False, None)[:5]
        blocks.append(("meaning", (f_m, mlines)))
    blocks.append(("ref", c["ref"]))
    hgt = pad
    for kind, val in blocks:
        hgt += {"fact": 190, "mono": 50, "ref": 60}.get(kind, 0)
        if kind == "ar":
            hgt += len(val[1]) * int(val[0].size * 1.8) + 10
        if kind == "meaning":
            hgt += len(val[1]) * 46 + 16
    hgt += pad
    x0 = (W - cw) // 2
    poly = []
    for t in range(0, cw, 22):
        poly.append((x0 + t, y + rnd.uniform(-5, 5)))
    for t in range(0, hgt, 22):
        poly.append((x0 + cw + rnd.uniform(-5, 5), y + t))
    for t in range(cw, 0, -22):
        poly.append((x0 + t, y + hgt + rnd.uniform(-6, 6)))
    for t in range(hgt, 0, -22):
        poly.append((x0 + rnd.uniform(-5, 5), y + t))
    sh = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sh).polygon([(px + 8, py + 16) for px, py in poly], fill=150)
    layer.paste((0, 0, 0, 255), (0, 0), sh.filter(ImageFilter.GaussianBlur(18)))
    paper = art._paper(W, H, CREAM, (222, 208, 180), 0.2).convert("RGBA")
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).polygon(poly, fill=255)
    layer.paste(paper, (0, 0), m)
    d = ImageDraw.Draw(layer)
    yy = y + pad
    for kind, val in blocks:
        if kind == "fact":
            f = font(HEAD, 170)
            d.text(((W - text_w(f, val, False)) / 2, yy), val, font=f, fill=INK)
            yy += 190
        elif kind == "mono":
            f = font(MONO, 32)
            d.text(((W - text_w(f, val, False)) / 2, yy), val, font=f, fill=INK)
            yy += 50
        elif kind == "ar":
            f, lines = val
            for ln in lines:
                _text(d, ((W - text_w(f, shape(ln), True, "ar")) / 2, yy), ln, f, INK, True)
                yy += int(f.size * 1.8)
            yy += 10
        elif kind == "meaning":
            f, lines = val
            for ln in lines:
                d.text(((W - text_w(f, ln, False)) / 2, yy), ln, font=f, fill=(70, 62, 52))
                yy += 46
            yy += 16
        elif kind == "ref":
            f = font(MONO, 26)
            d.text(((W - text_w(f, val, False)) / 2, yy + 10), val, font=f, fill=RED)
            yy += 60
    layer = layer.rotate(rnd.uniform(-1.2, 1.2), center=(W / 2, y + hgt / 2), resample=Image.BICUBIC)
    img.alpha_composite(layer)
    return y + hgt


def overlay(scene, lang, story, path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if scene.get("label"):
        label(img, scene["label"][lang])
    y = heading(ImageDraw.Draw(img), scene["heading"][lang], 250)
    c = scene.get("card")
    if c:
        if "ayah" in c:
            data = ayah_card(c["ayah"], lang, c.get("part"))
        elif "hadith" in c:
            data = hadith_card(c["hadith"], lang, verify=False)
        else:
            data = {"fact": c["fact"], "fact_label": c["fact_label"], "ref": c["ref"].upper()}
        card(img, data, lang, max(y + 70, 760))
    d = ImageDraw.Draw(img)
    f = font(MONO, 24)
    tag = f"QISSA #{story.get('number', 0):03d} · quranreelmaker.xyz"
    d.text((W - 60 - text_w(f, tag, False), H - 110), tag, font=f, fill=(225, 215, 195))
    video.shadowed(img).save(path)


# ---- narration ----
def speak(text, out, lang):
    import edge_tts
    voice, rate = VOICES[lang]
    asyncio.run(edge_tts.Communicate(text, voice, rate=rate).save(str(out)))
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


# ---- video ----
def make(story_id, lang, out_dir, log=print):
    story = load(story_id)
    problems = check(story)
    if problems:
        raise StoryError("script problems:\n  " + "\n  ".join(problems))
    out_dir = Path(out_dir)
    work = out_dir / f"work_{story_id}_{lang}"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    parts = []
    for i, sc in enumerate(story["scenes"]):
        log(f"Scene {i + 1}/{len(story['scenes'])}: {sc['art']}")
        voice = work / f"v{i}.mp3"
        secs = speak(sc["say"][lang], voice, lang) + 0.9
        bg = work / f"bg{i}.png"
        art.draw(sc["art"], seed=i).save(bg)
        ov = work / f"ov{i}.png"
        overlay(sc, lang, story, ov)
        seg = work / f"s{i}.mp4"
        move = ["(iw-%d)*t/%f" % (W, secs), "(ih-%d)/2" % H] if i % 2 else ["(iw-%d)/2" % W, "(ih-%d)*(1-t/%f)" % (H, secs)]
        graph = (f"[0:v]crop={W}:{H}:x='{move[0]}':y='{move[1]}',setsar=1,fps=30[bg];"
                 f"[1:v]format=rgba,fade=t=in:st=0.15:d=0.45:alpha=1[ov];[bg][ov]overlay=0:0,"
                 f"fade=t=in:st=0:d=0.25,format=yuv420p[v];"
                 f"[2:a]adelay=350|350,apad,atrim=0:{secs:.3f}[a]")
        r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(bg), "-loop", "1", "-i", str(ov),
                            "-i", str(voice), "-filter_complex", graph, "-map", "[v]", "-map", "[a]", "-t", f"{secs:.3f}",
                            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "160k",
                            "-ar", "44100", str(seg)], capture_output=True, text=True)
        if r.returncode:
            raise StoryError(f"scene {i + 1}: ffmpeg failed: {r.stderr[-500:]}")
        parts.append(seg)
    lst = work / "parts.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in parts))
    mp4 = out_dir / f"{story_id}_{lang}.mp4"
    log("Joining scenes")
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-c:v", "copy", "-af", CLEAR, "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(mp4)],
                       capture_output=True, text=True)
    if r.returncode:
        raise StoryError(f"join failed: {r.stderr[-500:]}")
    shutil.rmtree(work, ignore_errors=True)
    return mp4
