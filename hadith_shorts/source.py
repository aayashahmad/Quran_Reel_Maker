"""Hadith text and references, from the Sahih al-Bukhari and Sahih Muslim editions of fawazahmed0/hadith-api
(data/hadith/{ara,eng}-{bukhari,muslim}.json), each one checked against its sunnah.com page before use.

Nothing is rewritten: the English is the dataset's translation as it is, and the Arabic shown is either the full
narration or the Prophet's ﷺ words cut from it (a contiguous part of the original, marked as an excerpt)."""
import html
import json
import random
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache

import requests

from config import DATA

NAMES = {"bukhari": "Sahih al-Bukhari", "muslim": "Sahih Muslim"}
TRANSLATORS = {"bukhari": "Dr. Muhammad Muhsin Khan", "muslim": "Abdul Hamid Siddiqui"}
DATASET = "fawazahmed0/hadith-api (github.com/fawazahmed0/hadith-api)"
# books used for the automatic daily choice: faith, knowledge, character, worship and the heart, not legal
# details that need a teacher's context (any reference can still be made by hand with --ref)
GOOD_BOOKS = {"bukhari": {2, 3, 24, 30, 46, 51, 53, 66, 69, 75, 78, 80, 81, 82, 96, 97},
              "muslim": {1, 12, 45, 47, 48, 49, 53, 55}}
SAW = "صلى الله عليه وسلم"
MAX_EN_WORDS, MAX_AR_WORDS = 95, 70


class SourceError(Exception):
    pass


@dataclass
class Hadith:
    collection: str
    number: int                  # the dataset's number
    display_number: str          # the usual citation number (as sunnah.com shows it)
    url: str
    book: str
    arabic_full: str
    arabic: str                  # what the video shows
    arabic_is_excerpt: bool
    english: str
    narrator: str
    translator: str
    source: str = DATASET
    checks: list = field(default_factory=list)

    @property
    def ref(self):
        return f"{self.collection}:{self.number}"

    @property
    def citation(self):
        return f"{NAMES[self.collection]} {self.display_number}"


def plain(text):
    """Arabic without vowel marks, for comparing texts."""
    text = re.sub(r"[\u200e\u200f\"]", "", text)
    return re.sub(r"\s+", " ", "".join(c for c in unicodedata.normalize("NFC", text)
                                       if not unicodedata.category(c).startswith("M"))).strip()


@lru_cache(maxsize=8)
def _edition(col, lang):
    f = DATA / "hadith" / f"{lang}-{col}.json"
    if not f.exists():
        raise SourceError(f"{f} is missing: download it from {DATASET} (editions/{lang}-{col}.json)")
    d = json.loads(f.read_text(encoding="utf-8"))
    return {h["hadithnumber"]: h for h in d["hadiths"]}, d["metadata"]


def arabic_excerpt(text):
    """The Prophet's ﷺ words from a full narration: the quoted part after the last 'peace be upon him' that
    opens a quote. None when there is no clear quote (the full narration is then used, if it is short)."""
    marks = "[\u064B-\u065F\u0670]*"                   # vowel marks may sit in any order between letters
    found = list(re.finditer(marks.join("وسلم"), text))
    if not found:
        return None
    rest = text[found[-1].end():]
    q = rest.find('"')
    if q < 0:
        return None
    part = re.sub(r"[\u200e\u200f]", "", rest[q + 1:])          # invisible direction marks
    part = re.sub(r'["\s.]+$', "", part).strip().strip('"').strip(" ،,")
    return part if 3 <= len(part.split()) <= MAX_AR_WORDS else None


def narrator_of(english):
    m = re.match(r"\s*(?:Narrated\s+)?([^:]{3,80}?)\s*(?::|\breported\b|\bnarrated\b)", english)
    return m.group(1).strip(" '`") if m else ""


def get(ref):
    """The hadith for a reference such as 'bukhari:1' or 'muslim:5218', straight from the data."""
    try:
        col, num = ref.split(":")
        num = int(num)
    except ValueError:
        raise SourceError(f"bad reference {ref!r}: use collection:number, e.g. bukhari:1")
    if col not in NAMES:
        raise SourceError(f"unknown collection {col!r}: only {', '.join(NAMES)}")
    en_all, meta = _edition(col, "eng")
    ar_all, _ = _edition(col, "ara")
    en, ar = en_all.get(num), ar_all.get(num)
    if not en or not ar or not en["text"].strip() or not ar["text"].strip():
        raise SourceError(f"{ref}: no English or Arabic text in the data")
    book_no = (en.get("reference") or {}).get("book")
    book = meta["sections"].get(str(book_no), "").strip()
    if col == "bukhari":
        display, url = str(num), f"https://sunnah.com/bukhari:{num}"
    else:
        r = en.get("reference") or {}
        display = str(en.get("arabicnumber") or ar.get("arabicnumber") or num).split(".")[0]
        url = f"https://sunnah.com/muslim/{r.get('book')}/{r.get('hadith')}"
    full = ar["text"].strip()
    excerpt = arabic_excerpt(full)
    english = re.sub(r"\s+", " ", en["text"]).strip()
    return Hadith(col, num, display, url, book, full, excerpt or full, bool(excerpt), english,
                  narrator_of(english), TRANSLATORS[col])


def eligible(h):
    """Short enough for a Short, with a clear Arabic quote, from a general-audience book."""
    _, meta = _edition(h.collection, "eng")
    en_all, _ = _edition(h.collection, "eng")
    book_no = (en_all[h.number].get("reference") or {}).get("book")
    return (book_no in GOOD_BOOKS[h.collection] and 18 <= len(h.english.split()) <= MAX_EN_WORDS
            and h.arabic_is_excerpt and "(See" not in h.english)


def candidates(collections, seed=1446):
    """Every eligible reference, in a fixed shuffled order (the same order on every run)."""
    refs = []
    for col in collections:
        en_all, _ = _edition(col, "eng")
        for num in sorted(en_all):
            try:
                if eligible(get(f"{col}:{num}")):
                    refs.append(f"{col}:{num}")
            except SourceError:
                continue
    random.Random(seed).shuffle(refs)
    return refs


def verify(h, session=None):
    """Open the hadith's sunnah.com page and check it is the same narration: the citation number and several
    words of the English and the Arabic must be there. Returns (ok, detail)."""
    s = session or requests
    try:
        r = s.get(h.url, headers={"User-Agent": "Mozilla/5.0 (QuranReelMaker reference check)"}, timeout=30)
    except requests.RequestException as e:
        return False, f"could not open {h.url}: {e.__class__.__name__}"
    if r.status_code != 200:
        return False, f"{h.url} answered {r.status_code}"
    page = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", r.text)))
    m = re.search(rf"{re.escape(NAMES[h.collection])}\s+(\d+)[a-z]?", page)
    if not m or m.group(1) != h.display_number:
        return False, f"{h.url} shows {m.group(0) if m else 'no number'}, expected {h.citation}"
    en_words = [w.lower() for w in re.findall(r"[A-Za-z]{5,}", h.english)][3:11]
    en_hits = sum(w in page.lower() for w in en_words)
    ar_words = [w for w in plain(h.arabic).split() if len(w) >= 4][:8]
    ar_page = plain(page)
    ar_hits = sum(w in ar_page for w in ar_words)
    if en_hits < max(3, len(en_words) - 3) or ar_hits < max(3, len(ar_words) - 3):
        return False, f"{h.url}: text does not match (English {en_hits}/{len(en_words)}, Arabic {ar_hits}/{len(ar_words)})"
    return True, f"{h.url} matches {h.citation} (English {en_hits}/{len(en_words)}, Arabic {ar_hits}/{len(ar_words)})"
