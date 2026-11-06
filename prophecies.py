"""Prophecies in the Quran, for the /quran-prophecies page: what the Quran foretold that has already happened
("past") and what it says is still to come ("future"). Only references are kept here: the Arabic, Urdu and English
of every ayah are taken from the same verified Quran data as the rest of the site. The titles say only what the
cited ayat say; the notes on fulfilled ones state well-known history. Keep to what is widely agreed (no disputed
interpretations), and have a scholar check new entries."""

PROPHECIES = [
    # past: foretold, then it happened
    {"id": "romans", "cat": "past", "ayat": [(30, 2, 4)],
     "en": "The defeated Romans will win within a few years", "ur": "مغلوب رومی چند سال میں غالب آئیں گے",
     "note": "Within a few years of these ayat the Romans (Byzantines) defeated the Persians, around 624–627 CE."},
    {"id": "badr", "cat": "past", "ayat": [(54, 45, 45)],
     "en": "Their assembly will be defeated and turn their backs", "ur": "یہ جماعت شکست کھائے گی اور پیٹھ پھیر کر بھاگے گی",
     "note": "Revealed in Makkah, fulfilled at the battle of Badr (2 AH)."},
    {"id": "abu-lahab", "cat": "past", "ayat": [(111, 1, 3)],
     "en": "Abu Lahab will be ruined and enter the Fire", "ur": "ابو لہب ہلاک ہوگا اور آگ میں جائے گا",
     "note": "Revealed years before his death; he died without accepting Islam, shortly after Badr."},
    {"id": "masjid-al-haram", "cat": "past", "ayat": [(48, 27, 27)],
     "en": "The believers will enter al-Masjid al-Haram in safety", "ur": "مومن امن کے ساتھ مسجد حرام میں داخل ہوں گے",
     "note": "Revealed after Hudaibiya (6 AH); fulfilled the next year with the 'Umrah of 7 AH."},
    {"id": "crowds", "cat": "past", "ayat": [(110, 1, 3)],
     "en": "Victory will come and people will enter Islam in crowds", "ur": "فتح آئے گی اور لوگ فوج در فوج اسلام میں داخل ہوں گے",
     "note": "Fulfilled with the conquest of Makkah (8 AH) and the tribes that came to accept Islam after it."},
    {"id": "protection", "cat": "past", "ayat": [(5, 67, 67)],
     "en": "Allah will protect the Prophet ﷺ from the people", "ur": "اللہ نبی ﷺ کو لوگوں سے بچائے گا",
     "note": "His enemies never succeeded in killing him; he passed away in Madinah in 11 AH."},
    {"id": "authority", "cat": "past", "ayat": [(24, 55, 55)],
     "en": "Allah promised the believers authority and safety in the land", "ur": "اللہ نے مومنوں سے زمین میں خلافت اور امن کا وعدہ کیا",
     "note": "Fulfilled when the believers, persecuted at first, came to live in safety and lead in Arabia and beyond."},
    {"id": "preserved", "cat": "past", "ayat": [(15, 9, 9)],
     "en": "Allah will preserve the Quran", "ur": "اللہ قرآن کی حفاظت کرے گا",
     "note": "The same text is memorised, recited and printed all over the world today."},
    {"id": "challenge", "cat": "past", "ayat": [(2, 23, 24)],
     "en": "They will never produce a surah like it", "ur": "وہ اس جیسی ایک سورت بھی نہیں لا سکیں گے",
     "note": "The challenge was given in the Prophet's ﷺ lifetime and still stands."},
    # future: what the Quran says is still to come
    {"id": "the-hour", "cat": "future", "ayat": [(20, 15, 15)],
     "en": "The Hour is coming", "ur": "قیامت ضرور آنے والی ہے"},
    {"id": "gog-magog", "cat": "future", "ayat": [(21, 96, 97)],
     "en": "Gog and Magog will be let loose", "ur": "یاجوج و ماجوج کھول دیے جائیں گے"},
    {"id": "the-beast", "cat": "future", "ayat": [(27, 82, 82)],
     "en": "A creature will come out of the earth", "ur": "زمین سے ایک جانور نکلے گا"},
    {"id": "trumpet", "cat": "future", "ayat": [(39, 68, 68)],
     "en": "The Trumpet will be blown", "ur": "صور پھونکا جائے گا"},
    {"id": "sun-and-stars", "cat": "future", "ayat": [(81, 1, 6)],
     "en": "The sun will be wrapped up, the stars will fall and the seas will be set on fire", "ur": "سورج لپیٹ دیا جائے گا، ستارے گر پڑیں گے، سمندر بھڑکا دیے جائیں گے"},
    {"id": "moon-and-sun", "cat": "future", "ayat": [(75, 7, 9)],
     "en": "The moon will darken and the sun and moon will be joined", "ur": "چاند بے نور ہوگا اور سورج اور چاند اکٹھے کر دیے جائیں گے"},
    {"id": "earthquake", "cat": "future", "ayat": [(99, 1, 5)],
     "en": "The earth will shake and tell its news", "ur": "زمین ہلا دی جائے گی اور اپنی خبریں بیان کرے گی"},
    {"id": "mountains", "cat": "future", "ayat": [(101, 4, 5)],
     "en": "People will be like scattered moths and mountains like fluffed wool", "ur": "لوگ بکھرے پتنگوں اور پہاڑ دھنکی اون کی طرح ہوں گے"},
    {"id": "scales", "cat": "future", "ayat": [(21, 47, 47)],
     "en": "Just scales will be set up on the Day of Resurrection", "ur": "قیامت کے دن انصاف کے ترازو رکھے جائیں گے"},
]
CATS = {"past": ("Fulfilled", "پوری ہو چکیں"), "future": ("Still to come", "ابھی آنی ہیں")}
