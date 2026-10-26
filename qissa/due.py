"""Is a Qissa video due now? Standard library only. Video n of the day is due once QISSA_TIMES[n] (local) has
passed and fewer than n were uploaded today. Prints due=true/false (also to $GITHUB_OUTPUT); FORCE=1 = due."""
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

STATE = Path(__file__).resolve().parent / "published.json"


def times():
    return [t.strip() for t in os.getenv("QISSA_TIMES", "09:00,14:00").split(",") if t.strip()]


def due_count(now=None):
    """How many of today's videos are due by now (their time has passed)."""
    now = now or datetime.now(ZoneInfo(os.getenv("TIMEZONE", "Asia/Kolkata")))
    return sum(1 for t in times() if (now.hour, now.minute) >= tuple(int(x) for x in t.split(":")))


def uploaded_today(now=None):
    now = now or datetime.now(ZoneInfo(os.getenv("TIMEZONE", "Asia/Kolkata")))
    state = json.loads(STATE.read_text()) if STATE.exists() else []
    return sum(1 for e in state if e.get("day") == now.date().isoformat() and e.get("status") == "uploaded")


def is_due(now=None):
    return uploaded_today(now) < due_count(now)


if __name__ == "__main__":
    due = os.getenv("FORCE") == "1" or is_due()
    print(f"due={'true' if due else 'false'}")
    if os.getenv("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"due={'true' if due else 'false'}\n")
