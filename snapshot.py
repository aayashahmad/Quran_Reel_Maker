"""A shareable image (PNG, 1080 wide, 4:5 or taller for long ayat) of one Quran prophecy: its title in English and
Urdu, the full ayat in Arabic with their English meaning, the reference, how it came true, and the site's name at
the bottom. Nothing is cut: the picture grows taller when the ayat are long."""
import io
from functools import lru_cache

from PIL import Image, ImageDraw

from video import font, shape, text_w, wrap, RAQM, GOLD, GOLD2, WHITE, SOFT, MUTED, SITE_LABEL

W, MIN_H, MAX_H = 1080, 1350, 2400
PAD = 84                                     # inside the gold frame
INNER = W - 2 * PAD
GREEN = (120, 200, 150)


def _lines(text, fname, size, rtl, lang):
    return font(fname, size), wrap(text, font(fname, size), INNER, rtl, lang)


def _block(text, fname, size, lh, color, rtl=False, lang="ar", align="center", stroke=0):
    """(height, draw(d, y)) of a wrapped paragraph."""
    f, lines = _lines(text, fname, size, rtl, lang)
    step = int(size * lh)

    def draw(d, y):
        for ln in lines:
            s = shape(ln) if rtl else ln
            w = text_w(f, s, rtl, lang)
            x = (W - w) / 2 if align == "center" else PAD
            kw = dict(direction="rtl", language=lang) if rtl and RAQM else {}
            d.text((x, y), s, font=f, fill=color, stroke_width=stroke, stroke_fill=color, **kw)
            y += step
        return y
    return len(lines) * step, draw


def _plan(item, scale):
    """The blocks from top to bottom (with gaps) at a text scale (1 = full size)."""
    z = lambda n: max(16, int(n * scale))
    cat = "FULFILLED  ·  پوری ہو چکی" if item["cat"] == "past" else "STILL TO COME  ·  ابھی آنی ہے"
    blocks = [(_block("PROPHECIES IN THE QURAN", "Amiri-Regular.ttf", z(30), 1.3, GOLD), 6),
              (_block(cat, "NotoNaskhArabic.ttf", z(26), 1.5, GREEN if item["cat"] == "past" else GOLD2), 20),
              (_block(item["en"], "Amiri-Regular.ttf", z(54), 1.25, GOLD2, stroke=1), 6),
              (_block(item["ur"], "NotoNastaliqUrdu.ttf", z(36), 2.0, SOFT, rtl=True, lang="ur"), 40)]
    for r in item["refs"]:
        ar = " ".join(f"{v['ar']} ﴿{v['n']}﴾" for v in r["verses"])
        en = " ".join(v["en"] for v in r["verses"])
        span = f"{r['from']}" + (f"–{r['to']}" if r["to"] != r["from"] else "")
        blocks += [(_block(ar, "AmiriQuran-Regular.ttf", z(46), 1.95, WHITE, rtl=True), 14),
                   (_block(en, "Amiri-Regular.ttf", z(32), 1.45, SOFT), 10),
                   (_block(f"Surah {r['surah_en']} {r['surah']}:{span}", "Amiri-Regular.ttf", z(28), 1.3, GOLD), 24)]
    if item.get("note"):
        blocks.append((_block("How it came true: " + item["note"], "Amiri-Regular.ttf", z(28), 1.4, GREEN), 10))
    return blocks


@lru_cache(maxsize=64)
def _png(key, item_json):
    import json
    item = json.loads(item_json)
    footer = 150
    for scale in (1, .92, .85, .78, .72, .66, .6):          # the largest text that fits in MAX_H
        blocks = _plan(item, scale)
        body = sum(h + gap for (h, _), gap in blocks)
        if body + 2 * PAD + footer <= MAX_H:
            break
    h = max(MIN_H, body + 2 * PAD + footer)
    img = Image.new("RGB", (W, h))
    top, bot = (11, 61, 46), (3, 20, 15)
    d = ImageDraw.Draw(img)
    for y in range(h):                                        # the site's green gradient
        t = y / (h - 1)
        d.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))
    d.rounded_rectangle((28, 28, W - 28, h - 28), radius=36, outline=GOLD, width=3)
    d.rounded_rectangle((40, 40, W - 40, h - 40), radius=28, outline=(212, 175, 95, 90), width=1)
    y = PAD + max(0, (h - 2 * PAD - footer - body) // 2)      # centred when there is room
    for (bh, draw), gap in blocks:
        draw(d, y)
        y += bh + gap
    # the site's name at the bottom
    d.line([(W / 2 - 160, h - footer - 4), (W / 2 + 160, h - footer - 4)], fill=GOLD, width=2)
    f = font("Amiri-Regular.ttf", 46)
    d.text(((W - text_w(f, SITE_LABEL, rtl=False)) / 2, h - footer + 18), SITE_LABEL, font=f, fill=GOLD2,
           stroke_width=1, stroke_fill=GOLD2)
    f = font("Amiri-Regular.ttf", 26)
    sub = "Read every prophecy and make free Quran reels"
    d.text(((W - text_w(f, sub, rtl=False)) / 2, h - footer + 80), sub, font=f, fill=MUTED)
    out = io.BytesIO()
    img.save(out, "PNG", optimize=True)
    return out.getvalue()


def prophecy_png(item):
    """PNG bytes for one prophecy (item: as built for the page, with its "refs")."""
    import json
    keep = {k: item[k] for k in ("id", "cat", "en", "ur", "refs") if k in item}
    keep["note"] = item.get("note", "")
    return _png(item["id"], json.dumps(keep, ensure_ascii=False, sort_keys=True))
