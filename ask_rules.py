"""Ask the Quran: recognising a question that asks for a ruling (fatwa), before anything is searched, in English,
Roman Urdu and Urdu. Such a question still gets related ayat and hadith to understand the subject, but it is told
plainly, first, that this site does not give rulings and that a qualified scholar should be asked. Fixed patterns
only (no AI): a match is decided by these words, so it is predictable and can be checked."""
import re

RULING = re.compile("|".join([
    r"\b(halal|haram|haraam|makruh|makrooh|mustahab|wajib|waajib|fard|farz|sunnat|bid'?ah|biddat)\b",
    r"\b(permissible|impermissible|forbidden|allowed in islam|lawful|unlawful|fatwa|fatawa|ruling|obligatory)\b",
    r"\bis it (a )?sin\b|\bis (it|this|that) (ok|okay|allowed|permitted)\b",
    r"\bcan (i|we|a (man|woman|muslim)) (marry|eat|drink|pray|fast|listen|wear|keep|take|shave|pluck|work|invest|"
    r"divorce|celebrate|use|have|do|go|touch|tattoo|smoke|vape|trade|sell|buy)\b",
    r"\b(jaiz|jayaz|jaez|najaiz|na jaiz|nājaiz|durust|thik hai kya)\b",
    r"\bgunah (hai|hota|hoga|he)\b|\bkya .{0,40}\b(kar|kha|pi|pee|pehen|pahen|sun|rakh|tod|tor|chhod|chor|le|de|"
    r"parh|padh|bech|khareed|mana) ?sakt[aei]\b",
    r"حلال|حرام|جائز|ناجائز|فتوی|فتویٰ|مکروہ|واجب|فرض ہے|گناہ ہے|کر سکتے ہیں|کر سکتا ہوں|کر سکتی ہوں",
]), re.I)
NOTE = {"en": "This sounds like a question about a ruling (fatwa). Quran Reel Maker does not give rulings: please ask a "
              "qualified scholar or a Darul Ifta. The ayat and hadith below are only to help you understand the subject.",
        "ur": "یہ ایک شرعی حکم (فتویٰ) کا سوال لگتا ہے۔ یہ ویب سائٹ فتویٰ نہیں دیتی: براہِ کرم کسی مستند عالم یا دارالافتاء سے "
              "پوچھیے۔ نیچے دی گئی آیات اور احادیث صرف موضوع کو سمجھنے کے لیے ہیں۔"}


def is_ruling(q):
    return bool(RULING.search(q or ""))
