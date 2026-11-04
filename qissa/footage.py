"""Real moving footage for scene backgrounds, from Pexels (free to use, no attribution required; we credit anyway).
Needs a free API key in PEXELS_API_KEY (pexels.com/api). Clips are cached in data/footage/. Without a key, or
if nothing suitable is found, the scene falls back to its drawn paper art.

Only nature, sea, sky, boats, towns and objects are searched, never people; the queries below avoid subjects that
would show faces, and a story can override a scene's query with "footage": "<words>"."""
import json
import os
import re
from pathlib import Path

import requests

from config import DATA

DIR = DATA / "footage"
QUERIES = {   # art name -> what to search for (people-free subjects)
    "sea-night": "ocean waves at night",
    "ship": "old wooden sailing boat at sea",
    "fish": "whale underwater ocean",
    "darkness": "deep dark ocean underwater",
    "dawn": "sunrise over calm sea",
    "shore": "empty sandy beach waves",
    "town-dusk": "old city rooftops at night",
    "town-dawn": "ancient town sunrise aerial",
    "desert": "desert sand dunes wind",
    "sky": "clouds moving sky timelapse",
    "rain": "rain drops leaves",
    "garden": "green garden plants sunlight",
    "fire": "fire flames dark",
    "mountain": "mountains fog",
    "cave": "dark cave entrance light",
    "night": "starry night sky timelapse",
}

# words in a text -> footage that shows them (people-free); the first matches in the text pick the clips, so every
# video gets pictures of what its own words are about
WORDS = [
    (r"\b(sea|ocean|waves?)\b", "ocean waves"), (r"\b(rain|rains|raining)\b", "rain drops leaves"),
    (r"\bwater|\b(a|the) well\b|\briver|\bspring\b|thirst", "clear water flowing stream"), (r"\bfire\b|flames?\b|\bhell\b", "fire flames dark"),
    (r"paradise|jannah|garden|gardens", "lush green garden waterfall"), (r"\bdates?\b|palm", "date palm trees"),
    (r"\bcamels?\b", "camels desert"), (r"desert|\bsand\b", "desert sand dunes wind"), (r"\bsheep\b|goats?\b|flock", "sheep grazing field"),
    (r"\bbirds?\b", "birds flying sky"), (r"\bants?\b", "ants macro"), (r"\bfish\b|whale", "whale underwater ocean"),
    (r"\bships?\b|\bboats?\b|\bark\b", "old wooden sailing boat at sea"), (r"mountains?|\bhills?\b", "mountains fog"),
    (r"\bcave\b", "dark cave entrance light"), (r"\bmoon\b", "full moon night clouds"), (r"\bsun\b|sunrise|dawn|fajr", "sunrise over hills"),
    (r"\bstars?\b", "starry night sky timelapse"), (r"\bnight\b|tahajjud", "night sky timelapse"), (r"\bsky\b|heavens?\b", "clouds moving sky timelapse"),
    (r"\btrees?\b|\bplants?\b|\bseeds?\b|harvest|crops?", "green field wind"), (r"\bfruits?\b", "fresh fruit tree branch"),
    (r"mosque|masjid|prayer|pray\b|prostrat|ablution|wudu", "mosque architecture"), (r"qur'?an|recit", "open book pages light"),
    (r"knowledge|learn|teach|scholar", "old books library"), (r"\bfood\b|\bfeed|hungry|\bbread\b|meal", "bread on wooden table"),
    (r"\bneighbou?rs?\b|\bhouses?\b|\bhomes?\b", "old town street houses"), (r"guests?\b|hospitality", "tea pouring cup"),
    (r"charity|sadaqa|\bspend|\bpoor\b|needy|\bgold\b|silver|wealth|money", "coins on table"),
    (r"\bgraves?\b|\bdeath\b|\bdie\b|\bdied\b", "autumn leaves falling"), (r"\bmarket|\btrade|\bbuy\b|\bsell\b", "old market spices"),
    (r"\bjourney|travel|\broad\b|\bpath\b", "empty road landscape"), (r"\bheart|intention|sincer", "candle light dark"),
    (r"\blight\b|\blamps?\b", "lantern light night"), (r"\bwind\b", "wind grass field"), (r"\btongue|\bspeak|\bspeech|\bwords?\b", "calm lake reflection"),
    (r"\bmilk\b", "milk pouring glass"), (r"\bhoney\b", "honey dripping"), (r"\bmothers?\b|\bfathers?\b|parents", "warm sunset field"),
]


def queries_for(text):
    """The footage queries for the things this text talks about, in the order it first mentions them."""
    low = (text or "").lower()
    hits = sorted((m.start(), q) for rx, q in WORDS for m in [re.search(rx, low)] if m)
    out = []
    for _, q in hits:
        if q not in out:
            out.append(q)
    return out


def _slug(q):
    return re.sub(r"[^a-z0-9]+", "-", q.lower()).strip("-")


def clip(query, seed=0):
    """(path, credit) of a portrait clip for this query, or (None, None)."""
    key = os.getenv("PEXELS_API_KEY")
    DIR.mkdir(parents=True, exist_ok=True)
    out = DIR / f"{_slug(query)}-{seed}.mp4"
    meta = out.with_suffix(".json")
    if out.exists() and meta.exists():
        return out, json.loads(meta.read_text())
    if not key:
        return None, None
    try:
        r = requests.get("https://api.pexels.com/videos/search", headers={"Authorization": key}, timeout=30,
                         params={"query": query, "orientation": "portrait", "size": "medium", "per_page": 15})
        r.raise_for_status()
        videos = [v for v in r.json().get("videos", []) if v.get("duration", 0) >= 7]
        if not videos:
            return None, None
        v = videos[seed % len(videos)]
        files = [f for f in v["video_files"] if f.get("width") and f.get("height") and f["height"] > f["width"]
                 and 700 <= f["width"] <= 1440 and f.get("file_type") == "video/mp4"]
        if not files:
            return None, None
        f = min(files, key=lambda f: abs(f["width"] - 1080))
        data = requests.get(f["link"], timeout=120)
        data.raise_for_status()
        tmp = out.with_suffix(".part")
        tmp.write_bytes(data.content)
        import subprocess
        ok = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name",
                             "-of", "csv=p=0", str(tmp)], capture_output=True, text=True).stdout.strip()
        if not ok:                                       # not a playable video: don't keep it
            tmp.unlink(missing_ok=True)
            return None, None
        tmp.replace(out)
        credit = {"by": v.get("user", {}).get("name", ""), "url": v.get("url", ""), "source": "Pexels"}
        meta.write_text(json.dumps(credit))
        return out, credit
    except (requests.RequestException, ValueError, KeyError):
        return None, None


def for_scene(scene, index):
    """The scene's own "footage" query, else what its narration talks about, else the default for its art."""
    if scene.get("art") == "paper":
        return None, None
    words = queries_for(scene.get("say", {}).get("en", ""))
    query = scene.get("footage") or (words[0] if words else None) or QUERIES.get(scene.get("art"))
    if not query:
        return None, None
    return clip(query, index % 3)
