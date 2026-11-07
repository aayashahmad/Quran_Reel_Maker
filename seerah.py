"""The life of the Prophet Muhammad ﷺ (Seerah), chapter by chapter, for /seerah: read and listen in English and Urdu.

A chapter is a list of blocks in order:
  {"say": {"en", "ur"}}            a short linking passage (our words: plain, widely agreed history only)
  {"ayah": (surah, from, to)}      the ayat, taken from the verified Quran text (Arabic, Urdu, English)
  {"hadith": "bukhari:3", ...}     a sahih hadith, taken word for word from the data and checked on sunnah.com;
                                   "en"/"ur": (first words, last words) to show only that part (None = from the
                                   start / to the end), e.g. to leave out the chain of narrators or a long ending.
Everything the Prophet ﷺ said or did is quoted from the Quran or Sahih al-Bukhari / Sahih Muslim, never told in our
own words. The linking passages are drafts until a scholar has checked them ("status")."""
import re

from hadith_shorts import source

STATUS = "draft: to be checked by a scholar"
VOICES = {"en": ("en-US-AndrewMultilingualNeural", "-8%"), "ur": ("ur-PK-AsadNeural", "-8%")}

CHAPTERS = [
    {"n": 1, "id": "birth-and-early-life", "period": "Makkah", "when": "c. 570 CE",
     "en": "Birth and Early Life", "ur": "ولادت اور ابتدائی زندگی",
     "q": "Where and when was the Prophet Muhammad ﷺ born?",
     "blocks": [
         {"say": {"en": "Muhammad ﷺ was born in Makkah, in the tribe of Quraysh. Historians date his birth to around 570 CE. "
                        "His father Abdullah died before he was born, and his mother Aminah died when he was a small child. "
                        "He grew up an orphan, cared for by his grandfather Abdul Muttalib and then by his uncle Abu Talib.",
                  "ur": "محمد ﷺ مکہ میں قبیلہ قریش میں پیدا ہوئے۔ مورخین آپ کی ولادت تقریباً 570 عیسوی میں بتاتے ہیں۔ "
                        "آپ کے والد عبداللہ آپ کی ولادت سے پہلے وفات پا گئے، اور والدہ آمنہ آپ کے بچپن ہی میں وفات پا گئیں۔ "
                        "آپ یتیم پلے بڑھے؛ پہلے دادا عبدالمطلب نے اور پھر چچا ابو طالب نے آپ کی پرورش کی۔"}},
         {"say": {"en": "He himself told us the day of the week on which he was born.",
                  "ur": "آپ ﷺ نے خود بتایا کہ آپ ہفتے کے کس دن پیدا ہوئے۔"}},
         {"hadith": "muslim:2750", "ur": ("ابو قتادہ انصاری", None)},
         {"say": {"en": "Like the prophets before him, he worked as a shepherd in his youth.",
                  "ur": "پہلے انبیاء کی طرح آپ نے بھی جوانی میں بکریاں چرائیں۔"}},
         {"hadith": "bukhari:2262", "ur": ("ابوہریرہ رضی اللہ عنہ نے کہ", None)},
         {"say": {"en": "In Makkah he became known for his honesty, and people called him al-Amin, the trustworthy. "
                        "Years later, Allah reminded him of these early years:",
                  "ur": "مکہ میں آپ اپنی سچائی کے لیے مشہور ہوئے اور لوگ آپ کو امین کہتے تھے۔ "
                        "برسوں بعد اللہ تعالیٰ نے آپ کو ان ابتدائی برسوں کی یاد دلائی:"}},
         {"ayah": (93, 6, 8)},
     ]},
    {"n": 2, "id": "the-first-revelation", "period": "Makkah", "when": "c. 610 CE",
     "en": "The First Revelation", "ur": "پہلی وحی",
     "q": "How did the first revelation come to the Prophet Muhammad ﷺ?",
     "blocks": [
         {"say": {"en": "When he was about forty years old, he began to spend days alone in the cave of Hira, on a mountain "
                        "near Makkah, worshipping Allah. There the first revelation came to him. "
                        "Aisha, the mother of the believers, may Allah be pleased with her, tells us what happened.",
                  "ur": "جب آپ تقریباً چالیس برس کے ہوئے تو مکہ کے قریب ایک پہاڑ پر غار حرا میں تنہائی میں اللہ کی عبادت کرنے لگے۔ "
                        "وہیں آپ پر پہلی وحی نازل ہوئی۔ ام المؤمنین حضرت عائشہ رضی اللہ عنہا بتاتی ہیں کہ کیا ہوا۔"}},
         {"hadith": "bukhari:3", "ur": ("ام المؤمنین عائشہ رضی اللہ عنہا", None)},
         {"say": {"en": "These were the first words of the Quran to be revealed:",
                  "ur": "قرآن کے سب سے پہلے نازل ہونے والے الفاظ یہ تھے:"}},
         {"ayah": (96, 1, 5)},
         {"say": {"en": "Khadijah, may Allah be pleased with her, believed in him, and she was the first person to accept Islam. "
                        "Then the Prophet ﷺ began to call his family and his people to worship Allah alone.",
                  "ur": "حضرت خدیجہ رضی اللہ عنہا آپ پر ایمان لائیں اور سب سے پہلے اسلام قبول کرنے والی وہی تھیں۔ "
                        "پھر نبی ﷺ نے اپنے خاندان اور اپنی قوم کو ایک اللہ کی عبادت کی دعوت دینا شروع کی۔"}},
     ]},
    {"n": 3, "id": "the-hijrah", "period": "Makkah to Madinah", "when": "622 CE",
     "en": "The Hijrah to Madinah", "ur": "ہجرتِ مدینہ",
     "q": "What was the Hijrah of the Prophet Muhammad ﷺ?",
     "blocks": [
         {"say": {"en": "For thirteen years the Prophet ﷺ called the people of Makkah to Islam. Many believers were persecuted, "
                        "and the leaders of Quraysh plotted against him. Then Allah allowed him to emigrate to Madinah, whose "
                        "people had accepted Islam and promised to protect him. He left Makkah secretly with his companion "
                        "Abu Bakr, may Allah be pleased with him, and they hid in the cave of Thawr while Quraysh searched for them.",
                  "ur": "تیرہ برس تک نبی ﷺ اہل مکہ کو اسلام کی دعوت دیتے رہے۔ بہت سے مومنوں کو ستایا گیا اور قریش کے سرداروں نے "
                        "آپ کے خلاف سازشیں کیں۔ پھر اللہ نے آپ کو مدینہ ہجرت کی اجازت دی، جہاں کے لوگ اسلام قبول کر چکے تھے اور "
                        "انہوں نے آپ کی حفاظت کا وعدہ کیا تھا۔ آپ اپنے ساتھی حضرت ابوبکر رضی اللہ عنہ کے ساتھ خاموشی سے مکہ سے نکلے، "
                        "اور دونوں غار ثور میں چھپے رہے جبکہ قریش انہیں تلاش کر رہے تھے۔"}},
         {"ayah": (9, 40, 40)},
         {"say": {"en": "Abu Bakr himself tells us what happened in the cave.",
                  "ur": "حضرت ابوبکر رضی اللہ عنہ خود بتاتے ہیں کہ غار میں کیا ہوا۔"}},
         {"hadith": "bukhari:4663", "ur": ("ابوبکر صدیق رضی اللہ عنہ نے بیان کیا", None)},
         {"say": {"en": "They reached Madinah safely. This journey, the Hijrah, is so important that the Islamic calendar "
                        "counts its years from it.",
                  "ur": "دونوں بحفاظت مدینہ پہنچ گئے۔ یہ سفر، ہجرت، اتنا اہم ہے کہ اسلامی کیلنڈر کے سال اسی سے شمار ہوتے ہیں۔"}},
     ]},
    {"n": 4, "id": "the-battle-of-badr", "period": "Madinah", "when": "2 AH · 624 CE",
     "en": "The Battle of Badr", "ur": "غزوۂ بدر",
     "q": "What happened at the Battle of Badr?",
     "blocks": [
         {"say": {"en": "In the second year after the Hijrah, the Muslims of Madinah met the army of Quraysh at the wells of "
                        "Badr. The believers were few, and the army of Makkah was about three times larger. "
                        "Umar ibn al-Khattab, may Allah be pleased with him, tells us what the Prophet ﷺ did before the battle.",
                  "ur": "ہجرت کے دوسرے سال مدینہ کے مسلمانوں کا سامنا بدر کے کنوؤں کے پاس قریش کے لشکر سے ہوا۔ "
                        "مومن تھوڑے تھے اور مکہ کا لشکر ان سے تقریباً تین گنا بڑا تھا۔ "
                        "حضرت عمر اور حضرت ابن عباس رضی اللہ عنہم بتاتے ہیں کہ جنگ سے پہلے نبی ﷺ نے کیا کیا۔"}},
         {"hadith": "muslim:4588", "en": (None, "So Allah helped him with angels."),
          "ur": ("رسول اللہ صلی اللہ علیہ وسلم نے مشرکین", "فرشتوں کے ذریعے سے آپ کی مدد فرمائی ۔")},
         {"say": {"en": "Ibn Abbas, may Allah be pleased with him, narrates how the Prophet ﷺ came out of his tent.",
                  "ur": "حضرت ابن عباس رضی اللہ عنہما بیان کرتے ہیں کہ نبی ﷺ اپنے خیمے سے کیسے باہر تشریف لائے۔"}},
         {"hadith": "bukhari:3953", "ur": ("ابن عباس رضی اللہ عنہما نے کہ", None)},
         {"say": {"en": "Allah gave the believers victory that day, and reminded them of it in the Quran:",
                  "ur": "اس دن اللہ نے مومنوں کو فتح دی، اور قرآن میں انہیں اس کی یاد دلائی:"}},
         {"ayah": (3, 123, 123)},
     ]},
    {"n": 5, "id": "the-conquest-of-makkah", "period": "Madinah", "when": "8 AH · 630 CE",
     "en": "The Conquest of Makkah", "ur": "فتح مکہ",
     "q": "What happened at the conquest of Makkah?",
     "blocks": [
         {"say": {"en": "Eight years after he had left Makkah, and after Quraysh broke the treaty of Hudaibiya, the Prophet ﷺ "
                        "returned with an army of about ten thousand believers. Makkah was opened with almost no fighting. "
                        "Abdullah ibn Mas'ud, may Allah be pleased with him, describes what he did at the Ka'bah.",
                  "ur": "مکہ چھوڑنے کے آٹھ برس بعد، جب قریش نے صلح حدیبیہ کا معاہدہ توڑ دیا، نبی ﷺ تقریباً دس ہزار مومنوں کے ساتھ "
                        "مکہ واپس آئے۔ مکہ تقریباً بغیر لڑائی کے فتح ہو گیا۔ حضرت عبداللہ بن مسعود رضی اللہ عنہ بتاتے ہیں کہ "
                        "آپ نے کعبہ کے پاس کیا کیا۔"}},
         {"hadith": "bukhari:4287", "ur": ("عبداللہ بن مسعود رضی اللہ عنہ نے بیان کیا", None)},
         {"say": {"en": "The words he recited are from the Quran:", "ur": "آپ جو الفاظ پڑھ رہے تھے وہ قرآن کے ہیں:"}},
         {"ayah": (17, 81, 81)},
         {"say": {"en": "He forgave the people of Makkah who had opposed him for so many years, and people began to enter "
                        "Islam in crowds, as Allah had foretold:",
                  "ur": "آپ نے اہل مکہ کو معاف کر دیا جو برسوں آپ کی مخالفت کرتے رہے تھے، اور لوگ فوج در فوج اسلام میں داخل ہونے لگے، "
                        "جیسا کہ اللہ نے پہلے ہی بتا دیا تھا:"}},
         {"ayah": (110, 1, 3)},
     ]},
]
BY_ID = {c["id"]: c for c in CHAPTERS}


def _cut(text, span):
    """The part of `text` from the first words to the last words of `span` (word for word), and whether it was cut."""
    if not span:
        return text, False
    first, last = span
    a = text.index(first) if first else 0
    b = text.index(last, a) + len(last) if last else len(text)
    return text[a:b].strip(), bool(last)


def hadith_block(b):
    """{"ref", "citation", "url", "en", "ur", "ar", "part"}: the hadith's own text (part = only a part is shown)."""
    h = source.get(b["hadith"])
    en, cut_en = _cut(h.english, b.get("en"))
    ur, cut_ur = _cut(h.urdu_full, b.get("ur"))
    return {"ref": b["hadith"], "citation": h.citation, "url": h.url, "en": en, "ur": ur, "ar": h.arabic_full,
            "part": cut_en or cut_ur}


def check(verify=True):
    """Problems with the chapters (empty = ready): both languages, ayat exist, every cut is word for word, every hadith
    matches its sunnah.com page (verify)."""
    import requests
    from quran_data import load_quran, surah_ranges
    ranges = surah_ranges(load_quran())
    problems, session = [], requests.Session()
    for c in CHAPTERS:
        for k, b in enumerate(c["blocks"], 1):
            where = f"{c['id']} block {k}"
            if "say" in b and not all(b["say"].get(x) for x in ("en", "ur")):
                problems.append(f"{where}: needs English and Urdu")
            if "ayah" in b:
                s, a, z = b["ayah"]
                if s not in ranges or not 1 <= a <= z <= ranges[s][1] - ranges[s][0]:
                    problems.append(f"{where}: no ayah {s}:{a}-{z}")
            if "hadith" in b:
                try:
                    hb = hadith_block(b)
                    if not hb["ur"]:
                        problems.append(f"{where}: {b['hadith']} has no Urdu")
                except (ValueError, source.SourceError) as e:
                    problems.append(f"{where}: {b['hadith']}: {e}")
                    continue
                if verify:
                    ok, detail = source.verify(source.get(b["hadith"]), session)
                    if not ok and "English 8/8" not in detail:          # the English must match fully
                        problems.append(f"{where}: {detail}")
    return problems


def spoken_text(block, lang, ayah_text=None):
    """What the voice reads for a block (ﷺ and the salawat spoken out)."""
    from hadith_shorts.tts import spoken
    if "say" in block:
        text = block["say"][lang]
    elif "ayah" in block:
        text = ayah_text
    else:
        text = hadith_block(block)[lang]
    text = re.sub(r"\s*\(\d+\.\d+(?:, \d+\.\d+)*\)", "", text)          # "(96.1, 96.2)" verse numbers in translations
    return spoken(text, lang)
