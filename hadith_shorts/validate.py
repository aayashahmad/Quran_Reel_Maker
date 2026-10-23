"""Checks before anything is published: the hadith text against its source, Arabic shaping, and the finished
video's size, length, codecs and audio level. Each returns a list of problems (empty = passed)."""
import json
import re
import subprocess

from PIL import features

from hadith_shorts import settings, source


def content(h, lang="en"):
    problems = []
    if lang == "ur":
        squash = lambda t: re.sub(r"[\s\"“”’‘]", "", t)
        if not h.urdu:
            problems.append("no clear Urdu text of the Prophet's words")
        elif squash(h.urdu) not in squash(h.urdu_full):
            problems.append("the Urdu shown is not part of the source translation")
    if source.plain(h.arabic) not in source.plain(h.arabic_full):
        problems.append("the Arabic shown is not part of the source narration")
    for name in ("english", "arabic", "url", "display_number", "translator"):
        if not getattr(h, name):
            problems.append(f"missing {name}")
    if not re.match(r"https://sunnah\.com/", h.url):
        problems.append(f"source link is not sunnah.com: {h.url}")
    return problems


def arabic_shaping():
    """Arabic needs libraqm for joined letters and correct vowel marks."""
    return [] if features.check("raqm") else ["libraqm is not available: Arabic would not be shaped correctly"]


def media(path, max_seconds=None):
    problems = []
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_type,codec_name,width,height:format=duration", "-of", "json", str(path)],
                       capture_output=True, text=True)
    try:
        info = json.loads(r.stdout)
    except ValueError:
        return [f"cannot read {path}"]
    streams = info.get("streams", [])
    v = next((s for s in streams if s["codec_type"] == "video"), None)
    a = next((s for s in streams if s["codec_type"] == "audio"), None)
    dur = float(info.get("format", {}).get("duration", 0))
    if not v or v.get("codec_name") != "h264":
        problems.append("no H.264 video stream")
    elif (v["width"], v["height"]) != (settings.VIDEO_WIDTH, settings.VIDEO_HEIGHT):
        problems.append(f"size is {v['width']}x{v['height']}")
    if not a or a.get("codec_name") != "aac":
        problems.append("no AAC audio stream")
    if not 8 <= dur <= (max_seconds or settings.VIDEO_MAX_SECONDS):
        problems.append(f"duration {dur:.1f}s is out of range")
    if a:
        vol = subprocess.run(["ffmpeg", "-i", str(path), "-af", "volumedetect", "-vn", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
        m = re.search(r"max_volume: (-?[\d.]+) dB", vol)
        if not m or float(m.group(1)) < -30:
            problems.append("the narration is silent or far too quiet")
    return problems
