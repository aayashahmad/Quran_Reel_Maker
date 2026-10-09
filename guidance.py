"""Ask the Quran: match a visitor's question to a topic in guidance.json (built by build_guidance.py)
and assemble its ayat (text from the site's own Quran data), sahih hadith and guidance.
No AI and no outside service: matching is by keywords in English, Roman Urdu and Urdu."""
import json
import pathlib
import re
from difflib import SequenceMatcher

TOPICS = json.loads((pathlib.Path(__file__).parent / "guidance.json").read_text(encoding="utf-8"))
BY_ID = {t["id"]: t for t in TOPICS}
# phrases that always mean someone may be in danger: answered with the helpline topic first
CRISIS = re.compile(r"suicid|kill (my ?self|myself)|end (my|this) life|want to die|self.?harm|hurt myself|"
                    r"khud ?kushi|mar(na)? jana? chah|marna chahta|marna chahti|خودکشی|مرنا چاہت", re.I)
STOP = set("""i me my am is are was the a an to of in on and or for with it this that be do i'm im how what why
    when can should feel feeling very so really no not dont don't cant can't keep always get got have has will
    would there their they them who whom which where does did he she his her you your we our us about from at by as but if all any every
    mujhe mujhko mera meri mere hai hain hy h ho hun hoon hu tha thi ka ki ke ko se main mai mein me kya kia
    kaise kese kyun kyu kab kahan bohot bahut bhot boht bht nahi nai nhi na ye yeh wo woh koi kuch sab aur
    bhi to tu tum aap ap hum karun karoon karna karta karti kar raha rahi ho gaya gayi gya""".split())


def _words(text):
    return [w for w in re.findall(r"[\w']+", text.lower()) if w not in STOP and len(w) > 1]


def _plain(w):
    return re.sub(r"(.)\1+", r"\1", w)


def _shape(w):
    """Spelling-tolerant shape of a (Roman Urdu) word: first letter, then its consonants without repeats,
    so khatam / khtm / ktm -> ktm, gussa / gusa / ghussa -> gs, qayamat / qyamt -> qmt, hogi / hugy -> hg."""
    if not w.isascii():
        return w
    w = _plain(w)
    return w[0] + re.sub(r"[aeiouyhw']", "", w[1:])


def _phrases(tid):
    from guidance_examples import EXAMPLES
    return [p.strip() for p in EXAMPLES.get(tid, "").split("|") if p.strip()]


_INDEX = {}
for _t in TOPICS:
    _vocab = set(_words(_t["words"] + " " + _t["en"] + " " + " ".join(_phrases(_t["id"]))))
    _INDEX[_t["id"]] = (_vocab, {_shape(w) for w in _vocab if len(_shape(w)) >= 2},
                        [set(map(_shape, _words(p))) for p in _phrases(_t["id"])])


def match(question):
    """Topics ranked for this question: [(score, topic id)], best first; under 2 = no real match.
    Each word counts once: exact word 2, same spelling shape 1.5, same start 1; plus up to 3 for the
    example question closest in shape."""
    q = _words(question)
    qs = {_shape(w) for w in q}
    scores = {}
    for tid, (vocab, shapes, examples) in _INDEX.items():
        s = 0.0
        for w in q:
            if w in vocab:
                s += 2
            elif _shape(w) in shapes and (len(_shape(w)) >= 3 or any(       # short shapes: words must look alike too
                    _shape(v) == _shape(w) and SequenceMatcher(None, _plain(v), _plain(w)).ratio() >= .8 for v in vocab)):
                s += 1.5
            elif len(w) >= 4 and any(v.startswith(w[:5]) or w.startswith(v[:5]) for v in vocab if len(v) >= 4):
                s += 1
        if s and examples:                                                   # only once a word really matched
            s += 3 * max(len(qs & e) / len(qs | e) for e in examples if e)
        scores[tid] = round(s, 2)
    if CRISIS.search(question):
        scores["crisis"] = 100
    return sorted(((v, t) for t, v in scores.items()), key=lambda x: -x[0])


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
