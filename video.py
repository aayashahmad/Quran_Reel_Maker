import os
import re
import subprocess
import unicodedata
import wave
from functools import lru_cache

import requests
from PIL import Image, ImageDraw, ImageFont, features

from config import FONTS, W, H, FPS, CHANNEL_TAG, INTRO_SECONDS
from translations import LANGS, NO_SPACES

_GF = "https://github.com/google/fonts/raw/main/ofl/"
FONT_URLS = {
    "Amiri-Regular.ttf": _GF + "amiri/Amiri-Regular.ttf",
    "AmiriQuran-Regular.ttf": _GF + "amiriquran/AmiriQuran-Regular.ttf",
    "NotoNastaliqUrdu.ttf": _GF + "notonastaliqurdu/NotoNastaliqUrdu%5Bwght%5D.ttf",
}
BASE_FONTS = tuple(FONT_URLS)     # always needed; translation fonts below are fetched when a language uses them
FONT_URLS.update({
    "NotoSans.ttf": _GF + "notosans/NotoSans%5Bwdth,wght%5D.ttf",
    "NotoNaskhArabic.ttf": _GF + "notonaskharabic/NotoNaskhArabic%5Bwght%5D.ttf",
    "NotoSansThaana.ttf": _GF + "notosansthaana/NotoSansThaana%5Bwght%5D.ttf",
    "NotoSansSC.ttf": _GF + "notosanssc/NotoSansSC%5Bwght%5D.ttf",
    "NotoSansJP.ttf": _GF + "notosansjp/NotoSansJP%5Bwght%5D.ttf",
    "NotoSansKR.ttf": _GF + "notosanskr/NotoSansKR%5Bwght%5D.ttf",
    **{f"NotoSans{n}.ttf": _GF + f"notosans{n.lower()}/NotoSans{n}%5Bwdth,wght%5D.ttf"
       for n in ("Devanagari", "Bengali", "Tamil", "Malayalam", "Thai", "Sinhala", "Myanmar", "Ethiopic")},
})
# Translation text per font: (size, smallest size, line height, highlight band top as a share of size)
TR_STYLE = {"NotoNastaliqUrdu.ttf": (52, 28, 2.0, 0.15), "NotoNaskhArabic.ttf": (50, 28, 1.85, 0.2)}
TR_STYLE_DEFAULT = (50, 26, 1.6, 0.0)

RAQM = features.check("raqm")
if not RAQM:
    import arabic_reshaper
    from bidi.algorithm import get_display

GOLD = (212, 175, 95)
WHITE = (245, 245, 240)
SOFT = (200, 215, 205)
MUTED = (140, 170, 155)
DIM = (150, 175, 165)
HL_BG = (92, 74, 28)              # box behind the word being recited
AR_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def ayah_end(n):
    """End-of-ayah ornament with Arabic-Indic number, as printed in the mushaf."""
    return "\u06DD" + str(n).translate(AR_DIGITS)


def ensure_fonts(names=BASE_FONTS):
    FONTS.mkdir(exist_ok=True)
    for name in names:
        p = FONTS / name
        if not p.exists():
            r = requests.get(FONT_URLS[name], timeout=300)
            r.raise_for_status()
            p.write_bytes(r.content)


FALLBACK_FONTS = ("NotoSans.ttf", "NotoNaskhArabic.ttf")    # Latin/Cyrillic and Arabic letters


def tr_lang(code=None):
    """Settings of a translation language (Urdu when code is None), with its fonts downloaded."""
    code = code or "ur"
    lang = dict(LANGS[code], code=code)
    lang["shape"] = lang["shape"] or code       # language tag for text shaping
    ensure_fonts(BASE_FONTS + (lang["font"],) + FALLBACK_FONTS)
    return lang


@lru_cache(maxsize=None)
def _letters_in(name):
    from fontTools.ttLib import TTFont
    return set(TTFont(str(FONTS / name), lazy=True).getBestCmap())


def font_for(text, name):
    """`name`, or a fallback font when `name` lacks some of the letters in `text`
    (e.g. an Arabic word inside the Dhivehi translation)."""
    need = {ord(c) for c in text if not c.isspace() and unicodedata.category(c) != "Cf"}
    for n in (name,) + FALLBACK_FONTS:
        if (FONTS / n).exists() and need <= _letters_in(n):
            return n
    return name


def font(name, size):
    engine = ImageFont.Layout.RAQM if RAQM else ImageFont.Layout.BASIC
    return ImageFont.truetype(str(FONTS / name), size, layout_engine=engine)


def shape(text):
    return text if RAQM else get_display(arabic_reshaper.reshape(text))


def text_w(f, s, rtl=True, lang="ar"):
    if RAQM:
        return f.getlength(s, direction="rtl" if rtl else "ltr", language=lang if rtl else None)
    return f.getlength(s)


def _letters(word):
    """Split a word into letters, keeping combining marks (vowel signs etc.) with their letter."""
    out = []
    for ch in word:
        if out and unicodedata.category(ch).startswith("M"):
            out[-1] += ch
        else:
            out.append(ch)
    return out


def wrap(text, f, max_w, rtl, lang):
    def fits(t):
        return text_w(f, shape(t) if rtl else t, rtl, lang) <= max_w

    pieces = []                         # (text, joined to the previous piece without a space)
    for word in text.split():
        if fits(word):
            pieces.append((word, False))
            continue
        chunk, first = "", True         # too wide for one line (e.g. Chinese): break between letters
        for ch in _letters(word):
            if chunk and not fits(chunk + ch):
                pieces.append((chunk, not first))
                chunk, first = "", False
            chunk += ch
        pieces.append((chunk, not first))
    lines, cur = [], ""
    for word, glued in pieces:
        t = (cur + ("" if glued else " ") + word).strip()
        if fits(t) or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_block(d, text, fname, y, max_h, size, min_size, color, lh, rtl=True, lang="ar", width=W):
    """Auto-shrinks font to fit box; returns y after the block."""
    max_w = width - 140
    while True:
        f = font(fname, size)
        lines = wrap(text, f, max_w, rtl, lang)
        line_h = int(size * lh)
        if len(lines) * line_h <= max_h or size <= min_size:
            break
        size -= 4
    for ln in lines:
        s = shape(ln) if rtl else ln
        w = text_w(f, s, rtl, lang)
        kw = {}
        if RAQM:
            kw = dict(direction="rtl", language=lang) if rtl else {}
        d.text(((width - w) / 2, y), s, font=f, fill=color, **kw)
        y += line_h
    return y


def draw_words(d, tokens, y, max_h, size, min_size, lh, color, hl=None, fname="AmiriQuran-Regular.ttf", lang="ar",
               rtl=True, band=0.55):
    """Draw words one by one (right-to-left, or left-to-right), so a single word can be highlighted.
    tokens: list of (text, index); the token whose index == hl gets a gold box.
    The layout depends only on the tokens, so every highlight state lines up exactly."""
    max_w = W - 140
    names = {text: fname if fname == "AmiriQuran-Regular.ttf" else font_for(text, fname) for text, _ in tokens}
    while True:
        f = font(fname, size)
        fonts = {n: font(n, size) for n in set(names.values())}
        space = text_w(f, " ", rtl, lang)
        if lang == "ur":                        # Nastaliq spaces are narrow; leave room for the highlight box
            space = max(space, size * 0.45)
        lines, cur, cur_w = [], [], 0.0
        for text, idx in tokens:
            ww = text_w(fonts[names[text]], shape(text) if rtl else text, rtl, lang)
            if cur and cur_w + space + ww > max_w:
                lines.append((cur, cur_w))
                cur, cur_w = [], 0.0
            cur_w += (space if cur else 0) + ww
            cur.append((text, idx, ww))
        if cur:
            lines.append((cur, cur_w))
        line_h = int(size * lh)
        if len(lines) * line_h <= max_h or size <= min_size:
            break
        size -= 4
    kw = dict(direction="rtl" if rtl else "ltr", language=lang) if RAQM else {}
    pad = min(12, space * 0.45)             # highlight box margin, never reaching the next word
    for words, line_w in lines:
        # Highlight box height = real ink extent of this line (harakat above and below included)
        boxes = [fonts[names[t]].getbbox(shape(t) if rtl else t, **kw) for t, _, _ in words]
        top, bottom = min(bx[1] for bx in boxes) - 8, max(bx[3] for bx in boxes) + 8
        top0 = size * band                  # lines repeat every line_h; keep the box in this line's band
        top, bottom = max(top, top0), min(bottom, top0 + line_h)
        x = (W + line_w) / 2 if rtl else (W - line_w) / 2     # where the centred line starts
        for text, idx, ww in words:
            if rtl:
                x -= ww
            hit = hl is not None and idx == hl
            if hit:
                d.rounded_rectangle([x - pad, y + top, x + ww + pad, y + bottom], radius=14, fill=HL_BG)
            d.text((x, y), shape(text) if rtl else text, font=fonts[names[text]], fill=GOLD if hit else color, **kw)
            x += -space if rtl else ww + space
        y += line_h
    return y


def center(d, text, size, y, color, width=W):
    f = font("Amiri-Regular.ttf", size)
    w = text_w(f, text, rtl=False)
    d.text(((width - w) / 2, y), text, font=f, fill=color)


@lru_cache(maxsize=4)
def _gradient(w, h):
    top, bot = (11, 61, 46), (3, 20, 15)
    g = Image.new("RGB", (1, 256))
    for y in range(256):
        t = y / 255
        g.putpixel((0, y), tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))
    return g.resize((w, h), Image.BILINEAR)


def background(w=W, h=H):
    return _gradient(w, h).copy()


def make_frame(item, path, hl=None, tr=None, tr_hl=None, lang=None):
    """item may be a real ayah, or the Bismillah frame (item["is_bismillah"]).
    hl: index of the Arabic word being recited (highlighted), or None.
    tr: None = translation not read aloud; False = Arabic is playing (translation dimmed);
        True = the translation is being read. tr_hl: index of its word being read, or None.
    lang: from tr_lang(); the translation shown is item["tr"] (Urdu item["ur"] by default)."""
    lang = lang or tr_lang()
    img = background()
    d = ImageDraw.Draw(img)
    bism = item.get("is_bismillah")

    # header
    ref = "Bismillah" if bism else f"{item['surah']}:{item['ayah']}"
    center(d, f"Surah {item['surah_en']}  •  {ref}", 56, 110, GOLD)
    draw_block(d, item["surah_ar"], "Amiri-Regular.ttf", 190, 140, 80, 50, GOLD, 1.5)
    d.line([(240, 330), (W - 240, 330)], fill=GOLD, width=3)

    # arabic ayah
    words = item.get("words") or item["ar"].split()
    tokens = [(w, i) for i, w in enumerate(words)]
    if not bism:
        tokens.append((ayah_end(item["ayah"]), None))
    y = draw_words(d, tokens, 380, 640, 78, 34, 1.9, DIM if tr else WHITE, hl)
    if item.get("sajda"):
        note = "آیتِ سجدہ" + (" (عند الشافعی)" if (item["surah"], item["ayah"]) == (22, 77) else "")
        y = draw_block(d, note, "NotoNastaliqUrdu.ttf", y, 110, 40, 30, GOLD, 2.2, lang="ur")

    # translation
    y = max(y + 40, 1060)
    d.line([(400, y - 20), (W - 400, y - 20)], fill=(90, 130, 110), width=2)
    color = SOFT if tr is None else (WHITE if tr else DIM)
    text = item.get("tr", item["ur"])
    size, min_size, lh, band = TR_STYLE.get(lang["font"], TR_STYLE_DEFAULT)
    if lang["code"] in NO_SPACES:
        draw_block(d, text, lang["font"], y + 10, H - y - 260, size, min_size, color, lh,
                   rtl=lang["rtl"], lang=lang["shape"])
    else:
        draw_words(d, [(w, i) for i, w in enumerate(text.split())], y + 10, H - y - 260, size, min_size, lh,
                   color, tr_hl, fname=lang["font"], lang=lang["shape"], rtl=lang["rtl"], band=band)

    if CHANNEL_TAG:
        center(d, CHANNEL_TAG, 38, H - 150, MUTED)
    img.save(path)


def card(info, w, h, lang=None):
    """Title card: used as the reel's first frame (vertical) and as the YouTube thumbnail (landscape)."""
    lang = lang or tr_lang()
    img = background(w, h)
    d = ImageDraw.Draw(img)
    d.rectangle([24, 24, w - 25, h - 25], outline=GOLD, width=4)

    def with_translation(y, size):
        if lang["code"] == "ur":
            draw_block(d, "قرآن پاک اردو ترجمہ کے ساتھ", "NotoNastaliqUrdu.ttf", y, size * 3, size, size * 5 // 8,
                       SOFT, 2.0, lang="ur", width=w)
            return
        center(d, f"With {lang['name']} translation", size * 7 // 8, y + size // 4, SOFT, w)
        if lang["native"] != lang["name"]:
            draw_block(d, lang["native"], lang["font"], y + size * 3 // 2, size * 2, size * 3 // 4, size // 2,
                       MUTED, 1.6, rtl=lang["rtl"], lang=lang["shape"], width=w)

    if h > w:   # vertical 9:16
        center(d, f"Surah {info['surah']}", 60, 380, MUTED, w)
        draw_block(d, info["surah_ar"], "Amiri-Regular.ttf", 480, 330, 190, 90, GOLD, 1.6, width=w)
        center(d, f"Surah {info['surah_en']}", 88, 860, WHITE, w)
        center(d, info["label"], 66, 990, GOLD, w)
        if info["part_label"]:
            center(d, info["part_label"], 60, 1080, SOFT, w)
        with_translation(1260, 64)
        if CHANNEL_TAG:
            center(d, CHANNEL_TAG, 42, h - 170, MUTED, w)
    else:       # landscape 16:9 thumbnail
        draw_block(d, info["surah_ar"], "Amiri-Regular.ttf", 50, 270, 170, 80, GOLD, 1.5, width=w)
        center(d, f"Surah {info['surah_en']}", 72, 330, WHITE, w)
        sub = info["label"] + (f"  •  {info['part_label']}" if info["part_label"] else "")
        center(d, sub, 54, 435, GOLD, w)
        with_translation(530, 48)
    return img


def make_thumbnail(info, path, lang=None):
    card(info, 1280, 720, lang).save(path, "JPEG", quality=90)
    return path


def _wav(src, dst):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
                    "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(dst)], check=True)
    with wave.open(str(dst)) as w:
        return w.getnframes() / w.getframerate()


def word_timeline(segments, nwords, dur):
    """[(seconds, word index or None)] that exactly covers `dur` seconds of Arabic audio.
    Short pauses between words keep the previous word lit so it doesn't flicker."""
    out, t = [], 0.0
    for pos, start, end in sorted(segments, key=lambda s: s[1]):
        if not 1 <= pos <= nwords:
            continue
        s, e = max(start / 1000, t), min(end / 1000, dur)
        if e <= s:
            continue
        if s > t:
            if out and out[-1][1] is not None and s - t < 0.35:
                out[-1] = (out[-1][0] + s - t, out[-1][1])
            else:
                out.append((s - t, None))
        out.append((e - s, pos - 1))
        t = e
    if dur > t:
        out.append((dur - t, None))
    merged = []
    for sec, w in out:
        if merged and merged[-1][1] == w:
            merged[-1] = (merged[-1][0] + sec, w)
        else:
            merged.append((sec, w))
    return merged


def _voiced(wav, dur):
    """[(start, end)] of the parts of this audio that are not silence."""
    log = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(wav), "-af", "silencedetect=noise=-35dB:d=0.25",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    out, t, kind = [], 0.0, "end"
    for kind, sec in re.findall(r"silence_(start|end): ([\d.]+)", log):
        sec = min(float(sec), dur)
        if kind == "start" and sec > t:
            out.append((t, sec))
        t = sec
    if kind == "end" and dur > t:               # the file doesn't end in silence
        out.append((t, dur))
    return [(a, b) for a, b in out if b - a > 0.05] or [(0.0, dur)]


def tr_timeline(wav, nwords_text, dur):
    """[(seconds, word index or None)] covering `dur` seconds of translation audio.
    Estimated: the speaking time (pauses skipped) is shared by the words in proportion
    to their length, since there are no word timings for the translation readings."""
    weights = [max(1, len(re.sub(r"[^\w]", "", w))) + 1 for w in nwords_text]
    voiced = _voiced(wav, dur)
    total = sum(b - a for a, b in voiced)

    def real(x):                                # speaking-time offset -> time in the file
        for a, b in voiced:
            if x <= b - a:
                return a + x
            x -= b - a
        return voiced[-1][1]

    out, t, acc = [], 0.0, 0.0
    for i, w in enumerate(weights):
        s, acc = real(acc / sum(weights) * total), acc + w
        e = real(acc / sum(weights) * total)
        if s > t:                               # pause: before the first word nothing is lit,
            out.append((s - t, i - 1 if i else None))   # later the previous word stays lit
        out.append((e - s, i))
        t = e
    if dur > t:
        out.append((dur - t, len(weights) - 1 if weights else None))
    merged = []
    for sec, w in out:
        if merged and merged[-1][1] == w:
            merged[-1] = (merged[-1][0] + sec, w)
        elif sec > 0:
            merged.append((sec, w))
    return merged


# Small hosts (e.g. 512 MB): set FFMPEG_THREADS=1 so x264 doesn't size its buffers for every host core.
_THREADS = os.getenv("FFMPEG_THREADS")
LOW_MEM_X264 = ["-threads", _THREADS, "-x264-params", "rc-lookahead=5"] if _THREADS else []


def render(items, audio_lists, info, out_path, workdir, log=print, lang=None):
    """One frame per ayah, timed to its audio. audio_lists[i] = files played in order
    for ayah i (Arabic, then the translation). A title card is shown first. Returns total seconds.
    lang: translation language code (Urdu by default); items carry its text in "tr"."""
    lang = tr_lang(lang)
    workdir.mkdir(parents=True, exist_ok=True)

    frames, wavs = [], []
    if INTRO_SECONDS > 0:
        fp = workdir / "intro.png"
        card(info, W, H, lang).save(fp)
        sil = workdir / "intro.wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                        "-i", "anullsrc=r=44100:cl=stereo", "-t", str(INTRO_SECONDS),
                        "-c:a", "pcm_s16le", str(sil)], check=True)
        frames.append((fp, INTRO_SECONDS))
        wavs.append(sil)

    for i, (it, files) in enumerate(zip(items, audio_lists)):
        log(f"Rendering ayah {i + 1}/{len(items)}")
        durs = []
        for j, f in enumerate(files):
            wv = workdir / f"a{i}_{j}.wav"
            durs.append(_wav(f, wv))
            wavs.append(wv)
        read = len(files) > 1                   # the translation is read aloud after the Arabic
        words = it.get("words") or []
        states = word_timeline(it.get("segments") or [], len(words), durs[0])
        if read:
            if lang["code"] in NO_SPACES:       # no word boundaries: the whole translation is lit
                states.append((durs[1], ("tr", None)))
            else:
                tl = tr_timeline(workdir / f"a{i}_1.wav", it.get("tr", it["ur"]).split(), durs[1])
                states += [(sec, ("tr", w)) for sec, w in tl]
            if len(durs) > 2:
                states.append((sum(durs[2:]), ("tr", None)))
        drawn = {}
        for sec, st in states:
            if st not in drawn:
                fp = workdir / f"f{i}_{len(drawn)}.png"
                if isinstance(st, tuple):
                    make_frame(it, fp, tr=True, tr_hl=st[1], lang=lang)
                else:
                    make_frame(it, fp, hl=st, tr=False if read else None, lang=lang)
                drawn[st] = fp
            frames.append((drawn[st], sec))

    fl = []
    for fp, dur in frames:
        fl += [f"file '{fp.resolve()}'", f"duration {dur:.3f}"]
    fl.append(f"file '{frames[-1][0].resolve()}'")  # concat quirk
    lst = workdir / "frames.txt"
    alst = workdir / "audio.txt"
    lst.write_text("\n".join(fl))
    alst.write_text("\n".join(f"file '{w.resolve()}'" for w in wavs))

    total = sum(d for _, d in frames)
    log("Encoding video 0%")
    proc = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error", "-nostats", "-progress", "pipe:1",
        "-f", "concat", "-safe", "0", "-i", str(lst),
        "-f", "concat", "-safe", "0", "-i", str(alst),
        "-vf", f"fps={FPS},format=yuv420p",
        "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage", "-crf", "20",
        *LOW_MEM_X264,
        "-c:a", "aac", "-b:a", "160k", "-t", f"{total:.3f}",   # exact length; -shortest overshoots
        "-movflags", "+faststart", str(out_path)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    for line in proc.stdout:
        if line.startswith("out_time_us=") and line.strip()[12:].isdigit():
            pct = min(99, int(int(line.strip()[12:]) / 1e6 / total * 100))
            log(f"Encoding video {pct}%")
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg failed: " + proc.stderr.read().strip()[-300:])
    return total


STORY_LABELS = {
    "roman": ("Aaj ka kaam:", "Reflection, tafsir nahi"),
    "urdu": ("آج کا کام:", "یہ غور و فکر ہے، تفسیر نہیں"),
    "english": ("Today:", "A reflection, not tafsir"),
}


def make_story(items, info, data, path, language="roman"):
    """1080x1920 status/story image: ayat + Urdu translation + modern reflection."""
    ensure_fonts()
    urdu = language == "urdu"
    body_font = "NotoNastaliqUrdu.ttf" if urdu else "Amiri-Regular.ttf"
    label, note = STORY_LABELS.get(language, STORY_LABELS["roman"])
    ar = " ".join(f"{x['ar']} {ayah_end(x['ayah'])}" for x in items)
    ur = " ".join(f"{x['ur']} ({x['ayah']})" for x in items)

    def content(d, y):
        def text(t, y, max_h, size, min_size, color, lh):
            return draw_block(d, t, body_font, y, max_h, size, min_size, color,
                              2.0 if urdu else lh, rtl=urdu, lang="ur")
        center(d, f"Surah {info['surah_en']}  •  {info['ref']}", 50, y, GOLD)
        y = draw_block(d, ar, "AmiriQuran-Regular.ttf", y + 90, 470, 66, 30, WHITE, 1.9)
        y = draw_block(d, ur, "NotoNastaliqUrdu.ttf", y + 10, 340, 40, 24, SOFT, 2.0, lang="ur")
        y += 30
        d.line([(380, y), (W - 380, y)], fill=GOLD, width=2)
        y = text(data["headline"], y + 40, 260, 68, 40, GOLD, 1.35)
        y = text(data["reflection"], y + 20, 420, 44, 28, WHITE, 1.45)
        return text(f"{label} {data['action']}", y + 30, 260, 42, 26, SOFT, 1.45)

    # Measure on a scratch image, then draw centred between the top and the footer.
    top, bottom = 100, H - 230
    used = content(ImageDraw.Draw(Image.new("RGB", (W, H))), 0)
    img = background()
    d = ImageDraw.Draw(img)
    d.rectangle([24, 24, W - 25, H - 25], outline=GOLD, width=4)
    content(d, top + max(0, (bottom - top - used) // 2))

    if CHANNEL_TAG:
        center(d, CHANNEL_TAG, 40, H - 190, MUTED)
    if urdu:
        draw_block(d, note, "NotoNastaliqUrdu.ttf", H - 140, 80, 30, 24, MUTED, 2.0, lang="ur")
    else:
        center(d, note, 32, H - 125, MUTED)
    img.save(path, "PNG")
    return path
