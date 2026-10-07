"""Moving backgrounds for reels: eleven styles drawn here (no downloaded footage), each a seamless
12-second loop. A loop is made once, saved in data/bg/, and played behind every reel that uses it.
All motion repeats a whole number of times per loop, so the end meets the start without a jump."""
import math
import random
import subprocess
import threading
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter

from config import DATA

BW, BH = 540, 960          # drawn at half size: soft shapes look the same once scaled up, and draw 4x faster
LOOP_FPS, LOOP_SECONDS = 20, 12
FRAMES = LOOP_FPS * LOOP_SECONDS
VERSION = 2                # bump when a style's look changes, so saved loops are made again
STYLES = ("stars", "particles", "rays", "aurora", "night", "waves",
          "mosque", "lanterns", "arches", "desert", "rosette")
NAMES = {"stars": "Star pattern", "particles": "Gold particles", "rays": "Light rays", "aurora": "Aurora",
         "night": "Night sky", "waves": "Waves", "mosque": "Mosques at dusk", "lanterns": "Lanterns",
         "arches": "Islamic arch", "desert": "Desert night", "rosette": "Rosette"}
GOLD = (212, 175, 95)
_lock = threading.Lock()


def pick(info):
    """The style for a reel: chosen from the surah and first ayah, so each reel gets its own
    and the same reel always looks the same."""
    # large primes, so the result keeps depending on both whatever the number of styles
    # (static/device-reel.js uses the same formula)
    return STYLES[(info["surah"] * 7919 + info["first"] * 131) % len(STYLES)]


@lru_cache(maxsize=None)
def _base(top=(11, 61, 46), bottom=(3, 20, 15)):
    g = Image.new("RGB", (1, 256))
    for y in range(256):
        t = y / 255
        g.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return g.resize((BW, BH), Image.BILINEAR)


def _glow(base, layer, radius):
    """Blend a layer of light shapes over the base, softened."""
    return Image.alpha_composite(base.convert("RGBA"), layer.filter(ImageFilter.GaussianBlur(radius))).convert("RGB")


def _star(cx, cy, r):
    """Eight-pointed star outline (two overlapping squares), as on the website."""
    pts = []
    for k in range(16):
        a = math.pi / 8 * k
        rr = r if k % 2 == 0 else r * 0.76
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


def _stars(t, rnd):
    """The star pattern drifting diagonally by exactly one tile per loop."""
    img = _base().copy()
    layer = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    tile = 120
    off = t * tile
    for gy in range(-1, BH // tile + 2):
        for gx in range(-1, BW // tile + 2):
            cx, cy = gx * tile + off + (tile / 2 if gy % 2 else 0), gy * tile + off
            d.polygon(_star(cx, cy, 30), outline=GOLD + (95,), width=2)
            d.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], outline=GOLD + (70,), width=2)
    return _glow(img, layer, 0.7)


def _particles(t, rnd):
    """Soft gold lights rising and twinkling."""
    img = _base().copy()
    layer = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for p in rnd["particles"]:
        y = (p["y"] - t * BH * p["laps"]) % (BH + 40) - 20
        x = p["x"] + 10 * math.sin(2 * math.pi * (t * p["sway"] + p["phase"]))
        a = int(p["alpha"] * (0.55 + 0.45 * math.sin(2 * math.pi * (t * p["tw"] + p["phase"]))))
        r = p["r"]
        d.ellipse([x - r, y - r, x + r, y + r], fill=GOLD + (a,))
    return _glow(img, layer, 2.2)


def _rays(t, rnd):
    """Soft light rays from above, swaying slowly."""
    img = _base().copy()
    layer = Image.new("RGBA", (BW // 2, BH // 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    ox, oy, length = BW // 4, -40, BH
    sway = 0.10 * math.sin(2 * math.pi * t)
    for k in range(9):
        a = math.pi / 2 + (k - 4) * 0.16 + sway * (1 if k % 2 else -1)
        w = 0.035 + 0.02 * math.sin(2 * math.pi * (t * 2 + k / 9))
        pts = [(ox, oy), (ox + length * math.cos(a - w), oy + length * math.sin(a - w)),
               (ox + length * math.cos(a + w), oy + length * math.sin(a + w))]
        d.polygon(pts, fill=GOLD + (34 if k % 2 else 22,))
    layer = layer.filter(ImageFilter.GaussianBlur(6)).resize((BW, BH), Image.BILINEAR)
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


def _aurora(t, rnd):
    """Large soft colour clouds drifting on closed paths."""
    img = _base((8, 44, 38), (2, 14, 12)).copy()
    small = Image.new("RGBA", (BW // 4, BH // 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(small)
    sw, sh = small.size
    for b in rnd["blobs"]:
        x = sw * (0.5 + 0.35 * math.sin(2 * math.pi * (t * b["fx"] + b["px"])))
        y = sh * (0.5 + 0.38 * math.cos(2 * math.pi * (t * b["fy"] + b["py"])))
        r = b["r"]
        d.ellipse([x - r, y - r, x + r, y + r], fill=b["color"] + (70,))
    small = small.filter(ImageFilter.GaussianBlur(14)).resize((BW, BH), Image.BILINEAR)
    return Image.alpha_composite(img.convert("RGBA"), small).convert("RGB")


def _night(t, rnd):
    """A night sky: twinkling stars and a crescent moon."""
    img = _base((6, 22, 34), (2, 8, 14)).copy()
    layer = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for s in rnd["sky"]:
        a = int(s["alpha"] * (0.5 + 0.5 * math.sin(2 * math.pi * (t * s["tw"] + s["phase"]))))
        r = s["r"]
        d.ellipse([s["x"] - r, s["y"] - r, s["x"] + r, s["y"] + r], fill=(235, 230, 210, a))
    mx, my, mr = BW * 0.84, BH * 0.925, 20     # bottom right: below the translation, clear of all text
    d.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=(240, 220, 170, 150))
    d.ellipse([mx - mr + 9, my - mr - 4, mx + mr + 9, my + mr - 4], fill=(0, 0, 0, 0))
    return _glow(img, layer, 0.8)


def _waves(t, rnd):
    """Gentle gold wave lines moving across the lower half."""
    img = _base().copy()
    layer = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for k in range(7):
        y0, amp, cycles, speed = BH * (0.55 + k * 0.06), 10 + 3 * k, 1.5 + k * 0.25, (1, 2, 1, 3, 2, 1, 2)[k]
        pts = [(x, y0 + amp * math.sin(2 * math.pi * (x / BW * cycles + t * speed * (1 if k % 2 else -1))))
               for x in range(0, BW + 6, 6)]
        d.line(pts, fill=GOLD + (55 + 10 * k,), width=3)
    return _glow(img, layer, 1.2)


def _mosque_shape(d, x0, base, scale, fill):
    """A mosque silhouette: a main dome on a drum, two small domes and two minarets."""
    s = scale
    d.rectangle([x0 - 70 * s, base - 40 * s, x0 + 70 * s, base], fill=fill)            # prayer hall
    d.rectangle([x0 - 34 * s, base - 62 * s, x0 + 34 * s, base - 40 * s], fill=fill)    # drum
    d.ellipse([x0 - 38 * s, base - 110 * s, x0 + 38 * s, base - 38 * s], fill=fill)     # main dome
    d.polygon([(x0 - 3 * s, base - 108 * s), (x0, base - 126 * s), (x0 + 3 * s, base - 108 * s)], fill=fill)
    for side in (-1, 1):
        cx = x0 + side * 52 * s
        d.ellipse([cx - 16 * s, base - 66 * s, cx + 16 * s, base - 34 * s], fill=fill)  # small domes
        mx = x0 + side * 92 * s
        d.rectangle([mx - 6 * s, base - 150 * s, mx + 6 * s, base], fill=fill)          # minaret
        d.rectangle([mx - 9 * s, base - 118 * s, mx + 9 * s, base - 112 * s], fill=fill)  # balcony
        d.polygon([(mx - 7 * s, base - 150 * s), (mx, base - 172 * s), (mx + 7 * s, base - 150 * s)], fill=fill)


def _mosque(t, rnd):
    """Mosques at dusk along the bottom, the sky glowing and stars twinkling above."""
    glow = 0.5 + 0.5 * math.sin(2 * math.pi * t)
    img = _base((10, 30, 46), (38 + int(14 * glow), 34 + int(8 * glow), 40)).copy()
    layer = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for st in rnd["sky"][:70]:
        if st["y"] < BH * 0.55:
            a = int(st["alpha"] * 0.7 * (0.5 + 0.5 * math.sin(2 * math.pi * (t * st["tw"] + st["phase"]))))
            d.ellipse([st["x"] - 1, st["y"] - 1, st["x"] + 1, st["y"] + 1], fill=(235, 230, 210, a))
    img = _glow(img, layer, 1.2)
    horizon = Image.new("RGBA", (BW // 4, BH // 4), (0, 0, 0, 0))
    ImageDraw.Draw(horizon).ellipse([BW / 8 - 70, BH / 4 - 30, BW / 8 + 70, BH / 4 + 20],
                                    fill=(230, 150, 80, int(70 + 40 * glow)))
    horizon = horizon.filter(ImageFilter.GaussianBlur(16)).resize((BW, BH), Image.BILINEAR)
    img = Image.alpha_composite(img.convert("RGBA"), horizon).convert("RGB")
    sil = ImageDraw.Draw(img)
    _mosque_shape(sil, BW * 0.2, BH, 0.55, (6, 18, 16))
    _mosque_shape(sil, BW * 0.82, BH, 0.48, (6, 18, 16))
    _mosque_shape(sil, BW * 0.5, BH, 0.8, (3, 12, 11))
    return img


def _lantern(d, cx, top, length, angle, a):
    """A hanging Ramadan lantern on its string, swung by `angle` (radians)."""
    bx, by = cx + length * math.sin(angle), top + length * math.cos(angle)
    d.line([(cx, top), (bx, by)], fill=GOLD + (int(120 * a),), width=1)
    w, h = 26, 48
    d.polygon([(bx - 8, by), (bx + 8, by), (bx + w / 2, by + 12), (bx - w / 2, by + 12)], fill=GOLD + (int(210 * a),))
    d.rectangle([bx - w / 2, by + 12, bx + w / 2, by + 12 + h], outline=GOLD + (int(230 * a),), width=2,
                fill=(240, 190, 90, int(140 * a)))
    d.line([(bx, by + 12), (bx, by + 12 + h)], fill=GOLD + (int(160 * a),), width=1)
    d.polygon([(bx - w / 2, by + 12 + h), (bx + w / 2, by + 12 + h), (bx, by + 32 + h)], fill=GOLD + (int(210 * a),))


def _lanterns(t, rnd):
    """Ramadan lanterns hanging at both sides, swaying gently and glowing."""
    img = _base((14, 40, 44), (3, 14, 14)).copy()
    glow = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
    lit = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
    g, d = ImageDraw.Draw(glow), ImageDraw.Draw(lit)
    # short strings: every lantern stays above y=190, where the Arabic text starts
    for i, (cx, length) in enumerate(((24, 40), (60, 95), (96, 15), (BW - 96, 25), (BW - 60, 75), (BW - 24, 100))):
        ang = 0.09 * math.sin(2 * math.pi * (t * (1 + i % 2) + i * 0.27))
        bx, by = cx + length * math.sin(ang), length * math.cos(ang)
        pulse = 0.75 + 0.25 * math.sin(2 * math.pi * (t * 2 + i * 0.4))
        g.ellipse([bx - 50, by - 10, bx + 50, by + 100], fill=(240, 180, 80, int(80 * pulse)))
        _lantern(d, cx, 0, length, ang, 0.9)
    img = _glow(img, glow, 14)
    return Image.alpha_composite(img.convert("RGBA"), lit).convert("RGB")


def _arch(cx, base, w, h):
    """Outline points of a pointed (Islamic) arch: upright sides, then two circular arcs meeting at
    the apex, each centred inside the opposite half (radius 0.8 of the width)."""
    r = 0.8 * w
    apex = math.acos((w / 2 - r) / r)                      # angle where the left arc reaches the centre line
    rise = r * math.sin(apex)
    ys = base - (h - rise)                                 # where the arcs spring from the sides
    left = [(cx - w / 2 + r + r * math.cos(a), ys - r * math.sin(a))
            for a in (math.pi - (math.pi - apex) * k / 24 for k in range(25))]
    right = [(2 * cx - x, y) for x, y in reversed(left)]
    return [(cx - w / 2, base)] + left + right[1:] + [(cx + w / 2, base)]


def _arches(t, rnd):
    """A great pointed arch framing the screen, with light travelling along it, and small arches below."""
    img = _base().copy()
    layer = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    big = _arch(BW / 2, BH - 18, BW - 28, BH - 40)
    d.line(big + [big[0]], fill=GOLD + (140,), width=3)
    inner = _arch(BW / 2, BH - 30, BW - 52, BH - 64)
    d.line(inner + [inner[0]], fill=GOLD + (70,), width=2)
    n = len(big)
    for k in range(3):                                         # three lights running round the arch
        pos = (t + k / 3) % 1 * (n - 1)
        x, y = big[int(pos)]
        d.ellipse([x - 14, y - 14, x + 14, y + 14], fill=(250, 220, 150, 200))
    for i in range(5):
        cx = BW * (0.18 + i * 0.16)
        small = _arch(cx, BH - 18, 64, 120)
        d.line(small, fill=GOLD + (60,), width=2)
    return _glow(img, layer, 1.6)


def _desert(t, rnd):
    """Desert dunes under a night sky, sand drifting across them."""
    img = _base((8, 20, 34), (30, 26, 22)).copy()
    layer = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for st in rnd["sky"]:
        if st["y"] < BH * 0.6:
            a = int(st["alpha"] * (0.5 + 0.5 * math.sin(2 * math.pi * (t * st["tw"] + st["phase"]))))
            r = st["r"]
            d.ellipse([st["x"] - r, st["y"] - r, st["x"] + r, st["y"] + r], fill=(235, 230, 210, a))
    for p in rnd["particles"][:30]:                            # sand drifting right, a whole lap per loop
        x = (p["x"] + t * BW * p["laps"]) % BW
        y = BH * 0.78 + (p["y"] % (BH * 0.2))
        d.ellipse([x - 1.2, y - 1.2, x + 1.2, y + 1.2], fill=(220, 190, 140, int(p["alpha"] * 0.6)))
    img = _glow(img, layer, 0.8)
    dunes = ImageDraw.Draw(img)
    for k, (h, amp, col) in enumerate(((0.80, 28, (44, 34, 24)), (0.86, 22, (34, 26, 18)), (0.92, 16, (22, 17, 12)))):
        pts = [(x, BH * h + amp * math.sin(2 * math.pi * (x / BW * (1.2 + k * 0.4)) + k)) for x in range(0, BW + 6, 6)]
        dunes.polygon(pts + [(BW, BH), (0, BH)], fill=col)
    return img


def _rosette(t, rnd):
    """A large faint sixteen-point geometric rosette turning slowly behind the text."""
    img = _base().copy()
    layer = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy, rot = BW / 2, BH * 0.5, 2 * math.pi / 16 * t        # turns one point per loop: seamless
    for ring, (r, alpha) in enumerate(((250, 85), (190, 75), (130, 65), (70, 55))):
        pts = []
        for k in range(32):
            a = rot * (1 if ring % 2 == 0 else -1) + math.pi / 16 * k
            rr = r if k % 2 == 0 else r * 0.82
            pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        d.polygon(pts, outline=GOLD + (alpha,), width=2)
    for k in range(16):
        a = rot + math.pi / 8 * k
        d.line([(cx + 70 * math.cos(a), cy + 70 * math.sin(a)), (cx + 250 * math.cos(a), cy + 250 * math.sin(a))],
               fill=GOLD + (40,), width=1)
    return _glow(img, layer, 0.8)


DRAW = {"stars": _stars, "particles": _particles, "rays": _rays, "aurora": _aurora, "night": _night,
        "waves": _waves, "mosque": _mosque, "lanterns": _lanterns, "arches": _arches, "desert": _desert,
        "rosette": _rosette}


def _randoms():
    """Fixed positions and speeds (same every time), with whole-number repeats per loop."""
    rnd = random.Random(7)
    return {
        "particles": [dict(x=rnd.uniform(0, BW), y=rnd.uniform(0, BH), r=rnd.uniform(3, 7), laps=rnd.choice((1, 1, 2)),
                           sway=rnd.choice((1, 2)), tw=rnd.choice((1, 2, 3)), phase=rnd.random(),
                           alpha=rnd.randint(150, 240)) for _ in range(55)],
        "blobs": [dict(fx=rnd.choice((1, 2)), fy=rnd.choice((1, 2)), px=rnd.random(), py=rnd.random(),
                       r=rnd.uniform(28, 46), color=c)
                  for c in ((20, 120, 100), (30, 90, 120), (150, 120, 50), (25, 110, 70))],
        "sky": [dict(x=rnd.uniform(0, BW), y=rnd.uniform(0, BH * 0.8), r=rnd.choice((0.8, 1, 1.2, 1.6)),
                     tw=rnd.choice((1, 2, 3)), phase=rnd.random(), alpha=rnd.randint(120, 230)) for _ in range(140)],
    }


def loop(style):
    """Path of the saved background loop for this style, making it first if needed (seconds, once)."""
    out = DATA / "bg" / f"{style}-v{VERSION}.mp4"
    with _lock:
        if out.exists():
            return out
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_suffix(".part.mp4")
        proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                                 "-s", f"{BW}x{BH}", "-r", str(LOOP_FPS), "-i", "-", "-c:v", "libx264",
                                 "-preset", "medium", "-crf", "22", "-pix_fmt", "yuv420p", "-g", str(LOOP_FPS),
                                 str(tmp)], stdin=subprocess.PIPE)
        rnd, draw = _randoms(), DRAW[style]
        for i in range(FRAMES):
            proc.stdin.write(draw(i / FRAMES, rnd).tobytes())
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError(f"could not make the {style} background")
        tmp.replace(out)
        return out
