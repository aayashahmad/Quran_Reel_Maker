import argparse

from documentary import build

p = argparse.ArgumentParser(prog="python -m documentary")
sub = p.add_subparsers(dest="cmd", required=True)
sub.add_parser("list")
m = sub.add_parser("make")
m.add_argument("episode", choices=sorted(build.EPISODES))
m.add_argument("--lang", choices=["en", "ur"], default="en")
m.add_argument("--limit", type=int, help="only the first N segments (a quick look)")
a = p.parse_args()
if a.cmd == "list":
    for k, e in build.EPISODES.items():
        print(f"{k:20} chapters {e['chapters']}  {e['en']}")
else:
    build.make(a.episode, a.lang, limit=a.limit)
