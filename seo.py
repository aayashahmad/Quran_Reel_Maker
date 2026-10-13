"""Pages for search engines and AI answer engines: one page per surah (Arabic with Urdu and English
translation) and one per Ask the Quran topic (verified ayat, sahih hadith, guidance), plus their structured
data (schema.org JSON-LD), the sitemap and llms.txt. All text comes from the same verified data as the app."""
import json
import re

from config import ROOT

SITE = "https://quranreelmaker.xyz"
INDEXNOW_KEY = "591cf659eeb874507d48e077c1a3e769"     # public by design (IndexNow: lets Bing/Yandex accept our "these pages changed" pings)
NAME = "Quran Reel Maker"
AUTHOR = {"@type": "Person", "name": "Aayash Ahmad Bhat", "email": "mailto:aayash.bhat.dev@gmail.com"}

SURAHS = json.loads((ROOT / "surah_meta.json").read_text(encoding="utf-8"))
BY_NUMBER = {s["number"]: s for s in SURAHS}

# the spellings people search for, where they differ from the API's name
ALIASES = {1: "Fatiha", 2: "Baqarah", 3: "Al Imran", 4: "Nisa", 12: "Yusuf", 18: "Kahf", 19: "Maryam", 32: "Sajdah",
           36: "Yasin", 48: "Fath", 55: "Rahman", 56: "Waqiah", 62: "Jumuah", 67: "Mulk", 73: "Muzzammil",
           78: "Naba", 87: "Ala", 93: "Duha", 94: "Inshirah", 97: "Qadr", 103: "Asr", 108: "Kausar",
           109: "Kafirun", 110: "Nasr", 112: "Ikhlas", 113: "Falaq", 114: "Nas"}
POPULAR = [36, 55, 67, 18, 56, 1, 112, 2, 73, 113, 114, 97]

# Ask the Quran topics as the questions people type; "crisis" is not a public page (it lives in the app)
QUESTIONS = {
    "grief": "How do I cope with the death of a loved one?",
    "oppression": "What does the Quran say when someone wrongs you?",
    "hope": "Is there hope in Allah's mercy, even for me?",
    "dunya": "What does the Quran say about death, the afterlife and this world?",
    "prayer": "I struggle with prayer. What does the Quran say?",
    "forgive": "How do I forgive someone who hurt me?",
    "future": "How do I make decisions about my career and future?",
    "qiyamah": "When will the world end? What the Quran says about the Day of Judgement",
    "dua": "Why is my dua not answered?",
    "jihad": "What does jihad mean in Islam?",
}
PRIVATE_TOPICS = {"crisis"}


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower().replace("'", "")).strip("-")


def surah_path(n):
    return f"/surah/{n}-{slug(BY_NUMBER[n]['englishName'])}"


def surah_names(n):
    """'Al-Faatiha' plus the common spelling, e.g. 'Al-Faatiha (Fatiha)'."""
    s = BY_NUMBER[n]
    alias = ALIASES.get(n)
    return f"{s['englishName']} ({alias})" if alias and slug(alias) not in slug(s["englishName"]) else s["englishName"]


def question(topic):
    return QUESTIONS.get(topic["id"]) or f"What does the Quran say about {topic['en'][0].lower() + topic['en'][1:]}?"


def topic_path(tid):
    return f"/ask/{tid}"


def ld(obj):
    """A JSON-LD block, safe inside <script>."""
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def breadcrumbs(*items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": name, "item": SITE + path}
                                for i, (name, path) in enumerate(items)]}


HOME_FAQ = [
    ("How do I make a Quran reel?",
     "Choose a surah and the ayat you want, pick a translation language and a background, then press Generate. "
     "You get a vertical 9:16 video with Mishary Rashid Alafasy's recitation, each Arabic word highlighted as it is "
     "recited, and the translation underneath, ready for Instagram Reels, YouTube Shorts, TikTok and WhatsApp status."),
    ("Is Quran Reel Maker free?",
     "Yes. It is completely free, with no sign-up, no watermark other than the site's name and no ads."),
    ("Which translations and languages are available?",
     "More than 46 languages, including Urdu, English, Roman Urdu, Hindi, Bengali, Arabic tafsir, Indonesian, "
     "Turkish, French, Persian and Kashmiri. Some of them can also be read aloud after each ayah."),
    ("Can I read and listen to a whole surah?",
     "Yes. Read and listen plays any surah ayah by ayah with the Arabic words highlighted as they are recited, "
     "with the translation shown and optionally read aloud."),
    ("What is Ask the Quran?",
     "Describe a problem or ask a question, and it shows related ayat and authentic (sahih) hadith from Sahih "
     "al-Bukhari and Sahih Muslim, with every reference checked. It is guidance, not a fatwa: for rulings, ask a "
     "qualified scholar."),
    ("Can I make the video on my phone?",
     "Yes. Generate in cloud makes an MP4 on the server, or Generate on this device records it in your own "
     "browser on iPhone, Android or a computer."),
]


def home_ld():
    return [
        {"@context": "https://schema.org", "@type": "WebSite", "name": NAME, "url": SITE + "/",
         "description": "Free Quran reel maker with word-by-word highlighting and 46+ translations.",
         "inLanguage": ["en", "ur", "ar"],
         "potentialAction": {"@type": "SearchAction", "target": SITE + "/?ask={search_term_string}",
                             "query-input": "required name=search_term_string"}},
        {"@context": "https://schema.org", "@type": "WebApplication", "name": NAME, "url": SITE + "/",
         "applicationCategory": "MultimediaApplication", "operatingSystem": "Any (web browser)",
         "browserRequirements": "Requires JavaScript", "isAccessibleForFree": True,
         "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
         "description": "Make vertical Quran videos (reels and shorts) with Mishary Alafasy's recitation, word-by-word "
                        "highlighting and translations in 46+ languages; read and listen to any surah; ask the Quran "
                        "for guidance from verified ayat and sahih hadith.",
         "featureList": ["Word-by-word highlighting of the Arabic recitation", "46+ translation languages",
                         "Translation read aloud", "11 animated Islamic backgrounds", "Read and listen to any surah",
                         "Ask the Quran: verified ayat and sahih hadith"],
         "image": SITE + "/static/og.png", "author": AUTHOR, "creator": AUTHOR},
        {"@context": "https://schema.org", "@type": "FAQPage",
         "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
                        for q, a in HOME_FAQ]},
    ]


def sitemap_urls(topics, lastmod):
    urls = [("/", "1.0"), ("/surah", "0.8"), ("/ask", "0.8")]
    urls += [(surah_path(s["number"]), "0.7") for s in SURAHS]
    urls += [(topic_path(t["id"]), "0.7") for t in topics if t["id"] not in PRIVATE_TOPICS]
    urls += [("/privacy", "0.2"), ("/terms", "0.2")]
    return "".join(f"<url><loc>{SITE}{p}</loc><lastmod>{lastmod}</lastmod><priority>{pr}</priority></url>"
                   for p, pr in urls)


def llms_txt(topics):
    lines = [f"# {NAME}", "",
             "> Free website to make Quran reels (vertical videos for Instagram Reels, YouTube Shorts, TikTok and "
             "WhatsApp status) with Mishary Rashid Alafasy's recitation, word-by-word highlighting of the Arabic, and "
             "translations in 46+ languages including Urdu, English, Roman Urdu, Hindi and Kashmiri. Also: read and "
             "listen to any surah, and Ask the Quran (related ayat and sahih hadith from Sahih al-Bukhari and Sahih "
             "Muslim, every reference verified; guidance, not fatwa). No sign-up, no ads. Developed by Aayash Ahmad "
             "Bhat (aayash.bhat.dev@gmail.com).", "",
             "## Main", f"- [Make a Quran reel]({SITE}/): the app",
             f"- [All 114 surahs]({SITE}/surah): Arabic text with Urdu (Fateh Muhammad Jalandhry) and English "
             "(Saheeh International) translation",
             f"- [What the Quran says about life's problems]({SITE}/ask): topics with verified ayat and sahih hadith", "",
             "## Popular surahs"]
    lines += [f"- [Surah {surah_names(n)}]({SITE}{surah_path(n)})" for n in POPULAR]
    lines += ["", "## Ask the Quran topics"]
    lines += [f"- [{question(t)}]({SITE}{topic_path(t['id'])})" for t in topics if t["id"] not in PRIVATE_TOPICS]
    lines += ["", "## Notes", "- Quran text and word timings: Quran.com. Translations: alquran.cloud. Hadith: Sahih "
              "al-Bukhari and Sahih Muslim (fawazahmed0/hadith-api), each checked against sunnah.com.",
              "- The Kashmiri audio is made with an AI voice and may contain mistakes.",
              f"- [Privacy]({SITE}/privacy) · [Terms]({SITE}/terms)"]
    return "\n".join(lines) + "\n"
