"""Is a hadith video due now? Standard library only, so the workflow can ask in seconds before installing
anything. Slot n is due once its time (SLOT_TIMES, local) has passed today and it is not uploaded yet.
Slots in LAPTOP_SLOTS (all three by default) are made by the owner's Mac (RUNNER=laptop, on time, with the Hayatus
narrator's voice for Urdu); GitHub (any other RUNNER) makes one only when the Mac has not done so LAPTOP_GRACE_MIN
later (the Mac is off or asleep). GitHub alone was not enough: its scheduled runs come hours late or not at all.
Prints due=true/false (also to $GITHUB_OUTPUT). FORCE=1 (manual runs) always says due."""
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent


def slot_times():
    return [t.strip() for t in os.getenv("SLOT_TIMES", "09:00,15:00,21:00").split(",") if t.strip()]


def laptop_slots():
    return {int(x) for x in os.getenv("LAPTOP_SLOTS", "1,2,3").split(",") if x.strip()}


def due_slot(now=None, db_path=None):
    """The first slot number that is due and not uploaded, or None."""
    now = now or datetime.now(ZoneInfo(os.getenv("TIMEZONE", "Asia/Kolkata")))
    date = now.date().isoformat()
    db = sqlite3.connect(db_path or os.getenv("HADITH_DB", str(HERE / "history.sqlite")))
    try:
        done = {r[0] for r in db.execute("SELECT day FROM videos WHERE status = 'uploaded' AND day LIKE ?", (date + "%",))}
    except sqlite3.OperationalError:
        done = set()
    runner, grace = os.getenv("RUNNER", ""), int(os.getenv("LAPTOP_GRACE_MIN", "90"))
    mine = laptop_slots()
    for n, t in enumerate(slot_times(), 1):
        hh, mm = (int(x) for x in t.split(":"))
        if (now.hour, now.minute) < (hh, mm):
            return None                                   # later slots are not due yet either
        if (date if n == 1 else f"{date}#{n}") in done:
            continue
        if runner == "laptop" and n not in mine:
            continue                                      # the Mac makes only its own slots
        if runner and runner != "laptop" and n in mine and now.hour * 60 + now.minute < hh * 60 + mm + grace:
            continue                                      # still the Mac's turn
        return n
    return None


if __name__ == "__main__":
    due = os.getenv("FORCE") == "1" or due_slot() is not None
    print(f"due={'true' if due else 'false'}")
    if os.getenv("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"due={'true' if due else 'false'}\n")
