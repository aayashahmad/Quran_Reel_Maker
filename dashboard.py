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


def bars(values, width=560, height=90):
    """A tiny server-drawn bar chart (SVG) for the dashboard, no JavaScript needed."""
    top = max(values) if values and max(values) > 0 else 1
    n = max(len(values), 1)
    w = width / n
    rects = "".join(
        f'<rect x="{i * w + 1:.1f}" y="{height - v / top * (height - 4):.1f}" width="{max(w - 2, 1):.1f}" '
        f'height="{v / top * (height - 4):.1f}" rx="2"><title>{v}</title></rect>' for i, v in enumerate(values))
    return f'<svg viewBox="0 0 {width} {height}" class="bars" role="img" aria-label="per day">{rects}</svg>'


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
    return {"stats": s, "days": days, "views_chart": bars(views), "reels_chart": bars(reels),
            "cf": cf, "cf_configured": cloudflare_stats.configured(),
            "cf_chart": bars([d["visitors"] for d in cf["days"]]) if cf and cf["days"] else "",
            "servers": servers(), "youtube": youtube(), "system": system()}
