"""Settings for the Daily Sahih Hadith Shorts, from environment variables (see hadith_shorts/.env.example).
Nothing here is secret: the YouTube login comes from token.json / YT_TOKEN_JSON like the Quran poster."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent


def _bool(name, default):
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


HADITH_COLLECTIONS = [c.strip() for c in os.getenv("HADITH_COLLECTIONS", "bukhari,muslim").split(",") if c.strip()]
NARRATION_MODE = os.getenv("NARRATION_MODE", "en")         # en | ar_en (needs ARABIC_AUDIO_DIR recordings)
TTS_ENGINE = os.getenv("TTS_ENGINE", "edge")               # edge (Microsoft Edge neural voices) | say (macOS, testing)
URDU_ENGINE = os.getenv("URDU_ENGINE", "edge")             # omni: the Hayatus Sahaba narrator (OmniVoice, the Mac only)
OMNI_PYTHON = os.getenv("OMNI_PYTHON", str(Path.home() / ".hayatus-voice" / "omni" / "bin" / "python"))
ENGLISH_VOICE = os.getenv("ENGLISH_VOICE", "en-GB-RyanNeural")
ENGLISH_RATE = os.getenv("ENGLISH_RATE", "-8%")
URDU_VOICE = os.getenv("URDU_VOICE", "ur-PK-AsadNeural")
URDU_RATE = os.getenv("URDU_RATE", "-8%")
SLOT_LANGS = [x.strip() for x in os.getenv("SLOT_LANGS", "en,ur,en").split(",") if x.strip()]   # language of each daily slot
SAY_VOICE = os.getenv("SAY_VOICE", "Daniel")
ARABIC_AUDIO_DIR = Path(os.getenv("ARABIC_AUDIO_DIR", str(HERE / "arabic_audio")))  # <ref>.mp3, human-recorded
PAUSE_SECONDS = float(os.getenv("PAUSE_SECONDS", "0.35"))
INCLUDE_REFLECTION = _bool("INCLUDE_REFLECTION", False)    # a short reflection, clearly labelled as ours
VIDEO_WIDTH = int(os.getenv("VIDEO_WIDTH", "1080"))
VIDEO_HEIGHT = int(os.getenv("VIDEO_HEIGHT", "1920"))
VIDEO_MAX_SECONDS = float(os.getenv("VIDEO_MAX_SECONDS", "75"))
PUBLISH_TIME = os.getenv("PUBLISH_TIME", "")                # "18:00" = scheduled; empty = publish at upload
TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")
YOUTUBE_PRIVACY_STATUS = os.getenv("YOUTUBE_PRIVACY_STATUS", "private")   # private | unlisted | public
VIDEOS_PER_DAY = int(os.getenv("VIDEOS_PER_DAY", "3"))   # 09:00 en, 15:00 ur (the Mac), 21:00 en IST (SLOT_TIMES)
ENABLE_PUBLICATION = _bool("ENABLE_PUBLICATION", False)    # off: render and validate only, no upload
OUTPUT_DIRECTORY = Path(os.getenv("OUTPUT_DIRECTORY", str(ROOT / "output" / "hadith")))
DB_PATH = Path(os.getenv("HADITH_DB", str(HERE / "history.sqlite")))
SITE_LABEL = "quranreelmaker.xyz"
