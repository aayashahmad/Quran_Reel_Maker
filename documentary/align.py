"""When does each page of a long ayah or hadith start in its narration? Whisper (word timestamps) hears the block's
audio, its words are matched to the page text, and the page turns when the first words of the next page are spoken.
Runs in the Hayatus voice venv (it has mlx_whisper):

  ~/.hayatus-voice/omni/bin/python documentary/align.py jobs.json out.json
      jobs.json: [{"audio": path, "lang": "en"|"ur", "pages": [text, ...]}, ...]
      out.json:  {"<audio file name>|<pages hash>": [start of page 2, start of page 3, ...], ...}
"""
import difflib
import json
import re
import sys
import unicodedata

ASR = "mlx-community/whisper-large-v3-turbo"


def norm(s, lang):
    s = unicodedata.normalize("NFKC", s)
    if lang == "ur":
        s = re.sub(r"[ً-ٰٟؐ-ؚﷺ]", "", s)
        s = s.replace("ي", "ی").replace("ك", "ک").replace("ہ", "ه").replace("ۃ", "ه").replace("ة", "ه")
        return re.sub(r"\s+", " ", re.sub(r"[^؀-ۿ ]", " ", s)).split()
    return re.sub(r"[^a-z0-9' ]", " ", s.lower().replace("’", "'")).split()


def starts(audio, lang, pages):
    """Seconds at which pages 2..n begin in the audio (None for a page whose words were not heard)."""
    import mlx_whisper
    r = mlx_whisper.transcribe(str(audio), path_or_hf_repo=ASR, language=lang, word_timestamps=True)
    heard = [(w["word"], w["start"]) for seg in r["segments"] for w in seg.get("words", [])]
    hw, ht = [], []
    for word, t in heard:
        for x in norm(word, lang):
            hw.append(x)
            ht.append(t)
    pw, first = [], []
    for p in pages:
        first.append(len(pw))
        pw += norm(p, lang)
    to_heard = {}
    for a, b, size in difflib.SequenceMatcher(None, pw, hw, autojunk=False).get_matching_blocks():
        for k in range(size):
            to_heard[a + k] = b + k
    out = []
    for i in range(1, len(pages)):
        # the first word of the page that was heard (within its first 8 words), else the last heard word before it
        k = next((j for j in range(first[i], min(first[i] + 8, len(pw))) if j in to_heard), None)
        if k is not None:
            out.append(round(max(0.0, ht[to_heard[k]] - 0.15), 2))
            continue
        k = next((j for j in range(first[i] - 1, max(-1, first[i] - 8), -1) if j in to_heard), None)
        out.append(round(ht[to_heard[k]] + 0.5, 2) if k is not None else None)
    return out


if __name__ == "__main__":
    jobs = json.load(open(sys.argv[1]))
    res = {}
    for i, j in enumerate(jobs):
        res[j["key"]] = starts(j["audio"], j["lang"], j["pages"])
        print(f"[{i + 1}/{len(jobs)}] {j['key'][:60]} {res[j['key']]}", flush=True)
    json.dump(res, open(sys.argv[2], "w"), indent=1)
