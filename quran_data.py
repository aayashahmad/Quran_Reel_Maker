import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

import requests

from config import DATA, RECITATION_ID, URDU_EDITION

API = "https://api.alquran.cloud/v1/quran/{}"
AUDIO = "https://cdn.islamic.network/quran/audio/{}/{}/{}.mp3"
QDC = ("https://api.quran.com/api/v4/verses/by_chapter/{}?words=true&word_fields=text_uthmani"
       "&audio={}&per_page=50&page={}")
QDC_AUDIO = "https://verses.quran.com/{}"
BITRATE = {"ur.khan": 64, "en.walk": 192}  # other editions use 128
# recordings made on this computer rather than downloaded (data/audio/<edition>_<n>.mp3), e.g. the
# Kashmiri Bolbosh voice from ~/kashmiri-voice/make_kashmiri_audio.py; served at /api/audio/
LOCAL_AUDIO = {"ks.bolbosh"}


def local_audio_complete(edition):
    """True when every ayah of a local recording edition exists."""
    return sum(1 for _ in (DATA / "audio").glob(f"{edition}_*.mp3")) >= 6236
BISMILLAH = "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ"


def _get(url, tries=4):
    for i in range(tries):
        try:
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            return r
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(3 * (i + 1))


def _qdc_chapter(ch):
    """Quran.com words (Uthmani), word timings and audio file for every ayah of a surah."""
    out, page = {}, 1
    while page:
        d = _get(QDC.format(ch, RECITATION_ID, page)).json()
        for v in d["verses"]:
            words = [w["text_uthmani"] for w in v["words"] if w["char_type_name"] == "word"]
            # segments: [word position (1-based), start ms, end ms] within the ayah's audio file
            segs = [s[-3:] for s in (v.get("audio") or {}).get("segments") or [] if len(s) >= 3]
            out[v["verse_key"]] = {"words": words, "segments": segs, "audio_url": v["audio"]["url"]}
        page = d["pagination"]["next_page"]
    return out


def load_quran():
    """Returns list of 6236 ayat dicts in Quran order. Cached in data/quran_v3.json.

    Arabic text is Quran.com's Uthmani word list (`words`), so that its word timings
    (`segments`) line up with each word for highlighting.

    The source text joins Bismillah onto ayah 1 of every surah except 1 and 9, but
    Bismillah is not counted as that ayah and its recitation audio does not include it.
    So it is removed from the ayah text and `bismillah` is set; reels show it as its own
    frame instead. Al-Fatiha 1:1 stays as is (there it is the first ayah)."""
    DATA.mkdir(exist_ok=True)
    cache = DATA / "quran_v3.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))

    ar = _get(API.format("quran-uthmani")).json()["data"]["surahs"]
    ur = _get(API.format(URDU_EDITION)).json()["data"]["surahs"]
    ur_by_num = {a["number"]: a["text"] for s in ur for a in s["ayahs"]}
    with ThreadPoolExecutor(6) as ex:
        qdc = {}
        for part in ex.map(_qdc_chapter, range(1, 115)):
            qdc.update(part)

    out = []
    for s in ar:
        for a in s["ayahs"]:
            text = a["text"].replace("\ufeff", "").strip()
            bism = s["number"] not in (1, 9) and a["numberInSurah"] == 1
            if bism:
                words = text.split()
                assert "سْمِ" in words[0] and words[3].endswith("حِيمِ"), (s["number"], text)
                text = " ".join(words[4:])
            q = qdc[f"{s['number']}:{a['numberInSurah']}"]
            out.append({
                "n": a["number"],                    # global ayah number 1..6236
                "surah": s["number"],
                "surah_ar": s["name"],
                "surah_en": s["englishName"],
                "ayah": a["numberInSurah"],
                "ar": " ".join(q["words"]),
                "words": q["words"],
                "segments": q["segments"],
                "audio_url": q["audio_url"],
                "ur": ur_by_num[a["number"]].replace("\ufeff", "").strip(),
                "bismillah": bism,
                "ruku": a["ruku"],
                "sajda": bool(a["sajda"]),
            })
    cache.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return out


def surah_ranges(quran):
    """{surah number: (start index, end index exclusive)} into the ayat list."""
    r = {}
    for i, a in enumerate(quran):
        s = a["surah"]
        r[s] = (r[s][0], i + 1) if s in r else (i, i + 1)
    return r


def audio_url(item, edition=None):
    """Where the Arabic recitation (edition None) or a translation audio edition of an ayah is online."""
    if edition is None:
        return QDC_AUDIO.format(item["audio_url"])
    if edition in LOCAL_AUDIO:
        return f"/api/audio/{edition}/{item['n']}"
    return AUDIO.format(BITRATE.get(edition, 128), edition, item["n"])


def get_audio(item, edition=None):
    """Arabic recitation (edition None, from Quran.com) or a translation audio edition, downloaded once."""
    d = DATA / "audio"
    d.mkdir(parents=True, exist_ok=True)
    name = f"qdc{RECITATION_ID}" if edition is None else edition
    f = d / f"{name}_{item['n']}.mp3"
    url = audio_url(item, edition)
    if not f.exists() and edition in LOCAL_AUDIO:
        raise FileNotFoundError(f"{f.name} has not been made yet")
    if not f.exists():
        tmp = f.with_suffix(".part")     # never leave a half-downloaded file behind
        tmp.write_bytes(_get(url).content)
        tmp.replace(f)
    return f


def duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True)
    return float(r.stdout.strip())
