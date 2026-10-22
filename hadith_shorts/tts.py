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


def segments(english, max_words=16):
    """Caption parts: sentences, and long sentences split at commas or semicolons."""
    out = []
    for sent in re.split(r'(?<=[.!?])\s+(?=["“A-Z(])', english.strip()):
        words = sent.split()
        if len(words) <= max_words:
            out.append(sent)
            continue
        cur = []
        for part in re.split(r"(?<=[,;:])\s+", sent):
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


def spoken(text):
    """What the voice says: the text, with the ﷺ sign spoken out."""
    return text.replace("(ﷺ)", "(peace be upon him)").replace("ﷺ", "peace be upon him").replace("`", "'")


def _edge(text, out):
    try:
        import edge_tts
    except ImportError:
        raise TTSError("edge-tts is not installed: pip install -r hadith_shorts/requirements.txt")

    async def run():
        await edge_tts.Communicate(spoken(text), settings.ENGLISH_VOICE, rate=settings.ENGLISH_RATE).save(str(out))
    try:
        asyncio.run(run())
    except Exception as e:                       # network or service errors
        raise TTSError(f"edge-tts failed: {e.__class__.__name__}: {e}")


def _say(text, out):
    with tempfile.TemporaryDirectory() as tmp:
        aiff = Path(tmp) / "a.aiff"
        r = subprocess.run(["say", "-v", settings.SAY_VOICE, "-o", str(aiff), spoken(text)], capture_output=True)
        if r.returncode:
            raise TTSError(f"say failed: {r.stderr.decode()[:200]}")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(aiff), str(out)], check=True)


def speak(text, out):
    """Speak `text` into `out` (mp3/wav). Returns its length in seconds."""
    out = Path(out)
    {"edge": _edge, "say": _say}.get(settings.TTS_ENGINE, _edge)(text, out)
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
