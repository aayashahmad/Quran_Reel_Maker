"""The moving map: NASA's Blue Marble satellite picture of Arabia (public domain, from NASA GIBS). The camera comes
down from the whole region to the chapter's places while the route draws itself, and the chapter title fades in.
Every place is drawn at its real latitude and longitude."""
import math
import subprocess
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

import video
from video import font, shape, text_w, wrap

ROOT = Path(__file__).resolve().parent.parent
SAT = ROOT / "data" / "geo" / "BlueMarble_ShadedRelief_Bathymetry.jpg"
LAT0, LON0, LAT1, LON1 = 17.0, 31.0, 34.0, 47.0          # the picture's edges
PX = 3200, 3400
URL = ("https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi?SERVICE=WMS&REQUEST=GetMap&VERSION=1.3.0"
       f"&LAYERS=BlueMarble_ShadedRelief_Bathymetry&STYLES=&CRS=EPSG:4326&BBOX={LAT0},{LON0},{LAT1},{LON1}"
       f"&WIDTH={PX[0]}&HEIGHT={PX[1]}&FORMAT=image/jpeg")
W, H, FPS = 1920, 1080, 30
CREDIT = "Satellite image: NASA Blue Marble"
GOLD, CRIMSON = (240, 213, 147), (214, 64, 52)
SERIF, UR = "Amiri-Regular.ttf", "NotoNastaliqUrdu.ttf"
_img = None


def picture():
    global _img
    if _img is None:
        if not SAT.exists():
            SAT.parent.mkdir(parents=True, exist_ok=True)
            req = urllib.request.Request(URL, headers={"User-Agent": "QuranReelMaker/1.0 (https://quranreelmaker.xyz)"})
            SAT.write_bytes(urllib.request.urlopen(req, timeout=120).read())
        _img = Image.open(SAT).convert("RGB")
    return _img


def view_for(points, min_lat_span=3.4, pad=1.7):
    """(centre lat, centre lon, lat span) showing all the points, 16:9 on screen."""
    lats, lons = [p[0] for p in points], [p[1] for p in points]
    clat, clon = (max(lats) + min(lats)) / 2, (max(lons) + min(lons)) / 2
    k = math.cos(math.radians(clat))
    span = max(min_lat_span, (max(lats) - min(lats)) * pad, (max(lons) - min(lons)) * pad * k / (W / H))
    return clamp(clat, clon, span)


def clamp(clat, clon, span):
    k = math.cos(math.radians(clat))
    span = min(span, LAT1 - LAT0 - 0.2, (LON1 - LON0 - 0.2) * k / (W / H))
    lon_span = span * (W / H) / k
    clat = min(max(clat, LAT0 + span / 2), LAT1 - span / 2)
    clon = min(max(clon, LON0 + lon_span / 2), LON1 - lon_span / 2)
    return clat, clon, span


def frame_of(v):
    """The part of the picture a view shows, as a 1920x1080 frame, and how to place a (lat, lon) on it."""
    clat, clon, span = v
    lon_span = span * (W / H) / math.cos(math.radians(clat))
    la0, la1, lo0, lo1 = clat - span / 2, clat + span / 2, clon - lon_span / 2, clon + lon_span / 2
    px = lambda lo: (lo - LON0) / (LON1 - LON0) * PX[0]
    py = lambda la: (LAT1 - la) / (LAT1 - LAT0) * PX[1]
    img = picture().transform((W, H), Image.Transform.EXTENT, (px(lo0), py(la1), px(lo1), py(la0)),
                              Image.Resampling.BILINEAR)
    to_xy = lambda la, lo: ((lo - lo0) / (lo1 - lo0) * W, (la1 - la) / (la1 - la0) * H)
    return img, to_xy


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def _label(d, x, y, text, lang, size, color, main):
    f = font(UR if lang == "ur" else SERIF, size)
    s = shape(text) if lang == "ur" else text
    tw = text_w(f, s, lang == "ur", "ur" if lang == "ur" else None)
    tx = x + 26 if x + 26 + tw < W - 30 else x - 26 - tw
    ty = y - size * (0.95 if lang == "ur" else 0.62)
    kw = dict(direction="rtl", language="ur") if lang == "ur" and video.RAQM else {}
    for dx, dy in ((2, 2), (-1, 1), (1, -1), (0, 3)):
        d.text((tx + dx, ty + dy), s, font=f, fill=(0, 0, 0, 200), **kw)
    d.text((tx, ty), s, font=f, fill=color, **kw)


def title_layer(lines, lang):
    """The chapter (or episode) title at the bottom, on a dark gradient, so the map stays visible above it."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    grad = Image.new("L", (1, H))
    for y in range(H):
        grad.putpixel((0, y), int(225 * ease((y - H * 0.42) / (H * 0.5))))
    img.paste((8, 6, 4, 255), (0, 0, W, H), grad.resize((W, H)))
    d = ImageDraw.Draw(img)
    blocks = []
    for text, size, color in lines:
        lg = "ur" if lang == "ur" and not text.isascii() else "en"
        f = font(UR if lg == "ur" else SERIF, size)
        ls = wrap(text, f, W - 300, lg == "ur", "ur" if lg == "ur" else None)
        blocks.append((f, ls, color, lg))
    lh = lambda lg: 1.85 if lg == "ur" else 1.25
    total = sum(len(ls) * f.size * lh(lg) for f, ls, _, lg in blocks)
    y = H - 70 - total
    for f, ls, color, lg in blocks:
        for ln in ls:
            s = shape(ln) if lg == "ur" else ln
            w = text_w(f, s, lg == "ur", "ur" if lg == "ur" else None)
            kw = dict(direction="rtl", language="ur") if lg == "ur" and video.RAQM else {}
            d.text(((W - w) / 2 + 2, y + 2), s, font=f, fill=(0, 0, 0, 220), **kw)
            d.text(((W - w) / 2, y), s, font=f, fill=color, **kw)
            y += f.size * lh(lg)
    cf = font(SERIF, 22)
    d.text((W - text_w(cf, CREDIT, False, None) - 30, 24), CREDIT, font=cf, fill=(255, 255, 255, 170))
    return img


def segment(out, seconds, marks, route, lines, lang, places):
    """A moving-map video segment. marks: [(lat, lon, name, main?)], route: [(lat, lon), (lat, lon)] or None."""
    pts = [(m[0], m[1]) for m in marks if m[3]] or [(23.5, 39.5)]
    end = view_for(pts + (list(route) if route else []))
    start = clamp(end[0], end[1], end[2] * 2.6)
    title = title_layer(lines, lang)
    n = int(round(seconds * FPS))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-framerate",
           str(FPS), "-i", "-", "-vf", "fade=t=in:st=0:d=0.35,fade=t=out:st=%.3f:d=0.35,format=yuv420p" % max(0, seconds - 0.35),
           "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-t", f"{seconds:.3f}", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        t = i / FPS
        z = ease(t / (seconds * 0.55))
        v = (start[0] + (end[0] - start[0]) * z, start[1] + (end[1] - start[1]) * z,
             math.exp(math.log(start[2]) + (math.log(end[2]) - math.log(start[2])) * z))
        img, xy = frame_of(v)
        img = img.convert("RGBA")
        over = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(over)
        if route:
            a, b = xy(*route[0]), xy(*route[1])
            bend = 0.15 * math.dist(a, b)
            path = [(a[0] + (b[0] - a[0]) * s + bend * math.sin(math.pi * s), a[1] + (b[1] - a[1]) * s)
                    for s in [j / 60 for j in range(61)]]
            prog = ease((t - seconds * 0.35) / (seconds * 0.45))
            upto = int(prog * 60)
            for j in range(0, upto, 2):                                # dark edge, then the crimson dashes
                d.line([path[j], path[min(j + 1, upto)]], fill=(20, 10, 6, 200), width=15)
            for j in range(0, upto, 2):
                d.line([path[j], path[min(j + 1, upto)]], fill=(*CRIMSON, 255), width=10)
            if 0 < prog < 1:                                           # the moving head of the journey
                hx, hy = path[upto]
                for r, al in ((22, 60), (14, 120), (8, 255)):
                    d.ellipse([hx - r, hy - r, hx + r, hy + r], fill=(255, 226, 150, al))
        show = ease((t - seconds * 0.15) / 0.8)
        for la, lo, name, main in marks:
            x, y = xy(la, lo)
            if not (0 < x < W and 0 < y < H):
                continue
            r = 13 if main else 7
            pulse = 1 + (0.35 * (1 + math.sin(t * 4)) if main else 0)
            if main:
                d.ellipse([x - r * 2 * pulse, y - r * 2 * pulse, x + r * 2 * pulse, y + r * 2 * pulse],
                          outline=(*GOLD, int(150 * show)), width=3)
            d.ellipse([x - r, y - r, x + r, y + r], fill=(*(CRIMSON if main else (240, 236, 224)), int(255 * show)),
                      outline=(20, 14, 10, int(255 * show)), width=3)
            if show > 0.05:
                _label(d, x, y, name, lang, 46 if main else 34, (255, 246, 222, int(255 * show)) if main else
                       (232, 226, 210, int(230 * show)), main)
        img.alpha_composite(over)
        tl = ease((t - seconds * 0.25) / 0.9)
        if tl > 0:
            lay = title if tl >= 1 else Image.blend(Image.new("RGBA", (W, H), (0, 0, 0, 0)), title, tl)
            img.alpha_composite(lay)
        p.stdin.write(img.convert("RGB").tobytes())
    p.stdin.close()
    if p.wait():
        raise RuntimeError("ffmpeg failed on the moving map")
    return out
