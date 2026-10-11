"""A qari's own recordings for the YouTube reels, used with their permission.

Famous recitation recordings (Alafasy, Abdul Basit, Minshawi, ...) are registered by record labels in
YouTube's Content ID, so reels using them get blocked. Recordings made for this channel by a qari who has
agreed to it are ours to use. They live in recitations/<id>/, one file per ayah (SSSAAA.mp3, Bismillah =
001001.mp3), plus qari.json with the qari's name and how permission was given. Set QARI=<id> to use them.

  ./run.sh qari new hafiz-ahmad "Hafiz Ahmad" "Written permission by WhatsApp, 11 Oct 2026"
  ./run.sh qari add hafiz-ahmad 1 ~/Desktop/fatiha.m4a           a whole surah in one file: split into ayat
  ./run.sh qari add hafiz-ahmad 2 baqarah.mp3 --from 1 --to 20  ... or a part of a surah
  ./run.sh qari add hafiz-ahmad 112 ikhlas.mp3 --bismillah       the recording starts with Bismillah
  ./run.sh qari status hafiz-ahmad                               which surahs are complete

Splitting cuts at the longest pauses, so the qari should pause clearly between ayat (about a second) and
not join ayat (waqf) in this recording. Each ayah's length is compared with its text; anything that looks
wrong is reported, and nothing is saved until the split looks right."""
import argparse
import json
import re
import subprocess
import sys
import unicodedata

from config import ROOT

DIR = ROOT / "recitations"


def letters(words):
    return sum(1 for w in words for ch in w if unicodedata.category(ch) == "Lo")


def silences(path, noise="-35dB", min_len=0.3):
    log = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", f"silencedetect=noise={noise}:d={min_len}",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    h, m, sec = re.search(r"Duration: (\d+):(\d+):([\d.]+)", log).groups()
    dur = int(h) * 3600 + int(m) * 60 + float(sec)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
    pauses = [(s, e) for s, e in zip(starts, ends) if s > 0.05 and e < dur - 0.05]   # not the lead-in / tail
    return dur, pauses


def split(path, texts):
    """Cut a recording of len(texts) pieces at its len(texts)-1 longest pauses. Returns [(start, end)]."""
    dur, pauses = silences(path)
    need = len(texts) - 1
    if len(pauses) < need:
        for noise, min_len in (("-30dB", 0.25), ("-28dB", 0.2)):     # quieter room or shorter pauses
            dur, pauses = silences(path, noise, min_len)
            if len(pauses) >= need:
                break
        else:
            raise SystemExit(f"Found only {len(pauses)} clear pauses for {len(texts)} ayat. Ask the qari to pause "
                             "about a second between ayat, or add the ayat one by one.")
    cuts = sorted(sorted(pauses, key=lambda p: p[1] - p[0], reverse=True)[:need])
    bounds, start = [], 0.0
    for s, e in cuts:
        bounds.append((max(0.0, start), s + 0.15))
        start = e - 0.15
    bounds.append((start, dur))
    return bounds


def check(bounds, texts, names):
    """Print each piece's length next to its text length; return the names of pieces that look wrong."""
    secs = [b - a for a, b in bounds]
    rate = sum(secs) / max(1, sum(letters(t) for t in texts))
    odd = []
    for name, (a, b), t in zip(names, bounds, texts):
        expect = letters(t) * rate
        flag = (b - a) > 2.2 * expect + 1.5 or (b - a) < expect / 2.2 - 0.5
        odd += [name] if flag else []
        print(f"  {name:>8}  {a:7.1f}s – {b:7.1f}s  ({b - a:5.1f}s, text suggests ~{expect:4.1f}s){'   <- check' if flag else ''}")
    return odd


def cmd_add(a, quran, ranges):
    d = DIR / a.id
    if not (d / "qari.json").exists():
        raise SystemExit(f"Unknown qari '{a.id}'. First: ./run.sh qari new {a.id} \"Name\" \"how permission was given\"")
    s0, s1 = ranges[a.surah]
    first, last = a.from_ or 1, a.to or s1 - s0
    items = quran[s0 + first - 1:s0 + last]
    pieces = ([("bismillah", quran[0])] if a.bismillah else []) + [(f"{a.surah}:{it['ayah']}", it) for it in items]
    names, texts = [p[0] for p in pieces], [p[1]["words"] for p in pieces]
    print(f"Splitting {a.file} into {len(pieces)} pieces ({', '.join(names[:3])}{' …' if len(names) > 3 else ''})")
    bounds = split(a.file, texts)
    odd = check(bounds, texts, names)
    if odd and not a.force:
        raise SystemExit(f"\n{len(odd)} piece(s) look wrong ({', '.join(odd)}): probably a pause inside an ayah "
                         "or two ayat joined. Nothing saved. Listen to the recording, or add those ayat one by one "
                         "with --from/--to, or use --force if it is right.")
    for (name, it), (s, e) in zip(pieces, bounds):
        out = d / f"{it['surah']:03d}{it['ayah']:03d}.mp3"
        if name == "bismillah" and out.exists():
            continue                     # keep the first Bismillah recorded
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{s:.3f}", "-to", f"{e:.3f}", "-i", str(a.file),
                        "-ac", "1", "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "96k",
                        "-af", "afade=t=in:d=0.05,areverse,afade=t=in:d=0.08,areverse", str(out)], check=True)
    print(f"Saved {len(pieces)} files in {d}")


def cmd_status(a, quran, ranges):
    d = DIR / a.id
    info = json.loads((d / "qari.json").read_text(encoding="utf-8"))
    print(f"{info['name']}  ({info['permission']})")
    done = part = 0
    for s, (s0, s1) in ranges.items():
        have = sum((d / f"{s:03d}{q['ayah']:03d}.mp3").exists() for q in quran[s0:s1])
        if have == s1 - s0:
            done += 1
            print(f"  ✓ {s:3d} {quran[s0]['surah_en']}")
        elif have:
            part += 1
            print(f"  … {s:3d} {quran[s0]['surah_en']}: {have}/{s1 - s0} ayat")
    print(f"{done} surahs complete, {part} started. Bismillah (001001.mp3): "
          f"{'yes' if (d / '001001.mp3').exists() else 'not yet (record Al-Fatiha first)'}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="./run.sh qari", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new", help="register a qari")
    n.add_argument("id"), n.add_argument("name"), n.add_argument("permission")
    ad = sub.add_parser("add", help="add a recording")
    ad.add_argument("id"), ad.add_argument("surah", type=int), ad.add_argument("file")
    ad.add_argument("--from", dest="from_", type=int), ad.add_argument("--to", type=int)
    ad.add_argument("--bismillah", action="store_true", help="the recording starts with Bismillah")
    ad.add_argument("--force", action="store_true", help="save even if some ayat look wrong")
    st = sub.add_parser("status", help="what has been recorded")
    st.add_argument("id")
    a = ap.parse_args(argv)
    if a.cmd == "new":
        if not re.fullmatch(r"[a-z0-9-]+", a.id):
            raise SystemExit("Use lowercase letters, numbers and - for the id, e.g. hafiz-ahmad")
        (DIR / a.id).mkdir(parents=True, exist_ok=True)
        (DIR / a.id / "qari.json").write_text(json.dumps({"name": a.name, "permission": a.permission},
                                                          ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"Registered {a.name} in recitations/{a.id}/. Next: ./run.sh qari add {a.id} 1 <Al-Fatiha recording>")
        return
    from quran_data import load_quran, surah_ranges
    quran = load_quran()
    (cmd_add if a.cmd == "add" else cmd_status)(a, quran, surah_ranges(quran))


if __name__ == "__main__":
    main(sys.argv[1:])
