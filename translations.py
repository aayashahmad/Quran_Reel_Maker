"""Translation languages: one translation per language from alquran.cloud, a few of them also
read aloud. Each translation's text is downloaded once and cached in data/."""
import json
import re
import threading

from config import DATA, URDU_EDITION, URDU_NAME, URDU_AUDIO, URDU_AUDIO_NAME
from quran_data import API, _get

LATIN = "NotoSans.ttf"            # Latin and Cyrillic
NASKH = "NotoNaskhArabic.ttf"     # Arabic script other than Urdu


def _lang(name, native, edition, translator, font=LATIN, rtl=False, audio=None, reader=None):
    return dict(name=name, native=native, edition=edition, translator=translator,
                font=font, rtl=rtl, audio=audio, reader=reader)


# code: language. Urdu first (the default), English second, the rest by English name.
LANGS = {
    "ur": _lang("Urdu", "اردو", URDU_EDITION, URDU_NAME, "NotoNastaliqUrdu.ttf", True, URDU_AUDIO, URDU_AUDIO_NAME),
    "en": _lang("English", "English", "en.sahih", "Saheeh International", audio="en.walk", reader="Ibrahim Walk"),
    "sq": _lang("Albanian", "Shqip", "sq.ahmeti", "Sherif Ahmeti"),
    "am": _lang("Amharic", "አማርኛ", "am.sadiq", "Sadiq & Sani Habib", "NotoSansEthiopic.ttf"),
    "az": _lang("Azerbaijani", "Azərbaycan", "az.mammadaliyev", "Vasim Mammadaliyev and Ziya Bunyadov"),
    "bn": _lang("Bengali", "বাংলা", "bn.bengali", "Muhiuddin Khan", "NotoSansBengali.ttf"),
    "ber": _lang("Berber", "Tamaziɣt", "ber.mensur", "At Mensur"),
    "bs": _lang("Bosnian", "Bosanski", "bs.korkut", "Besim Korkut"),
    "bg": _lang("Bulgarian", "Български", "bg.theophanov", "Tzvetan Theophanov"),
    "ce": _lang("Chechen", "Нохчийн", "ce.magomedov", "Magomedov"),
    "zh": _lang("Chinese", "中文", "zh.jian", "Ma Jian", "NotoSansSC.ttf"),
    "cs": _lang("Czech", "Čeština", "cs.hrbek", "Ivan Hrbek"),
    "dv": _lang("Dhivehi", "ދިވެހި", "dv.divehi", "Office of the President of Maldives", "NotoSansThaana.ttf", True),
    "nl": _lang("Dutch", "Nederlands", "nl.leemhuis", "Fred Leemhuis"),
    "fr": _lang("French", "Français", "fr.hamidullah", "Muhammad Hamidullah", audio="fr.leclerc", reader="Youssouf Leclerc"),
    "de": _lang("German", "Deutsch", "de.bubenheim", "A. S. F. Bubenheim and N. Elyas"),
    "ha": _lang("Hausa", "Hausa", "ha.gumi", "Abubakar Mahmoud Gumi"),
    "hi": _lang("Hindi", "हिन्दी", "hi.hindi", "Suhel Farooq Khan and Saifur Rahman Nadwi", "NotoSansDevanagari.ttf"),
    "id": _lang("Indonesian", "Bahasa Indonesia", "id.indonesian", "Indonesian translation"),
    "it": _lang("Italian", "Italiano", "it.piccardo", "Hamza Roberto Piccardo"),
    "ja": _lang("Japanese", "日本語", "ja.japanese", "Japanese translation", "NotoSansJP.ttf"),
    "ko": _lang("Korean", "한국어", "ko.korean", "Korean translation", "NotoSansKR.ttf"),
    "ku": _lang("Kurdish", "کوردی", "ku.asan", "Burhan Muhammad-Amin", NASKH, True),
    "ms": _lang("Malay", "Bahasa Melayu", "ms.basmeih", "Abdullah Muhammad Basmeih"),
    "ml": _lang("Malayalam", "മലയാളം", "ml.abdulhameed", "Cheriyamundam Abdul Hameed and Kunhi Mohammed Parappoor",
                "NotoSansMalayalam.ttf"),
    "my": _lang("Burmese", "မြန်မာ", "my.ghazi", "Ghazi Muhammed Hashim", "NotoSansMyanmar.ttf"),
    "no": _lang("Norwegian", "Norsk", "no.berg", "Einar Berg"),
    "ps": _lang("Pashto", "پښتو", "ps.abdulwali", "Abdul Wali", NASKH, True),
    "fa": _lang("Persian", "فارسی", "fa.fooladvand", "Mohammad Mahdi Fooladvand", NASKH, True),
    "pl": _lang("Polish", "Polski", "pl.bielawskiego", "Józef Bielawski"),
    "pt": _lang("Portuguese", "Português", "pt.elhayek", "Samir El-Hayek"),
    "ro": _lang("Romanian", "Română", "ro.grigore", "George Grigore"),
    "ru": _lang("Russian", "Русский", "ru.kuliev", "Elmir Kuliev", audio="ru.kuliev-audio", reader="Elmir Kuliev"),
    "sd": _lang("Sindhi", "سنڌي", "sd.amroti", "Taj Mehmood Amroti", NASKH, True),
    "si": _lang("Sinhala", "සිංහල", "si.naseemismail", "Naseem Ismail and Masoor Maulana Kaleel", "NotoSansSinhala.ttf"),
    "so": _lang("Somali", "Soomaali", "so.abduh", "Mahmud Muhammad Abduh"),
    "es": _lang("Spanish", "Español", "es.cortes", "Julio Cortes"),
    "sw": _lang("Swahili", "Kiswahili", "sw.barwani", "Ali Muhsin Al-Barwani"),
    "sv": _lang("Swedish", "Svenska", "sv.bernstrom", "Knut Bernström"),
    "tg": _lang("Tajik", "Тоҷикӣ", "tg.ayati", "AbdolMohammad Ayati"),
    "ta": _lang("Tamil", "தமிழ்", "ta.tamil", "Jan Trust Foundation", "NotoSansTamil.ttf"),
    "tt": _lang("Tatar", "Татарча", "tt.nugman", "Yakub Ibn Nugman"),
    "th": _lang("Thai", "ไทย", "th.thai", "King Fahad Quran Complex", "NotoSansThai.ttf"),
    "tr": _lang("Turkish", "Türkçe", "tr.diyanet", "Diyanet İşleri"),
    "ug": _lang("Uyghur", "ئۇيغۇرچە", "ug.saleh", "Muhammad Saleh", NASKH, True),
    "uz": _lang("Uzbek", "Ўзбек", "uz.sodik", "Muhammad Sodik Muhammad Yusuf", audio="uz.sodik-audio",
                reader="Muhammad Sodik Muhammad Yusuf"),
}
LANGS = {k: LANGS[k] for k in ["ur", "en"] + sorted((k for k in LANGS if k not in ("ur", "en")),
                                                    key=lambda k: LANGS[k]["name"])}
NO_SPACES = {"zh", "ja", "th", "my"}   # written without spaces between words: wrapped by letter, never highlighted

_cache, _lock = {}, threading.Lock()


def texts(code, quran, log=print):
    """The translation of every ayah (6236 strings, in Quran order) in this language."""
    if code == "ur":
        return [a["ur"] for a in quran]     # already part of the Quran data
    with _lock:
        if code not in _cache:
            ed = LANGS[code]["edition"]
            f = DATA / f"tr_{ed}.json"
            if not f.exists():
                log(f"Downloading the {LANGS[code]['name']} translation")
                surahs = _get(API.format(ed)).json()["data"]["surahs"]
                f.write_text(json.dumps([a["text"].replace("﻿", "").strip()
                                         for s in surahs for a in s["ayahs"]], ensure_ascii=False),
                             encoding="utf-8")
            # some translations contain stray control characters, which fonts can't draw
            _cache[code] = [re.sub(r"[\x00-\x1f\x7f-\x9f]", "", t)
                            for t in json.loads(f.read_text(encoding="utf-8"))]
        return _cache[code]
