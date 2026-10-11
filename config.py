import os
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"
OUT = ROOT / "output"
FONTS = ROOT / "fonts"
STATE_FILE = ROOT / "state.json"
WEB_OUT = ROOT / "web_output"

# Arabic text, recitation and word-by-word timings come from Quran.com (free API).
# The timings belong to these exact audio files, which is what makes word highlighting line up.
RECITERS = {7: "Mishary Rashid Alafasy", 6: "Mahmoud Khalil Al-Husary", 9: "Mohamed Siddiq al-Minshawi",
            3: "Abdur-Rahman as-Sudais", 10: "Saud ash-Shuraym", 4: "Abu Bakr al-Shatri", 5: "Hani ar-Rifai"}
RECITATION_ID = int(os.getenv("QURAN_RECITER", "7"))   # Quran.com recitation id (7 = Alafasy); env for YouTube posts
RECITER_NAME = RECITERS[RECITATION_ID]
# A qari's own recordings, used with their permission (recitations/<QARI>/, see qari.py). When set, the
# recitation comes only from there: famous recordings are claimed by record labels on YouTube.
QARI = os.getenv("QARI", "")
QARI_DIR = ROOT / "recitations" / QARI
if QARI:
    import json
    RECITER_NAME = json.loads((QARI_DIR / "qari.json").read_text(encoding="utf-8"))["name"]
# Urdu translation, ruku and sajdah data come from alquran.cloud, Urdu audio from islamic.network.
URDU_EDITION = "ur.jalandhry"     # Fateh Muhammad Jalandhry (other: ur.junagarhi, ur.kanzuliman)
URDU_NAME = "Fateh Muhammad Jalandhry"

# Urdu translation read aloud after each ayah (set READ_URDU = False to turn off)
READ_URDU = True
URDU_AUDIO = "ur.khan"           # Shamshad Ali Khan
URDU_AUDIO_NAME = "Shamshad Ali Khan"

# Reel rules: a whole surah if it fits, otherwise even parts split at ayah boundaries.
# YouTube treats vertical videos up to 3 minutes as Shorts.
MAX_REEL_SECONDS = 170            # audio per reel (plus the title card)
INTRO_SECONDS = 1.5               # title card at the start (0 to turn off)

# Video size (vertical 9:16)
W, H = 1080, 1920
FPS = 20                          # enough for word highlights to follow the recitation closely

# YouTube
PRIVACY = os.getenv("YT_PRIVACY", "public")   # public / unlisted / private
CHANNEL_TAG = os.getenv("CHANNEL_TAG", "")    # optional text shown at bottom, e.g. "@mychannel"
