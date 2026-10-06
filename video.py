import subprocess
import wave
from functools import lru_cache

import requests
from PIL import Image, ImageDraw, ImageFont, features

from config import FONTS, W, H, FPS, CHANNEL_TAG, INTRO_SECONDS

FONT_URLS = {
    "Amiri-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf",
    "AmiriQuran-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/amiriquran/AmiriQuran-Regular.ttf",
    "NotoNastaliqUrdu.ttf": "https://github.com/google/fonts/raw/main/ofl/notonastaliqurdu/NotoNastaliqUrdu%5Bwght%5D.ttf",
}

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


def ensure_fonts():
    FONTS.mkdir(exist_ok=True)
    for name, url in FONT_URLS.items():
        p = FONTS / name
        if not p.exists():
            r = requests.get(url, timeout=120)
            r.raise_for_status()
            p.write_bytes(r.content)


def font(name, size):
    engine = ImageFont.Layout.RAQM if RAQM else ImageFont.Layout.BASIC
    return ImageFont.truetype(str(FONTS / name), size, layout_engine=engine)


def shape(text):
    return text if RAQM else get_display(arabic_reshaper.reshape(text))


def text_w(f, s, rtl=True, lang="ar"):
    if RAQM:
        return f.getlength(s, direction="rtl" if rtl else "ltr", language=lang if rtl else None)
    return f.getlength(s)


def wrap(text, f, max_w, rtl, lang):
    lines, cur = [], ""
    for word in text.split():
        t = (cur + " " + word).strip()
        if text_w(f, shape(t) if rtl else t, rtl, lang) <= max_w or not cur:
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


def draw_words(d, tokens, y, max_h, size, min_size, lh, color, hl=None, fname="AmiriQuran-Regular.ttf"):
    """Draw Arabic words right-to-left, one by one, so a single word can be highlighted.
    tokens: list of (text, index); the token whose index == hl gets a gold box.
    The layout depends only on the tokens, so every highlight state lines up exactly."""
    max_w = W - 140
    while True:
        f = font(fname, size)
        space = text_w(f, " ")
        lines, cur, cur_w = [], [], 0.0
        for text, idx in tokens:
            ww = text_w(f, shape(text))
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
    kw = dict(direction="rtl", language="ar") if RAQM else {}
    for words, line_w in lines:
        # Highlight box height = real ink extent of this line (harakat above and below included)
        boxes = [f.getbbox(shape(t), **kw) for t, _, _ in words]
        top, bottom = min(bx[1] for bx in boxes) - 8, max(bx[3] for bx in boxes) + 8
        band = size * 0.55                      # lines repeat every line_h; keep the box in this line's band
        top, bottom = max(top, band), min(bottom, band + line_h)
        x = (W + line_w) / 2                    # right edge of the centred line
        for text, idx, ww in words:
            x -= ww
            hit = hl is not None and idx == hl
            if hit:
                d.rounded_rectangle([x - 12, y + top, x + ww + 12, y + bottom], radius=14, fill=HL_BG)
            d.text((x, y), shape(text), font=f, fill=GOLD if hit else color, **kw)
            x -= space
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


def make_frame(item, path, hl=None, urdu=None):
    """item may be a real ayah, or the Bismillah frame (item["is_bismillah"]).
    hl: index of the Arabic word being recited (highlighted), or None.
    urdu: None = no Urdu audio; False = Arabic is playing (Urdu dimmed); True = Urdu is being read."""
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
    y = draw_words(d, tokens, 380, 640, 78, 34, 1.9, DIM if urdu else WHITE, hl)
    if item.get("sajda"):
        note = "آیتِ سجدہ" + (" (عند الشافعی)" if (item["surah"], item["ayah"]) == (22, 77) else "")
        y = draw_block(d, note, "NotoNastaliqUrdu.ttf", y, 110, 40, 30, GOLD, 2.2, lang="ur")

    # urdu translation
    y = max(y + 40, 1060)
    d.line([(400, y - 20), (W - 400, y - 20)], fill=(90, 130, 110), width=2)
    ur_color = SOFT if urdu is None else (WHITE if urdu else DIM)
    draw_block(d, item["ur"], "NotoNastaliqUrdu.ttf", y + 10, H - y - 260, 52, 28, ur_color, 2.0, lang="ur")

    if CHANNEL_TAG:
        center(d, CHANNEL_TAG, 38, H - 150, MUTED)
    img.save(path)


def card(info, w, h):
    """Title card: used as the reel's first frame (vertical) and as the YouTube thumbnail (landscape)."""
    img = background(w, h)
    d = ImageDraw.Draw(img)
    d.rectangle([24, 24, w - 25, h - 25], outline=GOLD, width=4)
    urdu = "قرآن پاک اردو ترجمہ کے ساتھ"
    if h > w:   # vertical 9:16
        center(d, f"Surah {info['surah']}", 60, 380, MUTED, w)
        draw_block(d, info["surah_ar"], "Amiri-Regular.ttf", 480, 330, 190, 90, GOLD, 1.6, width=w)
        center(d, f"Surah {info['surah_en']}", 88, 860, WHITE, w)
        center(d, info["label"], 66, 990, GOLD, w)
        if info["part_label"]:
            center(d, info["part_label"], 60, 1080, SOFT, w)
        draw_block(d, urdu, "NotoNastaliqUrdu.ttf", 1260, 200, 64, 40, SOFT, 2.0, lang="ur", width=w)
        if CHANNEL_TAG:
            center(d, CHANNEL_TAG, 42, h - 170, MUTED, w)
    else:       # landscape 16:9 thumbnail
        draw_block(d, info["surah_ar"], "Amiri-Regular.ttf", 50, 270, 170, 80, GOLD, 1.5, width=w)
        center(d, f"Surah {info['surah_en']}", 72, 330, WHITE, w)
        sub = info["label"] + (f"  •  {info['part_label']}" if info["part_label"] else "")
        center(d, sub, 54, 435, GOLD, w)
        draw_block(d, urdu, "NotoNastaliqUrdu.ttf", 530, 140, 48, 30, SOFT, 2.0, lang="ur", width=w)
    return img


def make_thumbnail(info, path):
    ensure_fonts()
    card(info, 1280, 720).save(path, "JPEG", quality=90)
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


def render(items, audio_lists, info, out_path, workdir, log=print):
    """One frame per ayah, timed to its audio. audio_lists[i] = files played in order
    for ayah i (Arabic, then Urdu). A title card is shown first. Returns total seconds."""
    ensure_fonts()
    workdir.mkdir(parents=True, exist_ok=True)

    frames, wavs = [], []
    if INTRO_SECONDS > 0:
        fp = workdir / "intro.png"
        card(info, W, H).save(fp)
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
        has_urdu = len(files) > 1
        words = it.get("words") or []
        states = word_timeline(it.get("segments") or [], len(words), durs[0])
        if has_urdu:
            states.append((sum(durs[1:]), "urdu"))
        drawn = {}
        for sec, st in states:
            if st not in drawn:
                fp = workdir / f"f{i}_{len(drawn)}.png"
                if st == "urdu":
                    make_frame(it, fp, urdu=True)
                else:
                    make_frame(it, fp, hl=st, urdu=False if has_urdu else None)
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
