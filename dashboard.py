"""Everything the admin dashboard shows besides the switches: health of the servers, the YouTube auto-poster,
the domain, the data on disk, and the usage counts (stats.py) and Cloudflare numbers (cloudflare_stats.py)."""
import json
import re
import shutil
import subprocess
import threading
import time
from datetime import date

import requests

import cloudflare_stats
import guidance
import seo
import stats
from config import DATA, ROOT, STATE_FILE

STARTED = time.time()
DOMAIN = "quranreelmaker.xyz"
DOMAIN_EXPIRES = date(2027, 10, 7)          # GoDaddy; auto-renew is off
BACKUP_URL = "https://quran-reel-maker.onrender.com"
_cache, _lock = {}, threading.Lock()


def _cached(key, seconds, fn):
    with _lock:
        hit = _cache.get(key)
        if hit and time.time() - hit[0] < seconds:
            return hit[1]
    val = fn()
    with _lock:
        _cache[key] = (time.time(), val)
    return val


def _check(url, headers=None):
    t = time.time()
    try:
        r = requests.get(url, timeout=8, headers=headers or {})
        return {"ok": r.ok, "ms": int((time.time() - t) * 1000), "by": r.headers.get("X-Served-By", "")}
    except requests.RequestException:
        return {"ok": False, "ms": None, "by": ""}


def servers():
    def run():
        tunnel = None
        try:
            tunnel = requests.get("http://127.0.0.1:20241/ready", timeout=3).json().get("readyConnections", 0)
        except (requests.RequestException, ValueError):
            pass
        return {"tunnel": tunnel, "public": _check(f"https://{DOMAIN}/robots.txt"),
                "backup": _check(f"{BACKUP_URL}/robots.txt", {"X-Visitor-IP": "admin-check"})}
    return _cached("servers", 60, run)


def youtube():
    state = {}
    try:
        state = json.loads(STATE_FILE.read_text())
    except (FileNotFoundError, ValueError):
        pass
    wf = ROOT / ".github" / "workflows" / "post.yml"
    text = wf.read_text() if wf.exists() else ""
    paused = bool(re.search(r"^\s*#\s*schedule:", text, re.M)) or "schedule:" not in text
    qari = sorted(p.name for p in (ROOT / "recitations").glob("*") if p.is_dir()) if (ROOT / "recitations").exists() else []
    return {"videos": state.get("videos", 0), "next_index": state.get("next_index", 0), "paused": paused, "qari": qari}


def system():
    du = shutil.disk_usage(ROOT)
    try:
        commit = subprocess.run(["git", "-C", str(ROOT), "log", "-1", "--format=%h · %cr · %s"],
                                capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        commit = ""
    ks = sum(1 for _ in (DATA / "audio").glob("ks.bolbosh_*.mp3")) if (DATA / "audio").exists() else 0
    return {"disk_free_gb": round(du.free / 1e9, 1), "disk_pct": round(du.used / du.total * 100),
            "uptime_h": round((time.time() - STARTED) / 3600, 1), "commit": commit, "kashmiri_audio": ks,
            "domain_days": (DOMAIN_EXPIRES - date.today()).days, "domain_expires": DOMAIN_EXPIRES.isoformat()}


def _pts(values, width, height, pad=6):
    top = max(values) if values and max(values) > 0 else 1
    step = width / max(len(values) - 1, 1)
    return [(i * step, height - pad - v / top * (height - 2 * pad)) for i, v in enumerate(values)], top


def area(series, labels, width=640, height=200):
    """A smooth server-drawn area chart (SVG): series = [(name, values, css class)], first one filled."""
    if not labels:
        return ""
    top = max([max(v) for _, v, _ in series if v] + [1])
    grid = "".join(f'<line x1="0" x2="{width}" y1="{height - 6 - f * (height - 12):.1f}" y2="{height - 6 - f * (height - 12):.1f}"/>'
                   for f in (0.25, 0.5, 0.75, 1))
    paths = []
    for k, (name, values, cls) in enumerate(series):
        step = width / max(len(values) - 1, 1)
        pts = [(i * step, height - 6 - v / top * (height - 12)) for i, v in enumerate(values)]
        line = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        if k == 0:
            paths.append(f'<path class="fill" d="{line} L{width},{height} L0,{height} Z"/>')
        paths.append(f'<path class="{cls}" d="{line}"/>')
        paths += [f'<circle class="{cls}" cx="{x:.1f}" cy="{y:.1f}" r="3"><title>{labels[i]}: {values[i]} {name}</title></circle>'
                  for i, (x, y) in enumerate(pts)]
    ticks = "".join(f'<span style="left:{i / max(len(labels) - 1, 1) * 100:.1f}%">{labels[i][5:]}</span>'
                    for i in sorted({0, len(labels) // 3, 2 * len(labels) // 3, len(labels) - 1}))
    return (f'<div class="area"><span class="ymax">{top:,}</span><svg viewBox="0 0 {width} {height}" preserveAspectRatio="none">'
            f'<defs><linearGradient id="g" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#34d399" stop-opacity=".35"/>'
            f'<stop offset="1" stop-color="#34d399" stop-opacity="0"/></linearGradient></defs><g class="grid">{grid}</g>'
            f'{"".join(paths)}</svg><div class="xt">{ticks}</div></div>')


def spark(values, width=120, height=34):
    if not values:
        return ""
    pts, _ = _pts(values, width, height, 3)
    line = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return f'<svg class="spark" viewBox="0 0 {width} {height}" preserveAspectRatio="none"><path d="{line}"/></svg>'


def bars(values, width=560, height=90):
    return spark(values, width, height)


def delta(today, yesterday):
    if not yesterday:
        return None if not today else "new"
    return round((today - yesterday) / yesterday * 100)


def collect():
    s = stats.summary(30)
    days = [d for d, _ in s["per_day"]]
    views = [c.get("page", 0) for _, c in s["per_day"]]
    reels = [c.get("reel_cloud", 0) + c.get("reel_device", 0) for _, c in s["per_day"]]
    cf = cloudflare_stats.stats()
    from translations import LANGS
    s["surahs"] = [(f"{n}. {seo.BY_NUMBER[int(n)]['englishName']}" if n.isdigit() and int(n) in seo.BY_NUMBER else n, c)
                   for n, c in s["surahs"]]
    s["langs"] = [(LANGS.get(k, {}).get("name", k), c) for k, c in s["langs"]]
    s["topics"] = [("Full search" if k == "search" else guidance.BY_ID[k]["en"] if k in guidance.BY_ID else k, c)
                   for k, c in s["topics"]]
    asks = [c.get("ask", 0) for _, c in s["per_day"]]
    yday = s["per_day"][-2][1] if len(s["per_day"]) > 1 else {}
    reel = lambda c: c.get("reel_cloud", 0) + c.get("reel_device", 0)
    sv = servers()
    cf_days = cf["days"] if cf and cf.get("days") else []
    return {"stats": s, "days": days,
            "traffic_chart": area([("page views", views, "l1"), ("reels", reels, "l2")], days),
            "spark_views": spark(views[-14:]), "spark_reels": spark(reels[-14:]), "spark_asks": spark(asks[-14:]),
            "spark_cf": spark([x["visitors"] for x in cf_days[-14:]]),
            "d_views": delta(s["today"].get("page", 0), yday.get("page", 0)),
            "d_reels": delta(reel(s["today"]), reel(yday)),
            "cf": cf, "cf_configured": cloudflare_stats.configured(),
            "cf_chart": area([("visitors", [x["visitors"] for x in cf_days], "l1")], [x["date"] for x in cf_days]) if cf_days else "",
            "healthy": bool(sv["public"]["ok"] and sv["backup"]["ok"]),
            "servers": sv, "youtube": youtube(), "system": system(), "now": time.strftime("%A, %d %B %Y · %H:%M")}
