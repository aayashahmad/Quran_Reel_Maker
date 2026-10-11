import argparse
import json
import shutil
from concurrent.futures import ThreadPoolExecutor

from config import STATE_FILE, OUT, MAX_REEL_SECONDS, PRIVACY, READ_URDU, URDU_AUDIO, QARI
from quran_data import load_quran, surah_ranges, get_audio, duration, qari_file
from content import reel_info, metadata
import backgrounds
import translations
import video


_QURAN = []


def quran_cached():
    if not _QURAN:
        _QURAN.extend(load_quran())
    return _QURAN


def read_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"next_index": 0, "videos": 0}


def write_state(s):
    STATE_FILE.write_text(json.dumps(s, indent=2))


DEFAULT_VOICE = URDU_AUDIO if READ_URDU else None


def ayah_audio(item, voice=DEFAULT_VOICE):
    """Audio files for one ayah: the Arabic recitation, then (if `voice`, an audio edition) the translation."""
    files = [get_audio(item)]
    if voice:
        files.append(get_audio(item, voice))
    return files


def bismillah_item(first, fatiha1):
    """Bismillah shown as its own unnumbered frame before ayah 1 (not for Surah 1 or 9).
    Its text, word timings and audio are Al-Fatiha 1:1 (Bismillah) from the same reciter."""
    b = {k: fatiha1[k] for k in ("n", "ar", "ur", "words", "segments", "audio_url")}
    b.update(is_bismillah=True, surah=first["surah"], surah_en=first["surah_en"],
             surah_ar=first["surah_ar"])
    return b


def with_bismillah(quran, items):
    if items and items[0].get("bismillah"):
        return [bismillah_item(items[0], quran[0])] + list(items)
    return list(items)


def prefetch(items, voice=DEFAULT_VOICE, log=print):
    """Download all audio for these ayat in parallel (the audio server is slow one by one)."""
    items = list(items)
    if any(it.get("bismillah") for it in items):
        items.append(quran_cached()[0])
    done = [0]

    def one(it):
        ayah_audio(it, voice)
        done[0] += 1
        log(f"Downloading audio {done[0]}/{len(items)}")
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(one, items))


def split(durs, cap=MAX_REEL_SECONDS, groups=None):
    """Split ayah durations into the fewest parts of at most `cap` seconds,
    then even them out. Returns [(start, end), ...] (end exclusive).
    `groups` (e.g. ruku numbers per ayah): parts end only where a group ends,
    unless one group alone is longer than `cap`."""
    if groups:
        # Every ruku end is a cut point. Rukus that fit are merged with their
        # neighbours; a ruku longer than `cap` is split evenly inside itself.
        parts, run, i = [], [], 0       # run: (start, end, seconds) of short rukus in a row

        def flush():
            merged = split([r[2] for r in run], cap)
            parts.extend((run[a][0], run[b - 1][1]) for a, b in merged)
            run.clear()

        while i < len(durs):
            j = i
            while j < len(durs) and groups[j] == groups[i]:
                j += 1
            secs = sum(durs[i:j])
            if secs <= cap:
                run.append((i, j, secs))
            else:
                if run:
                    flush()
                parts.extend((i + a, i + b) for a, b in split(durs[i:j], cap))
            i = j
        if run:
            flush()
        return parts

    def greedy(c):
        parts, start, tot = [], 0, 0.0
        for i, d in enumerate(durs):
            if i > start and tot + d > c:
                parts.append((start, i))
                start, tot = i, 0.0
            tot += d
        parts.append((start, len(durs)))
        return parts

    k = len(greedy(cap))
    lo, hi = sum(durs) / k, cap
    for _ in range(30):                 # smallest cap that still needs only k parts
        mid = (lo + hi) / 2
        if len(greedy(mid)) <= k:
            hi = mid
        else:
            lo = mid
    return greedy(hi)


def plan_surah(quran, start, end, log=print):
    log(f"Planning Surah {quran[start]['surah_en']}: fetching audio for {end - start} ayat")
    prefetch(quran[start:end], log=lambda m: None)
    durs = []
    for a in quran[start:end]:
        files = ayah_audio(a)
        if a.get("bismillah"):
            files = ayah_audio(quran[0]) + files
        durs.append(sum(duration(f) for f in files))
    rukus = [a["ruku"] for a in quran[start:end]]
    return [[start + a, start + b] for a, b in split(durs, groups=rukus)]


class TooLong(Exception):
    """Selection is longer than allowed. `parts` = suggested reels as (first ayah, last ayah, seconds)."""
    def __init__(self, seconds, parts):
        super().__init__(f"{seconds / 60:.0f} minutes is too long")
        self.seconds, self.parts = seconds, parts


def build_reel(items, info, out_dir, name, read_aloud=READ_URDU, log=print, max_seconds=None, lang="ur", bg=None,
               question=""):
    """Render mp4 + thumbnail for these ayat. Returns (mp4, thumb, title, desc, tags, seconds).
    lang: translation language code (see translations.LANGS); read_aloud: also play its recording
    after each ayah, when that language has one. bg: a background style (backgrounds.STYLES), or
    None to pick one from the surah and ayah.
    With max_seconds, raises TooLong (with suggested parts) instead of rendering a longer video."""
    voice = translations.LANGS[lang]["audio"] if read_aloud else None
    texts = translations.texts(lang, quran_cached(), log)
    prefetch(items, voice, log)
    if max_seconds:
        durs = []
        for it in items:
            files = ayah_audio(it, voice)
            if it.get("bismillah"):
                files = ayah_audio(quran_cached()[0], voice) + files
            durs.append(sum(duration(f) for f in files))
        if sum(durs) > max_seconds:
            parts = split(durs, groups=[it["ruku"] for it in items])
            raise TooLong(sum(durs), [(items[a]["ayah"], items[b - 1]["ayah"], sum(durs[a:b]))
                                      for a, b in parts])
    out_dir.mkdir(parents=True, exist_ok=True)
    work = out_dir / f"work_{name}"
    if work.exists():
        shutil.rmtree(work)
    items = [dict(it, tr=texts[it["n"] - 1]) for it in items]
    frames = [dict(it, tr=texts[it["n"] - 1]) for it in with_bismillah(quran_cached(), items)]
    audio = [ayah_audio(it, voice) for it in frames]
    mp4 = out_dir / f"{name}.mp4"
    secs = video.render(frames, audio, info | {"question": question}, mp4, work, log=log, lang=lang,
                        bg=bg or backgrounds.pick(info))
    thumb = video.make_thumbnail(info, out_dir / f"{name}_thumbnail.jpg", video.tr_lang(lang))
    shutil.rmtree(work, ignore_errors=True)
    title, desc, tags = metadata(items, info, bool(voice), lang)
    return mp4, thumb, title, desc, tags, secs


def post_one(quran, ranges, state, dry):
    idx = state["next_index"]
    if idx >= len(quran):
        print("Whole Quran finished! Alhamdulillah. Reset state.json to start again.")
        return False
    surah = quran[idx]["surah"]
    s0, s1 = ranges[surah]
    if QARI:                             # post only what the qari has recorded: the rest of this surah
        need = quran[idx:s1] + ([quran[0]] if any(a["bismillah"] for a in quran[idx:s1]) else [])
        missing = [f"{a['surah']}:{a['ayah']}" for a in need if not qari_file(a).exists()]
        if missing:
            print(f"Waiting for recordings of Surah {quran[idx]['surah_en']}: {len(missing)} ayat missing "
                  f"({', '.join(missing[:5])}{' …' if len(missing) > 5 else ''}). Nothing posted.")
            return False

    plan = state.get("plan")
    if not plan or plan["surah"] != surah or idx not in [p[0] for p in plan["parts"]]:
        plan = {"surah": surah, "parts": plan_surah(quran, idx, s1)}
        state["plan"] = plan
    parts = plan["parts"]
    k = [p[0] for p in parts].index(idx)
    a, b = parts[k]
    items = quran[a:b]
    info = reel_info(items, k + 1, len(parts), full=(a == s0 and b == s1))

    name = f"reel_{state['videos'] + 1:04d}_{info['ref'].replace(':', '_')}"
    mp4, thumb, title, desc, tags, secs = build_reel(items, info, OUT, name, log=lambda m: None)
    print(f"Rendered {mp4.name}  ({secs:.1f}s)  -> {title}")

    if dry:
        print("DRY RUN: not uploading, progress not changed.")
        return True

    from youtube_upload import upload
    vid = upload(mp4, title, desc, tags, PRIVACY, thumbnail=thumb)
    print(f"Uploaded: https://youtube.com/shorts/{vid}")
    state["next_index"] = b              # only advance AFTER a successful upload
    state["videos"] += 1
    write_state(state)
    return True


def main():
    import sys
    if sys.argv[1:2] == ["qari"]:            # a qari's own recordings: see qari.py
        import qari
        return qari.main(sys.argv[2:])
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["auth", "run", "status", "web", "qari"])
    ap.add_argument("--count", type=int, default=1, help="reels to post in this run")
    ap.add_argument("--dry-run", action="store_true", help="render only, no upload")
    ap.add_argument("--port", type=int, default=5050, help="port for the website")
    a = ap.parse_args()

    if a.cmd == "auth":
        from youtube_upload import auth
        return auth()
    if a.cmd == "web":
        from web import app
        print(f"Open http://localhost:{a.port}")
        return app.run(port=a.port, threaded=True)

    quran = quran_cached()
    ranges = surah_ranges(quran)
    state = read_state()
    if a.cmd == "status":
        done = state["next_index"]
        print(f"{done}/{len(quran)} ayat done, {state['videos']} reels posted.")
        if done < len(quran):
            q = quran[done]
            print(f"Next: Surah {q['surah_en']} {q['surah']}:{q['ayah']}")
        return

    for _ in range(a.count):
        if not post_one(quran, ranges, state, a.dry_run):
            break
        if a.dry_run:
            break


if __name__ == "__main__":
    main()
