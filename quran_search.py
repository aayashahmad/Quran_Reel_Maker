"""Ask the Quran, for questions outside the explained topics: search the whole Quran (English and Urdu
translations) and Sahih al-Bukhari and Sahih Muslim (data/hadith/, English and Urdu) for the ayat and hadith
that speak about the question. Nothing is written by AI: the visitor sees only the texts found, with their
references, and a note that these are search results, not a ruling.

The index is a SQLite full-text table in data/search.db, built on first use (about a minute) and kept on disk,
so it costs almost no memory."""
import json
import re
import sqlite3
import threading

from config import DATA
import guidance

DB = DATA / "search.db"
VERSION = "4"
_lock = threading.Lock()

# Roman Urdu (and a few English) words -> the words the English translations use
BRIDGE = {
    "namaz": "prayer", "namaaz": "prayer", "salah": "prayer", "salat": "prayer", "nimaz": "prayer",
    "roza": "fasting", "rozay": "fasting", "roze": "fasting", "rozah": "fasting", "sawm": "fasting",
    "zakat": "zakat", "zakaat": "zakat", "sadqa": "charity", "sadqah": "charity", "sadaqah": "charity", "khairat": "charity",
    "sood": "riba usury interest", "sud": "riba usury interest", "interest": "riba usury interest", "byaj": "riba usury interest",
    "sharab": "wine intoxicants", "alcohol": "wine intoxicants", "nasha": "intoxicants", "drinking": "wine",
    "jua": "gambling", "juwa": "gambling", "satta": "gambling",
    "jhoot": "lie lying", "jhooth": "lie lying", "jhut": "lie lying", "sach": "truth truthful", "sacha": "truthful",
    "chori": "steal theft", "chor": "thief", "zina": "adultery fornication", "parda": "hijab cover",
    "purdah": "hijab cover", "nikah": "marriage marry", "shadi": "marriage marry", "talaq": "divorce",
    "biwi": "wife", "bivi": "wife", "shohar": "husband", "shauhar": "husband", "walidain": "parents",
    "waldain": "parents", "ammi": "mother", "maa": "mother", "abbu": "father", "abu": "father", "baap": "father",
    "beta": "son", "beti": "daughter", "bhai": "brother", "behan": "sister", "bahan": "sister", "padosi": "neighbour",
    "yateem": "orphan", "yatim": "orphan", "ghareeb": "poor", "garib": "poor", "faqeer": "poor", "daulat": "wealth",
    "dolat": "wealth", "paisa": "money wealth", "paise": "money wealth", "ilm": "knowledge", "nabi": "prophet",
    "rasool": "messenger", "rasul": "messenger", "jannat": "paradise", "jannah": "paradise", "jahannam": "hell",
    "dozakh": "hell", "dozak": "hell", "maut": "death", "mout": "death", "qabar": "grave", "qabr": "grave",
    "qayamat": "resurrection hour", "qiyamat": "resurrection hour", "farishte": "angels", "farishta": "angel",
    "shaitan": "satan", "shaytan": "satan", "shetan": "satan", "jinn": "jinn", "jin": "jinn", "dua": "supplication invoke",
    "sabr": "patience patient", "shukar": "grateful thank", "shukr": "grateful thank", "gussa": "anger", "ghussa": "anger",
    "hasad": "envy", "takabbur": "arrogance arrogant", "ghuroor": "arrogance", "tauba": "repent repentance",
    "toba": "repent repentance", "gunah": "sin", "gunaah": "sin", "maafi": "forgive forgiveness", "maaf": "forgive",
    "insaf": "justice", "zulm": "injustice oppression", "qatl": "kill killing", "khana": "food eat", "pani": "water",
    "taharat": "purification", "wuzu": "ablution", "wudu": "ablution", "ghusl": "bath", "masjid": "mosque",
    "jumma": "friday", "juma": "friday", "ramzan": "ramadan", "ramadhan": "ramadan", "qurbani": "sacrifice",
    "dost": "friend", "kutta": "dog", "kuttay": "dogs", "suar": "swine pig", "pork": "swine pig", "khinzeer": "swine",
    "halal": "lawful", "haram": "unlawful forbidden", "gana": "music singing", "gaana": "music singing",
    "music": "music musical", "musiqi": "music musical", "tasveer": "pictures images", "tasvir": "pictures images",
    "darhi": "beard", "dadhi": "beard", "sona": "gold", "resham": "silk", "bimar": "sick illness", "beemar": "sick illness",
    "ilaj": "medicine treatment", "khwab": "dream", "khawab": "dream", "aurat": "woman women", "auraton": "women",
    "mard": "man men", "bache": "children", "bachay": "children", "aulad": "children offspring", "ghar": "house home",
    "safar": "travel journey", "tijarat": "trade", "karobar": "trade business", "qarz": "debt loan", "karz": "debt loan",
    "rizq": "provision", "rozi": "provision", "kaam": "work", "mehnat": "work", "naukri": "work", "doctor": "medicine",
    "imaan": "faith belief", "iman": "faith belief", "kufr": "disbelief", "kafir": "disbeliever", "shirk": "associate partners",
    "bidat": "innovation", "sunnat": "sunnah", "hadees": "hadith", "hadis": "hadith", "zikr": "remembrance",
    "tasbeeh": "glorify", "aakhirat": "hereafter", "akhirat": "hereafter", "duniya": "world", "dunya": "world",
    "insaan": "man mankind", "insan": "man mankind", "janwar": "animals", "sabzi": "vegetables", "doodh": "milk",
    "shahad": "honey", "khajoor": "dates", "neend": "sleep", "sona_": "sleep", "hasna": "laugh", "rona": "weep",
    "pardah": "headcovers veil", "parday": "headcovers veil", "hijab": "hijab veil headcovers",
    "musa": "moses", "moosa": "moses", "isa": "jesus", "eesa": "jesus", "maryam": "mary", "mariam": "mary",
    "ibrahim": "abraham", "ibraheem": "abraham", "nuh": "noah", "nooh": "noah", "yusuf": "joseph", "yousuf": "joseph",
    "dawood": "david", "dawud": "david", "sulaiman": "solomon", "suleman": "solomon", "yunus": "jonah", "younus": "jonah",
    "firaun": "pharaoh", "firon": "pharaoh", "ismail": "ishmael", "ishaq": "isaac", "yaqub": "jacob", "ayub": "job",
    "haroon": "aaron", "harun": "aaron", "loot": "lot", "zakariya": "zechariah", "yahya": "john", "ilyas": "elias",
    "luqman": "luqman", "khizar": "khidr", "adam": "adam", "hawwa": "eve", "jibreel": "gabriel", "jibrail": "gabriel",
    "abortion": "kill children", "suicide": "kill yourselves", "tattoo": "tattoo", "wig": "false hair",
}
STOP_EN = set("""what does do did say says said about is are was the a an in on of to for and or islam islamic quran
    allah's tell me please explain meaning mean means why how when where who which can could should would will
    shall may might must there their they them it its this that these those i my me we our you your he his she her
    be been being have has had not no yes than then also just only any some many much more most very all every
    kya hai hain kaha kehta kehte batao bataiye bare baare mein main me ka ki ke ko se aur ya nahi lena dena deni
    dene kaisa kaisi kaise kitna kitni kitne hoti hote hota hona chahiye chahie karna karni karte kiya kiye wala wali
    wale lagta milta sakta sakte sakti kab kyun kaun kis kisi apna apni apne bare hukm masla rule rules""".split())
STOP_UR = set("کے کی کا کو سے میں ہے ہیں کیا بارے اور یا نہیں کیسے کیوں کب کون جو یہ وہ پر بھی تو ہو ہوتا ہوتی ہوتے "
              "کرنا کریں کرے چاہیے بتائیں بتاؤ اسلام قرآن حکم مسئلہ".split())
# words that ask for a ruling: they help the ranking but a text need not contain them
INTENT = set("haram halal jaiz jayaz najaiz allowed permissible permitted forbidden prohibited lawful unlawful sin".split())


def _build():
    from quran_data import load_quran
    from translations import texts
    tmp = DB.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    c = sqlite3.connect(tmp)
    c.execute("create virtual table docs using fts5(kind unindexed, ref unindexed, lang unindexed, text, "
              "tokenize='porter unicode61 remove_diacritics 2')")
    quran = load_quran()
    en, ur = texts("en", quran, log=lambda m: None), texts("ur", quran, log=lambda m: None)
    rows = []
    for i, a in enumerate(quran):
        ref = f"{a['surah']}:{a['ayah']}"
        rows += [("quran", ref, "en", en[i]), ("quran", ref, "ur", ur[i])]
    for col in ("bukhari", "muslim"):
        for lang, code in (("eng", "en"), ("urd", "ur")):
            f = DATA / "hadith" / f"{lang}-{col}.json"
            if not f.exists():
                continue
            for h in json.loads(f.read_text(encoding="utf-8"))["hadiths"]:
                text = h["text"].strip()      # skip notes that only repeat a chain of narrators
                if len(text) >= 40 and not (len(text) < 400 and re.search(
                        r"(same chain|chain of (narrators|transmitters)|has been (narrated|reported|transmitted) (by|on the authority|through))", text, re.I)
                        and not re.search(r'(said|saying)\s*[:,]?\s*["“]', text)):
                    ref = json.dumps([col, h["hadithnumber"], h.get("reference") or {}])
                    rows.append(("hadith", ref, code, h["text"]))
    c.executemany("insert into docs values (?, ?, ?, ?)", rows)
    c.execute("create table meta (k, v)")
    c.execute("insert into meta values ('version', ?)", (VERSION,))
    c.commit()
    c.close()
    tmp.replace(DB)


def _db():
    with _lock:
        ok = False
        if DB.exists():
            try:
                c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
                ok = c.execute("select v from meta where k='version'").fetchone() == (VERSION,)
                c.close()
            except sqlite3.Error:
                pass
        if not ok:
            _build()
    return sqlite3.connect(f"file:{DB}?mode=ro", uri=True, check_same_thread=False)


def terms(question):
    """The searchable ideas in a question: [(alternative words, optional)]. Content words are required ideas
    (Roman Urdu turned into the English words the translations use, synonyms as alternatives, Urdu as it is);
    ruling words such as haram are optional."""
    groups, seen = [], set()
    for w in re.findall(r"[\w']+", question.lower()):
        w = w.strip("'")
        if len(w) < 2 or w in seen or w in STOP_EN or w in STOP_UR or (w.isascii() and w in guidance.STOP):
            continue
        seen.add(w)
        alts = BRIDGE.get(w, w).split() if w.isascii() else [w]
        optional = w in INTENT or any(a in INTENT for a in alts)
        groups.append((alts, optional))
    return groups[:8]


def content_words(question):
    """The question's own content words (no fillers), as they were written."""
    return [w for w in (x.strip("'") for x in re.findall(r"[\w']+", question.lower()))
            if len(w) >= 2 and w not in STOP_EN and w not in STOP_UR and w not in INTENT
            and not (w.isascii() and w in guidance.STOP)]


def _q(words):
    return " OR ".join('"' + t.replace('"', "") + '"' for t in words)


def _has(text, t):
    if not t.isascii():
        return t in text
    return re.search(rf"\b{re.escape(t[:max(4, len(t) - 2)])}", text) is not None


def _hits(c, groups, kind, limit):
    """[(ref, score)] best first. A text must contain every required idea (or, for longer questions, all but
    one); ideas that appear nowhere (e.g. an unknown word) are ignored."""
    groups = [g for g in groups if c.execute("select rowid from docs where docs match ? limit 1", (_q(g[0]),)).fetchone()]
    required = [g for g in groups if not g[1]] or groups
    if not required:
        return []
    need = len(required) if len(required) <= 2 else len(required) - 1
    rows = c.execute("select ref, text, bm25(docs) from docs where docs match ? and kind = ? order by bm25(docs) "
                     "limit 600", (_q([w for g in groups for w in g[0]]), kind)).fetchall()
    best = {}
    for ref, text, score in rows:
        low = text.lower()
        req = sum(any(_has(low, t) for t in g[0]) for g in required)
        opt = sum(any(_has(low, t) for t in g[0]) for g in groups if g not in required)
        if req >= need:
            cand = (req, opt, -score)
            if ref not in best or cand > best[ref]:
                best[ref] = cand
    return sorted(best, key=best.get, reverse=True)[:limit]


def search(question, quran, ranges, tr, lang, n_ayat=3, n_hadith=3):
    """An answer in the same shape as guidance.answer, or None when nothing relevant is found."""
    groups = terms(question)
    if not groups:
        return None
    c = _db()
    try:
        ayat = _hits(c, groups, "quran", n_ayat)
        hadith = _hits(c, groups, "hadith", n_hadith)
        if not ayat and not hadith:
            return None
        urdu_side = lang in ("ur", "ks", "ur-roman")
        passages = []
        for ref in ayat:
            s, a = map(int, ref.split(":"))
            i = ranges[s][0] + a - 1
            passages.append({"surah": s, "from": a, "to": a, "surah_en": quran[i]["surah_en"],
                             "surah_ar": quran[i]["surah_ar"], "verses": [{"n": a, "ar": quran[i]["ar"], "tr": tr[i]}]})
        hs = []
        for ref in hadith:
            col, num, r = json.loads(ref)
            en = c.execute("select text from docs where kind='hadith' and ref=? and lang='en'", (ref,)).fetchone()
            ur = c.execute("select text from docs where kind='hadith' and ref=? and lang='ur'", (ref,)).fetchone()
            en, ur = (en or ("",))[0].strip(), (ur or ("",))[0].strip()
            if col == "bukhari":
                label, url = f"Sahih al-Bukhari {num}", f"https://sunnah.com/bukhari:{num}"
            else:
                label = f"Sahih Muslim, Book {r.get('book')}, Hadith {r.get('hadith')}"
                url = f"https://sunnah.com/muslim/{r.get('book')}/{r.get('hadith')}"
            use_ur = urdu_side and bool(ur)
            hs.append({"ref": label, "url": url, "text": _short(ur if use_ur else en), "rtl": use_ur, "en": _short(en or ur)})
    finally:
        c.close()
    note_en = ("These ayat and hadith mention what you asked about. They are search results from the Quran and "
               "Sahih al-Bukhari and Sahih Muslim, not an explanation or a ruling. Read each one in full, and for "
               "a ruling (fatwa) please ask a qualified scholar.")
    note_ur = ("یہ آیات اور احادیث آپ کے سوال سے متعلق ہیں۔ یہ قرآن اور صحیح بخاری و صحیح مسلم میں تلاش کے نتائج ہیں، کوئی تشریح یا "
               "فتویٰ نہیں۔ ہر ایک کو مکمل پڑھیں، اور شرعی مسئلے کے لیے مستند عالم سے پوچھیں۔")
    return {"id": "search", "title": "What the Quran and Sunnah mention", "title_ur": "قرآن و سنت میں اس کا ذکر",
            "crisis": False, "guide": note_ur if urdu_side else note_en, "guide_rtl": urdu_side,
            "ayat": passages, "hadith": hs, "search": True}


def _short(text, limit=1400):
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + " …"
