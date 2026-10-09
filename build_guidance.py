"""Check the "Ask the Quran" library and write guidance.json for the website.

  python build_guidance.py

- every ayah reference must exist in the Quran data
- every hadith must exist in the Sahih al-Bukhari / Sahih Muslim editions (data/hadith/, from
  github.com/fawazahmed0/hadith-api, public domain); its English and Urdu text are copied in
- every hadith's sunnah.com page is opened: the link must work and show the same narration, and the
  number printed there (e.g. "Sahih Muslim 2999") is the one the site shows
Anything that fails stops the build."""
import html
import json
import re
import sys
import time

import requests

from config import DATA
from guidance_topics import TOPICS
from quran_data import load_quran, surah_ranges

NAMES = {"bukhari": "Sahih al-Bukhari", "muslim": "Sahih Muslim"}
OUT = "guidance.json"


def load_hadith():
    out = {}
    for col in NAMES:
        for lang in ("eng", "urd"):
            d = json.loads((DATA / "hadith" / f"{lang}-{col}.json").read_text(encoding="utf-8"))
            out[(col, lang)] = {h["hadithnumber"]: h for h in d["hadiths"]}
    return out


def sunnah_page(col, h):
    ref = h["reference"]
    if col == "bukhari" or not ref.get("book"):
        url = f"https://sunnah.com/bukhari:{h['hadithnumber']}"
    else:
        url = f"https://sunnah.com/{col}/{ref['book']}/{ref['hadith']}"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (QuranReelMaker reference check)"}, timeout=30)
    r.raise_for_status()
    page = html.unescape(re.sub(r"<[^>]+>", " ", r.text))
    m = re.search(rf"{re.escape(NAMES[col])}\s+(\d+[a-z]?)", page)
    return r.url, (m.group(1) if m else None), re.sub(r"\s+", " ", page)


def words(text, n=6):
    """A few distinctive words from the narration, to find it on the sunnah.com page."""
    w = re.findall(r"[A-Za-z]{5,}", text)
    return [x.lower() for x in w[3:3 + n]]


def tidy(text):
    """Drop the source's dangling cross-references such as '(See Hadith No)' and stray spaces."""
    text = re.sub(r"\s*\(See (Hadith )?No\.?\s*[\d, ]*\)", "", text)
    return re.sub(r"\s+", " ", text).strip()


def main():
    quran = load_quran()
    ranges = surah_ranges(quran)
    hadith = load_hadith()
    out, problems, cache = [], [], {}
    for t in TOPICS:
        ayat = []
        for ref in t["ayat"]:
            s, a = ref.split(":")
            first, last = (int(x) for x in (a.split("-") if "-" in a else (a, a)))
            s = int(s)
            if s not in ranges or not 1 <= first <= last <= ranges[s][1] - ranges[s][0]:
                problems.append(f"{t['id']}: ayah {ref} does not exist")
            ayat.append({"surah": s, "from": first, "to": last})
        hs = []
        for col, num in t["hadith"]:
            h, hu = hadith[(col, "eng")].get(num), hadith[(col, "urd")].get(num)
            if not h or not h["text"].strip():
                problems.append(f"{t['id']}: {col} {num} not found")
                continue
            key = (col, num)
            if key not in cache:
                url, shown, page = sunnah_page(col, h)
                hits = sum(w in page.lower() for w in words(h["text"]))
                if not shown or hits < 4:
                    problems.append(f"{t['id']}: {col} {num}: sunnah.com page {url} does not match ({shown}, {hits}/6 words)")
                cache[key] = (url, shown)
                time.sleep(1)                       # be polite to sunnah.com
            url, shown = cache[key]
            hs.append({"collection": NAMES[col], "number": shown, "url": url,
                       "en": tidy(h["text"]), "ur": tidy((hu or {}).get("text", ""))})
            print(f"  {t['id']:11} {NAMES[col]} {shown}  {url}")
        out.append({k: t[k] for k in ("id", "en", "ur", "guide_en", "guide_ur")} |
                   {"crisis": t.get("crisis", False), "words": t["words"], "ayat": ayat, "hadith": hs})
    if problems:
        print("\nProblems:\n  " + "\n  ".join(problems))
        sys.exit(1)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\n{len(out)} topics, {sum(len(t['ayat']) for t in out)} ayah passages, "
          f"{sum(len(t['hadith']) for t in out)} hadith: all checked, written to {OUT}")


if __name__ == "__main__":
    main()
