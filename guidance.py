"""Ask the Quran: match a visitor's question to a topic in guidance.json (built by build_guidance.py)
and assemble its ayat (text from the site's own Quran data), sahih hadith and guidance.
No AI and no outside service: matching is by keywords in English, Roman Urdu and Urdu."""
import json
import pathlib
import re

TOPICS = json.loads((pathlib.Path(__file__).parent / "guidance.json").read_text(encoding="utf-8"))
BY_ID = {t["id"]: t for t in TOPICS}
# phrases that always mean someone may be in danger: answered with the helpline topic first
CRISIS = re.compile(r"suicid|kill (my ?self|myself)|end (my|this) life|want to die|self.?harm|hurt myself|"
                    r"khud ?kushi|mar(na)? jana? chah|marna chahta|marna chahti|خودکشی|مرنا چاہت", re.I)
STOP = set("i me my am is are was the a an to of in on and or for with it this that be do i'm im how what why "
           "when can should feel feeling very so really no not dont don't cant can't keep always get got have has "
           "mujhe mera meri mere hai hain ho ka ki ke ko se main mai "
           "kya kaise bohot bahut".split())


def _words(text):
    return [w for w in re.findall(r"[\w']+", text.lower()) if w not in STOP and len(w) > 1]


_INDEX = {t["id"]: set(_words(t["words"] + " " + t["en"])) for t in TOPICS}


def match(question):
    """Topics ranked for this question: [(score, topic id)], best first; score 0 = no match."""
    q = _words(question)
    scores = {}
    for tid, vocab in _INDEX.items():
        s = 0
        for w in q:
            if w in vocab:
                s += 2
            elif len(w) >= 4 and any(v.startswith(w[:5]) or w.startswith(v[:5]) for v in vocab if len(v) >= 4):
                s += 1                     # "worried" ~ "worry", "parents" ~ "parent"
        scores[tid] = s
    if CRISIS.search(question):
        scores["crisis"] = 100
    return sorted(((s, t) for t, s in scores.items()), key=lambda x: -x[0])


def answer(topic, quran, ranges, tr, lang):
    """Everything the page shows for one topic. tr: the translation of all ayat in `lang`."""
    t = BY_ID[topic]
    passages = []
    for a in t["ayat"]:
        s0 = ranges[a["surah"]][0]
        first = quran[s0]
        passages.append({
            "surah": a["surah"], "from": a["from"], "to": a["to"],
            "surah_en": first["surah_en"], "surah_ar": first["surah_ar"],
            "verses": [{"n": n, "ar": quran[s0 + n - 1]["ar"], "tr": tr[s0 + n - 1]} for n in range(a["from"], a["to"] + 1)],
        })
    urdu_side = lang in ("ur", "ks", "ur-roman")
    return {
        "id": t["id"], "title": t["en"], "title_ur": t["ur"], "crisis": t["crisis"],
        "guide": t["guide_ur"] if urdu_side else t["guide_en"], "guide_rtl": urdu_side,
        "ayat": passages,
        "hadith": [{"ref": f"{h['collection']} {h['number']}", "url": h["url"],
                    "text": h["ur"] if urdu_side and h["ur"] else h["en"],
                    "rtl": bool(urdu_side and h["ur"]), "en": h["en"]} for h in t["hadith"]],
    }


def topic_list():
    return [{"id": t["id"], "title": t["en"], "title_ur": t["ur"]} for t in TOPICS if t["id"] != "crisis"]
