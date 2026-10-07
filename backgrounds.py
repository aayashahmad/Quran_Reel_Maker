"""Moving backgrounds for reels: six styles drawn here (no downloaded footage), each a seamless
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
VERSION = 1                # bump when a style's look changes, so saved loops are made again
STYLES = ("stars", "particles", "rays", "aurora", "night", "waves")
GOLD = (212, 175, 95)
_lock = threading.Lock()


def pick(info):
    """The style for a reel: chosen from the surah and first ayah, so each reel gets its own
    and the same reel always looks the same."""
    return STYLES[(info["surah"] * 31 + info["first"]) % len(STYLES)]


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
    mx, my, mr = BW * 0.78, BH * 0.1, 26
    d.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=(240, 220, 170, 150))
    d.ellipse([mx - mr + 11, my - mr - 5, mx + mr + 11, my + mr - 5], fill=(0, 0, 0, 0))
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


DRAW = {"stars": _stars, "particles": _particles, "rays": _rays, "aurora": _aurora, "night": _night,
        "waves": _waves}


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
    """Path of the saved background loop for this style, making it first if needed (about 10-60 s once)."""
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
