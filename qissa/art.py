"""Paper-collage scene backgrounds, drawn in code (no stock photos, no copyright): layered torn-paper shapes with
soft shadows on a grainy paper texture. Only nature, sea, ships, fish, towns and plants: never prophets, people
or angels. Each is drawn larger than the video so the camera can drift across it."""
import math
import random
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter

W, H = 1080, 1920
PAD = 1.12                                   # drawn larger than the frame, for the slow camera move
BW, BH = int(W * PAD), int(H * PAD)
ARTS = ("paper", "sea-night", "ship", "fish", "darkness", "dawn", "shore", "town-dusk", "town-dawn")


@lru_cache(maxsize=4)
def _grain(w, h, seed=7):
    rnd = random.Random(seed)
    small = Image.new("L", (w // 4, h // 4))
    small.putdata([128 + int(rnd.gauss(0, 14)) for _ in range(small.width * small.height)])
    return small.resize((w, h), Image.BILINEAR).filter(ImageFilter.GaussianBlur(1))


def _paper(w, h, top, bottom, grain=0.10):
    g = Image.new("RGB", (1, 256))
    for y in range(256):
        t = y / 255
        g.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    img = g.resize((w, h))
    noise = _grain(w, h).convert("RGB")
    return Image.blend(img, Image.composite(noise, img, Image.new("L", (w, h), 255)), grain)


def _torn(points, rnd, jag=10):
    """Roughen a polygon's edges like torn paper."""
    out = []
    for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1]):
        n = max(2, int(math.hypot(x2 - x1, y2 - y1) / 18))
        for k in range(n):
            t = k / n
            out.append((x1 + (x2 - x1) * t + rnd.uniform(-jag, jag) * 0.3, y1 + (y2 - y1) * t + rnd.uniform(-jag, jag)))
    return out


def _layer(img, poly, color, shadow=18, rnd=None):
    """A torn paper cut-out with a soft drop shadow."""
    rnd = rnd or random.Random(1)
    poly = _torn(poly, rnd)
    sh = Image.new("L", img.size, 0)
    ImageDraw.Draw(sh).polygon([(x + 6, y + 12) for x, y in poly], fill=110)
    sh = sh.filter(ImageFilter.GaussianBlur(shadow))
    img.paste((0, 0, 0), (0, 0), sh)
    paper = _paper(img.width, img.height, color, tuple(max(0, c - 18) for c in color), 0.16)
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).polygon(poly, fill=255)
    img.paste(paper, (0, 0), mask)


def _wave(y, amp, freq, phase, w=BW, h=BH):
    pts = [(x, y + amp * math.sin(x / freq + phase)) for x in range(-40, w + 60, 30)]
    return pts + [(w + 60, h + 40), (-40, h + 40)]


def _cloud(img, cx, cy, s, color, rnd):
    for dx, dy, r in ((-0.9, 0.15, 0.55), (-0.3, -0.25, 0.75), (0.45, -0.1, 0.62), (1.0, 0.2, 0.45)):
        x, y, rr = cx + dx * s, cy + dy * s, r * s
        _layer(img, [(x + rr * math.cos(a), y + rr * 0.8 * math.sin(a)) for a in [i * math.pi / 9 for i in range(18)]],
               color, 10, rnd)


def _ship(img, x, y, s, rnd):
    hull = [(x - 1.6 * s, y), (x + 1.7 * s, y - 0.1 * s), (x + 1.2 * s, y + 0.75 * s), (x - 1.15 * s, y + 0.75 * s)]
    _layer(img, hull, (112, 82, 52), 14, rnd)
    _layer(img, [(x - 0.05 * s, y - 2.3 * s), (x + 0.07 * s, y - 2.3 * s), (x + 0.07 * s, y), (x - 0.05 * s, y)], (82, 60, 40), 6, rnd)
    _layer(img, [(x + 0.12 * s, y - 2.1 * s), (x + 1.25 * s, y - 0.35 * s), (x + 0.12 * s, y - 0.35 * s)], (226, 214, 188), 10, rnd)


def _fish(img, cx, cy, s, color, rnd):
    body = [(cx - 2.2 * s + 4.4 * s * t, cy - math.sin(math.pi * t) * 0.85 * s) for t in [i / 24 for i in range(25)]]
    body += [(cx - 2.2 * s + 4.4 * s * t, cy + math.sin(math.pi * t) * 0.62 * s) for t in [i / 24 for i in range(24, -1, -1)]]
    _layer(img, body, color, 24, rnd)
    _layer(img, [(cx + 2.0 * s, cy), (cx + 2.9 * s, cy - 0.75 * s), (cx + 2.65 * s, cy), (cx + 2.9 * s, cy + 0.6 * s)],
           tuple(max(0, c - 12) for c in color), 12, rnd)
    d = ImageDraw.Draw(img)
    d.ellipse([cx - 1.65 * s - 9, cy - 0.25 * s - 9, cx - 1.65 * s + 9, cy - 0.25 * s + 9], fill=(230, 230, 220))


def _town(img, base, color, lit, rnd):
    d = ImageDraw.Draw(img)
    x = -20
    while x < BW:
        w, h = rnd.randint(70, 150), rnd.randint(120, 330)
        _layer(img, [(x, base - h), (x + w, base - h), (x + w, base + 60), (x, base + 60)], color, 8, rnd)
        if rnd.random() < 0.35:
            r = w * 0.45
            _layer(img, [(x + w / 2 + r * math.cos(a), base - h - r * 0.2 + r * math.sin(a))
                         for a in [math.pi + i * math.pi / 10 for i in range(11)]] + [(x + w / 2 + r, base - h)], color, 6, rnd)
        for _ in range(rnd.randint(1, 4)):
            wx, wy = x + rnd.randint(12, max(13, w - 24)), base - rnd.randint(30, max(31, h - 30))
            d.rectangle([wx, wy, wx + 12, wy + 16], fill=lit)
        x += w + rnd.randint(-10, 20)


def draw(art, seed=0):
    """The background for one scene, BW x BH."""
    rnd = random.Random(hash(art) % 1000 + seed)
    if art == "paper":
        return _paper(BW, BH, (34, 33, 31), (20, 19, 18), 0.18)
    if art == "sea-night":
        img = _paper(BW, BH, (16, 34, 52), (6, 16, 28))
        for i, (y, col) in enumerate([(BH * 0.55, (22, 52, 78)), (BH * 0.68, (17, 42, 66)), (BH * 0.82, (12, 32, 52))]):
            _layer(img, _wave(y, 26 - i * 5, 120 + i * 30, i * 1.7), col, 20, rnd)
        return img
    if art == "ship":
        img = _paper(BW, BH, (168, 170, 168), (120, 124, 126))
        for cx, cy, s in ((BW * 0.2, BH * 0.18, 90), (BW * 0.75, BH * 0.12, 70), (BW * 0.55, BH * 0.3, 60)):
            _cloud(img, cx, cy, s, (196, 196, 192), rnd)
        _layer(img, _wave(BH * 0.62, 22, 110, 0), (64, 104, 122), 18, rnd)
        _ship(img, BW * 0.5, BH * 0.6, 150, rnd)
        _layer(img, _wave(BH * 0.68, 26, 95, 2), (52, 90, 110), 20, rnd)
        _layer(img, _wave(BH * 0.8, 20, 140, 4), (40, 74, 94), 20, rnd)
        return img
    if art == "fish":
        img = _paper(BW, BH, (18, 44, 66), (5, 14, 24))
        _fish(img, BW * 0.45, BH * 0.62, 190, (52, 74, 92), rnd)
        _layer(img, _wave(BH * 0.86, 18, 120, 1), (8, 22, 36), 20, rnd)
        return img
    if art == "darkness":
        img = _paper(BW, BH, (12, 14, 18), (3, 4, 6), 0.2)
        d = ImageDraw.Draw(img)
        for _ in range(60):
            x, y, r = rnd.uniform(0, BW), rnd.uniform(0, BH), rnd.uniform(1, 3)
            d.ellipse([x - r, y - r, x + r, y + r], fill=(60, 64, 72))
        return img
    if art == "dawn":
        img = _paper(BW, BH, (232, 190, 140), (120, 150, 160))
        sun = Image.new("L", img.size, 0)
        ImageDraw.Draw(sun).ellipse([BW * 0.35, BH * 0.42, BW * 0.65, BH * 0.42 + BW * 0.3], fill=200)
        img.paste((250, 222, 170), (0, 0), sun.filter(ImageFilter.GaussianBlur(40)))
        _layer(img, _wave(BH * 0.6, 14, 140, 0), (110, 140, 150), 16, rnd)
        _layer(img, _wave(BH * 0.74, 18, 110, 2), (80, 114, 128), 18, rnd)
        return img
    if art == "shore":
        img = _paper(BW, BH, (214, 210, 200), (186, 180, 168))
        _layer(img, _wave(BH * 0.5, 14, 160, 1), (120, 150, 156), 14, rnd)
        _layer(img, _wave(BH * 0.6, 30, 220, 3), (206, 186, 150), 18, rnd)
        for i in range(9):                                  # the gourd plant: broad leaves over the sand
            x, y, s = BW * (0.2 + 0.08 * i), BH * (0.62 + 0.03 * (i % 3)), rnd.uniform(70, 110)
            leaf = [(x + s * math.cos(a) * (1 - 0.35 * abs(math.sin(a))), y - s * 0.7 * math.sin(a))
                    for a in [i2 * math.pi / 10 for i2 in range(21)]]
            _layer(img, leaf, (84 + rnd.randint(0, 20), 122 + rnd.randint(0, 20), 70), 10, rnd)
        return img
    if art in ("town-dusk", "town-dawn"):
        dusk = art == "town-dusk"
        img = _paper(BW, BH, (70, 64, 70) if dusk else (196, 180, 160), (30, 28, 34) if dusk else (150, 140, 130))
        for cx, cy, s in ((BW * 0.25, BH * 0.2, 90), (BW * 0.72, BH * 0.26, 110)):
            _cloud(img, cx, cy, s, (90, 84, 92) if dusk else (220, 212, 200), rnd)
        _town(img, BH * 0.72, (54, 48, 52) if dusk else (120, 110, 104), (240, 196, 110), rnd)
        _layer(img, [(-40, BH * 0.78), (BW + 40, BH * 0.76), (BW + 40, BH + 40), (-40, BH + 40)],
               (40, 36, 40) if dusk else (110, 100, 94), 16, rnd)
        return img
    raise ValueError(f"unknown art {art!r}: use one of {', '.join(ARTS)}")
