"""Anonymous usage counts for the admin dashboard: how many pages were opened and reels made, which surahs and
languages are popular. Only daily totals are kept (data/stats.json, the last 90 days): no IP addresses, no
questions or other text people type, nothing that identifies anyone."""
import json
import os
import threading
import time
from collections import Counter, defaultdict

from config import DATA

FILE = DATA / "stats.json"
KEEP_DAYS = 90
_lock = threading.Lock()
_days = None                       # {"2026-10-13": {"counts": Counter, "surahs": Counter, "langs": Counter, "topics": Counter}}
_dirty = False


def _load():
    global _days
    if _days is None:
        try:
            raw = json.loads(FILE.read_text())
        except (FileNotFoundError, ValueError):
            raw = {}
        _days = defaultdict(lambda: {k: Counter() for k in ("counts", "surahs", "langs", "topics")})
        for day, groups in raw.items():
            _days[day] = {k: Counter(groups.get(k, {})) for k in ("counts", "surahs", "langs", "topics")}


def count(what, surah=None, lang=None, topic=None):
    """Add one to today's total of `what` (e.g. "reel_cloud"), and to its surah / language / topic if given."""
    global _dirty
    day = time.strftime("%Y-%m-%d")
    with _lock:
        _load()
        d = _days[day]
        d["counts"][what] += 1
        if surah:
            d["surahs"][str(surah)] += 1
        if lang:
            d["langs"][lang] += 1
        if topic:
            d["topics"][topic] += 1
        _dirty = True


def save():
    """Write the totals to disk (called every minute); old days are dropped."""
    global _dirty
    with _lock:
        if _days is None or not _dirty:
            return
        cutoff = time.strftime("%Y-%m-%d", time.localtime(time.time() - KEEP_DAYS * 86400))
        data = {day: {k: dict(v) for k, v in g.items()} for day, g in sorted(_days.items()) if day >= cutoff}
        _dirty = False
    FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data))
    os.replace(tmp, FILE)


def _saver():
    while True:
        time.sleep(60)
        try:
            save()
        except OSError:
            pass


threading.Thread(target=_saver, daemon=True).start()


def summary(days=30):
    """Totals for the dashboard: per-day counts for the last `days` days, and the top surahs / languages / topics."""
    with _lock:
        _load()
        today = time.time()
        dates = [time.strftime("%Y-%m-%d", time.localtime(today - i * 86400)) for i in range(days - 1, -1, -1)]
        per_day = [(d, dict(_days[d]["counts"]) if d in _days else {}) for d in dates]
        top = {k: Counter() for k in ("surahs", "langs", "topics")}
        totals = Counter()
        for d in dates:
            if d in _days:
                totals.update(_days[d]["counts"])
                for k in top:
                    top[k].update(_days[d][k])
    return {"per_day": per_day, "totals": dict(totals), "today": per_day[-1][1],
            **{k: v.most_common(8) for k, v in top.items()}}
