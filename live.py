"""People on the site right now, for the admin dashboard. Each open tab makes up a random id and sends a small
ping every 30 seconds while it is visible (static/live.js). Only these random ids are kept, in memory, for about
a minute: no cookies, no IP addresses, nothing written to disk."""
import re
import threading
import time

WINDOW = 70                    # seconds since the last ping that still counts as "here now"
WHERE = {"home", "surah", "ask", "other"}
ACTS = {"", "reel", "listen", "ask"}
_lock = threading.Lock()
_seen = {}                     # random tab id -> (last ping time, where, activity)
_peak = {"day": "", "n": 0, "at": ""}


def ping(sid, where, act, leave=False):
    if not re.fullmatch(r"[a-z0-9]{8,32}", sid or ""):
        return
    now = time.time()
    with _lock:
        if leave:
            _seen.pop(sid, None)
            return
        if len(_seen) > 20000:                       # never grows without bound
            _prune(now)
        _seen[sid] = (now, where if where in WHERE else "other", act if act in ACTS else "")
        _prune(now)
        n, day = len(_seen), time.strftime("%Y-%m-%d")
        if _peak["day"] != day or n > _peak["n"]:
            _peak.update(day=day, n=n, at=time.strftime("%H:%M"))


def _prune(now):
    for k in [k for k, (t, _, _) in _seen.items() if now - t > WINDOW]:
        del _seen[k]


def snapshot():
    now = time.time()
    with _lock:
        _prune(now)
        where = {w: 0 for w in ("home", "surah", "ask", "other")}
        acts = {"reel": 0, "listen": 0, "ask": 0}
        for _, w, a in _seen.values():
            where[w] += 1
            if a in acts:
                acts[a] += 1
        today = time.strftime("%Y-%m-%d")
        peak = dict(_peak) if _peak["day"] == today else {"n": len(_seen), "at": time.strftime("%H:%M")}
    return {"now": len(_seen), "where": where, "acts": acts, "peak": peak["n"], "peak_at": peak["at"],
            "time": time.strftime("%H:%M:%S")}
