"""Qissa story videos (paper-collage style, English and Hinglish).

  python -m qissa check yunus            check the script: both languages, art, every ayah/hadith exists and verifies
  python -m qissa make yunus --lang en   make the video (en or hi); both: --lang all
  python -m qissa list                   the stories
  python -m qissa daily                  the daily job: next video in the queue, uploaded private, public 5 h later
"""
import argparse
import sys

from qissa import build


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m qissa")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("story")
    m = sub.add_parser("make")
    m.add_argument("story")
    m.add_argument("--lang", choices=["en", "hi", "all"], default="all")
    sub.add_parser("list")
    sub.add_parser("daily")
    a = ap.parse_args(argv)
    if a.cmd == "daily":
        from qissa import daily
        out = build.ROOT / "output" / "qissa"
        out.mkdir(parents=True, exist_ok=True)
        return daily.run(out)
    if a.cmd == "list":
        for f in sorted(build.STORIES.glob("*.json")):
            s = build.load(f.stem)
            print(f"{f.stem:12} #{s.get('number', 0):03d}  {s['title']['en']}  [{s.get('status', '')}]")
        return 0
    story = build.load(a.story)
    if a.cmd == "check":
        problems = build.check(story)
        print("ready" if not problems else "problems:\n  " + "\n  ".join(problems))
        return 1 if problems else 0
    out = build.ROOT / "output" / "qissa"
    out.mkdir(parents=True, exist_ok=True)
    for lang in (["en", "hi"] if a.lang == "all" else [a.lang]):
        for k, _ in build.parts_of(story):
            res = build.make(a.story, lang, out, part=k)
            print(f"Video: {res['video']} ({res['seconds']:.0f}s, part {k}/{res['parts']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
