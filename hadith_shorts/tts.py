"""Narration. The English is split into short caption parts and each part is spoken into its own file, so every
caption's start and end come from the real audio length (not estimates).

Engines: "edge" (Microsoft Edge's online neural voices via the edge-tts package: free, needs internet, unofficial,
may change or stop working) and "say" (macOS built-in voices, for local tests). Arabic is never synthesised: an
AI voice is not reliable for classical Arabic with full vowels, so the Arabic is read only from an approved human
recording (ARABIC_AUDIO_DIR/<collection>_<number>.mp3) when NARRATION_MODE is ar_en."""
import asyncio
import re
import subprocess
import tempfile
from pathlib import Path

from hadith_shorts import settings


class TTSError(Exception):
    pass


def segments(english, max_words=16, lang="en"):
    """Caption parts: sentences, and long sentences split at commas or semicolons."""
    out = []
    ends = r"(?<=[۔!؟])\s+" if lang == "ur" else r'(?<=[.!?])\s+(?=["“A-Z(])'
    for sent in re.split(ends, english.strip()):
        words = sent.split()
        if len(words) <= max_words:
            out.append(sent)
            continue
        cur = []
        for part in re.split(r"(?<=[,;:،])\s+", sent):
            if cur and len(" ".join(cur + [part]).split()) > max_words:
                out.append(" ".join(cur))
                cur = []
            cur.append(part)
        if cur:
            out.append(" ".join(cur))
    return [s for s in out if s.strip()]


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        raise TTSError(f"could not read the length of {path}")


PBUH = "(peace be upon him)"
# a mention of the Prophet: "the Prophet", "Allah's Messenger/Apostle", "the Messenger of Allah", with "Muhammad"
# after it, and a possessive 's; not "the Prophets" nor "the Prophet Musa" (another prophet)
_PROPHET = re.compile(r"\b(?:[Tt]he Prophet|Allah's (?:Messenger|Apostle)|(?:[Tt]he )?Messenger of Allah)(?: Muhammad)?(?:'s)?"
                      r"(?![a-zA-Z]| [A-Z][a-z]| ?\(?(?:ﷺ|peace be upon him|p\.?b\.?u\.?h|may Allah))")


def spoken(text, lang="en"):
    """What the voice says: the text, with the ﷺ sign spoken out and said after every mention of the Prophet that
    lacks it (some translations leave it out), ؐ and ؓ spoken in full (and in Urdu the brackets dropped)."""
    if lang == "ur":
        text = text.replace("ﷺ", " صلی اللہ علیہ وسلم ").replace("ؐ", " صلی اللہ علیہ وسلم ").replace("ؓ", " رضی اللہ عنہ ")
        return re.sub(r"\s+", " ", re.sub(r"[()]", " ", text)).strip()
    text = text.replace("(ﷺ)", PBUH).replace("ﷺ", PBUH).replace("ؐ", PBUH).replace("ؓ", "(may Allah be pleased with him)")
    return _PROPHET.sub(lambda m: f"{m.group(0)} {PBUH}", text).replace("`", "'")


def _edge(text, out, lang="en"):
    try:
        import edge_tts
    except ImportError:
        raise TTSError("edge-tts is not installed: pip install -r hadith_shorts/requirements.txt")

    async def run():
        voice, rate = (settings.URDU_VOICE, settings.URDU_RATE) if lang == "ur" else (settings.ENGLISH_VOICE, settings.ENGLISH_RATE)
        await edge_tts.Communicate(spoken(text, lang), voice, rate=rate).save(str(out))
    import time
    for attempt in range(6):                     # the free service sometimes returns no audio: retry with waits
        try:
            asyncio.run(run())
            if Path(out).exists() and Path(out).stat().st_size > 1000:
                return
            raise RuntimeError("empty audio")
        except Exception as e:                   # network or service errors
            if attempt == 5:
                raise TTSError(f"edge-tts failed 6 times: {e.__class__.__name__}: {e}")
            time.sleep(2 ** (attempt + 1))


def _say(text, out, lang="en"):
    with tempfile.TemporaryDirectory() as tmp:
        aiff = Path(tmp) / "a.aiff"
        r = subprocess.run(["say", "-v", settings.SAY_VOICE, "-o", str(aiff), spoken(text, lang)], capture_output=True)
        if r.returncode:
            raise TTSError(f"say failed: {r.stderr.decode()[:200]}")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(aiff), str(out)], check=True)


def speak(text, out, lang="en"):
    """Speak `text` into `out` (mp3/wav). Returns its length in seconds."""
    out = Path(out)
    {"edge": _edge, "say": _say}.get(settings.TTS_ENGINE, _edge)(text, out, lang)
    if not out.exists() or out.stat().st_size < 1000:
        raise TTSError(f"no audio was produced for: {text[:60]}")
    seconds = duration(out)
    if seconds < 0.3:
        raise TTSError(f"audio too short ({seconds:.2f}s) for: {text[:60]}")
    return seconds


def arabic_recording(h):
    """An approved human recording of the Arabic, if there is one."""
    f = settings.ARABIC_AUDIO_DIR / f"{h.collection}_{h.number}.mp3"
    return f if f.exists() else None
