"""Is a hadith video due now? Standard library only, so the workflow can ask in seconds before installing
anything. Slot n is due once its time (SLOT_TIMES, local) has passed today and it is not uploaded yet.
Prints due=true/false (also to $GITHUB_OUTPUT). FORCE=1 (manual runs) always says due."""
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent


def slot_times():
    return [t.strip() for t in os.getenv("SLOT_TIMES", "12:00,20:00").split(",") if t.strip()]


def due_slot(now=None, db_path=None):
    """The first slot number that is due and not uploaded, or None."""
    now = now or datetime.now(ZoneInfo(os.getenv("TIMEZONE", "Asia/Kolkata")))
    date = now.date().isoformat()
    db = sqlite3.connect(db_path or os.getenv("HADITH_DB", str(HERE / "history.sqlite")))
    try:
        done = {r[0] for r in db.execute("SELECT day FROM videos WHERE status = 'uploaded' AND day LIKE ?", (date + "%",))}
    except sqlite3.OperationalError:
        done = set()
    for n, t in enumerate(slot_times(), 1):
        hh, mm = (int(x) for x in t.split(":"))
        if (now.hour, now.minute) < (hh, mm):
            return None                                   # later slots are not due yet either
        if (date if n == 1 else f"{date}#{n}") not in done:
            return n
    return None


if __name__ == "__main__":
    due = os.getenv("FORCE") == "1" or due_slot() is not None
    print(f"due={'true' if due else 'false'}")
    if os.getenv("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"due={'true' if due else 'false'}\n")
