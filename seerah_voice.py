"""Seerah Urdu narration in the Hayatus Sahaba narrator's voice (OmniVoice, on this Mac), every sentence checked.

  python3 seerah_voice.py jobs > /tmp/jobs.json                       what is missing (site's Python)
  ~/.hayatus-voice/omni/bin/python seerah_voice.py make /tmp/jobs.json   make it (the Hayatus voice env)
  ... seerah_voice.py make jobs.json <folder>                           into another folder (hadith Shorts use this)

Each block is read sentence by sentence; Whisper listens to every take and a sentence is remade (up to TRIES) until
at least ACCEPT of its words are heard. Sentences still below that are listed in seerah_audio/review.tsv for a person
to listen to. The narrator (narrator.wav/.txt) is the one Hayatus Sahaba uses, so both sites share one voice.

The Prophet's ﷺ name and the salawat are said in proper Arabic: where Whisper hears "(محمد) صلی اللہ علیہ وسلم" in a
take, that stretch is replaced by the same narrator saying it in Arabic (voice/muhammad-salawat-ar.wav,
voice/salawat-ar.wav: OmniVoice's Arabic mode, chosen because Whisper heard them 100% right). If Whisper cannot place
it, the Urdu take is kept as it is."""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).parent
OUT = HERE / "seerah_audio"
NARRATOR = pathlib.Path.home() / "freelancing" / "Hayatus Sahaba" / "audio-omni"
ASR = "mlx-community/whisper-large-v3-turbo"
SR, GAP, SPEED, TRIES, ACCEPT = 24000, 0.45, 0.95, 3, 0.9


def jobs():
    import web
    out = []
    for c in web.seerah.CHAPTERS:
        for b in web.seerah_view(c):
            name = "-".join(b["audio_ur"].split("/")[3:6])               # n-ur-k-hash.mp3
            if not (OUT / name).exists():
                out.append({"file": name, "text": b["say_ur"]})
    return out


def sentences(text):
    """Sentences, and long ones split at a comma, so every take stays short enough to be read cleanly."""
    out = []
    for s in re.split(r"(?<=[۔؟!:])\s+", text.strip()):
        if len(s.split()) <= 30:
            out.append(s)
            continue
        cur = ""
        for part in re.split(r"(?<=[،,])\s+", s):
            if cur and len((cur + " " + part).split()) > 30:
                out.append(cur)
                cur = part
            else:
                cur = (cur + " " + part).strip()
        out.append(cur)
    return [s for s in out if len(re.findall(r"[؀-ۿ]", s)) >= 3]


def norm(s):
    s = re.sub(r"[ً-ٰٟؐ-ؚﷺ]", "", s)
    s = s.replace("ي", "ی").replace("ك", "ک").replace("ہ", "ه").replace("ۃ", "ه").replace("ة", "ه")
    return re.sub(r"\s+", " ", re.sub(r"[^؀-ۿ ]", " ", s)).split()


SALAWAT = ["صلی", "اللہ", "علیہ", "وسلم"]


def _w(word):
    """A heard word, plain: no vowel marks or punctuation, Arabic letters as Urdu."""
    word = re.sub(r"[ً-ٰٟ؀-؟،۔.,!?:\"']", "", word)
    for a, b in (("ى", "ی"), ("ي", "ی"), ("ه", "ہ"), ("ك", "ک"), ("ة", "ہ"), ("أ", "ا"), ("إ", "ا")):
        word = word.replace(a, b)
    return word.strip()


def arabic_salawat(audio, words, clips, sr=SR):
    """Replace each spoken "(محمد) صلی اللہ علیہ وسلم" in a take with the Arabic recording. words: Whisper's
    [(word, start, end)]. Returns (audio, how many were replaced)."""
    import numpy as np
    plain = [_w(w) for w, _, _ in words]
    spans, i = [], 0
    while i < len(plain):
        if plain[i] in ("صلی", "صل") and [p for p in plain[i:i + 4]][1:] == SALAWAT[1:]:
            a = i - 1 if i and plain[i - 1] == "محمد" else i
            spans.append((words[a][1], words[i + 3][2], "muhammad" if a < i else "salawat"))
            i += 4
        else:
            i += 1
    if not spans:
        return audio, 0
    out, pos, fade = [], 0, int(0.03 * sr)
    for start, end, kind in spans:
        a, b = int(max(0, start - 0.04) * sr), int(min(len(audio) / sr, end + 0.06) * sr)
        if a <= pos or b <= a:
            continue
        head = audio[pos:a].copy()
        head[-fade:] *= np.linspace(1, 0, min(fade, len(head)))[-len(head[-fade:]):]
        clip = clips[kind].copy()
        clip[:fade] *= np.linspace(0, 1, fade)
        clip[-fade:] *= np.linspace(1, 0, fade)
        out += [head, np.zeros(int(0.05 * sr), dtype=np.float32), clip, np.zeros(int(0.05 * sr), dtype=np.float32)]
        pos = b
    tail = audio[pos:].copy()
    if len(tail) > fade:
        tail[:fade] *= np.linspace(0, 1, fade)
    out.append(tail)
    return np.concatenate(out).astype(np.float32), len(spans)


def make(path, out=OUT):
    out = pathlib.Path(out)
    import difflib
    import subprocess
    import tempfile
    import time
    import mlx_whisper
    import numpy as np
    import soundfile as sf
    import torch
    from omnivoice import OmniVoice

    todo = json.load(open(path))
    if not todo:
        print("nothing to make")
        return
    model = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map="mps", dtype=torch.float16)
    ref, sr = sf.read(NARRATOR / "narrator.wav", dtype="float32")
    prompt = model.create_voice_clone_prompt(ref_audio=(torch.from_numpy(ref).unsqueeze(0), sr),
                                             ref_text=(NARRATOR / "narrator.txt").read_text(encoding="utf-8"))

    clips = {k: sf.read(HERE / "voice" / f"{f}-ar.wav", dtype="float32")[0]
             for k, f in (("salawat", "salawat"), ("muhammad", "muhammad-salawat"))}

    def timed(audio):
        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            sf.write(f.name, audio, SR)
            r = mlx_whisper.transcribe(f.name, path_or_hf_repo=ASR, language="ur", word_timestamps=True)
        return [(w["word"], w["start"], w["end"]) for seg in r["segments"] for w in seg.get("words", [])]

    def heard(audio):
        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            sf.write(f.name, audio, SR)
            return mlx_whisper.transcribe(f.name, path_or_hf_repo=ASR, language="ur")["text"]

    def coverage(text, audio):
        ref_w, hyp = norm(text), norm(heard(audio))
        sm = difflib.SequenceMatcher(None, ref_w, hyp, autojunk=False)
        return sum(b.size for b in sm.get_matching_blocks()) / max(1, len(ref_w))

    review = open(out / "review.tsv", "a", encoding="utf-8")
    for j, job in enumerate(todo, 1):
        t0, chunks, worst = time.time(), [], 1.0
        for s in sentences(job["text"]):
            best, best_c = None, -1.0
            for _ in range(TRIES):
                a = model.generate(text=s, language="ur", voice_clone_prompt=prompt, speed=SPEED)[0]
                c = coverage(s, a)
                if c > best_c:
                    best, best_c = a, c
                if best_c >= ACCEPT:
                    break
            if best_c < ACCEPT:
                review.write(f"{job['file']}\t{best_c:.2f}\t{s}\n")
                review.flush()
            worst = min(worst, best_c)
            want = s.count("صلی اللہ علیہ وسلم")
            if want:                                     # the name and salawat in proper Arabic
                best, done = arabic_salawat(best, timed(best), clips)
                if done < want:
                    review.write(f"{job['file']}\tsalawat {done}/{want} in Arabic\t{s}\n")
                    review.flush()
            chunks += [best, np.zeros(int(SR * GAP), dtype=np.float32)]
        wav = out / (job["file"] + ".wav")
        sf.write(wav, np.concatenate(chunks), SR)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-af", "loudnorm=I=-16:TP=-1.5",
                        "-ac", "1", "-b:a", "80k", str(out / job["file"])], check=True)
        wav.unlink()
        print(f"[{j}/{len(todo)}] {job['file']}  lowest sentence {worst:.0%}  {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    if sys.argv[1:2] == ["jobs"]:
        print(json.dumps(jobs(), ensure_ascii=False))
    elif sys.argv[1:2] == ["make"]:
        make(sys.argv[2], *sys.argv[3:4])
    else:
        print(__doc__)
