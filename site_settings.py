"""Switches the site owner can flip on the admin page (/admin), saved in data/settings.json.
That file is not in git; laptop-heartbeat.sh keeps the copies on both computers in sync
(the newer "updated" time wins)."""
import json
import os
import threading
import time

from config import DATA

FILE = DATA / "settings.json"
SWITCHES = {   # name: (default, label, explanation)
    "kashmiri_audio": (False, "Kashmiri audio (AI voice)",
                       "Read the Kashmiri translation aloud with the Bolbosh AI voice, where its audio has been made."),
    "device_generation": (True, "Generate on this device",
                          "Offer visitors the option to make the reel in their own browser."),
}
_lock = threading.Lock()
_cache = {"mtime": None, "values": None}


def get():
    """Current value of every switch (defaults for any not saved yet)."""
    with _lock:
        try:
            mtime = FILE.stat().st_mtime
        except FileNotFoundError:
            mtime = None
        if _cache["values"] is None or mtime != _cache["mtime"]:
            saved = {}
            if mtime is not None:
                try:
                    saved = json.loads(FILE.read_text())
                except ValueError:
                    saved = {}           # half-written or damaged: fall back to the defaults
            _cache["values"] = {k: bool(saved.get(k, d)) for k, (d, _, _) in SWITCHES.items()}
            _cache["mtime"] = mtime
        return dict(_cache["values"])


def save(values):
    """Save the switches (unknown names are ignored), atomically."""
    clean = {k: bool(values.get(k, d)) for k, (d, _, _) in SWITCHES.items()}
    clean["updated"] = time.time()
    FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(clean, indent=2))
    os.replace(tmp, FILE)
