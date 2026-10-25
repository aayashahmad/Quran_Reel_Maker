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
        tmp.replace(out)
        credit = {"by": v.get("user", {}).get("name", ""), "url": v.get("url", ""), "source": "Pexels"}
        meta.write_text(json.dumps(credit))
        return out, credit
    except (requests.RequestException, ValueError, KeyError):
        return None, None


def for_scene(scene, index):
    query = scene.get("footage") or QUERIES.get(scene.get("art"))
    if not query or scene.get("art") == "paper":
        return None, None
    return clip(query, index % 3)
