"""The optional donation box at the bottom of the site: a title, a short message, a QR code image (e.g. UPI) and
optionally a UPI ID or link, set on the admin page and shown only while the "donation" switch is on.
Stored in data/donation.json and data/donation_qr.png (not in git).

The backup server (Render) has no admin page of its own, so it copies the switches and the donation box from
the main site every few minutes (sync_from_main), and keeps showing the last copy while the laptop is off."""
import io
import json
import os
import threading
import time

import requests
from PIL import Image

from config import DATA

FILE = DATA / "donation.json"
QR = DATA / "donation_qr.png"
MAX_UPLOAD = 3 * 1024 * 1024
FIELDS = {"title": 80, "text": 400, "upi": 80, "link": 300}


def get():
    try:
        d = json.loads(FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        d = {}
    out = {k: str(d.get(k, ""))[:n] for k, n in FIELDS.items()}
    out["has_qr"] = QR.exists()
    out["version"] = str(d.get("version", ""))
    return out


def save(form, upload=None, remove_qr=False):
    """Save the text fields and, if given, a new QR image. Returns an error message or None."""
    link = form.get("link", "").strip()
    if link and not link.startswith(("https://", "upi://")):
        return "The link must start with https:// or upi://"
    if upload is not None and upload.filename:
        data = upload.read(MAX_UPLOAD + 1)
        if len(data) > MAX_UPLOAD:
            return "The image is too big (3 MB at most)."
        try:
            img = Image.open(io.BytesIO(data))
            img.verify()                                  # a real image, not something renamed
            img = Image.open(io.BytesIO(data))
            if img.format not in ("PNG", "JPEG", "WEBP", "GIF"):
                return "Please upload a PNG, JPG or WebP image."
            img = img.convert("RGBA")
            img.thumbnail((1000, 1000))
        except Exception:
            return "That file is not an image we can read."
        tmp = QR.with_suffix(".tmp")
        img.save(tmp, "PNG", optimize=True)               # re-drawn: no metadata or hidden content survives
        os.replace(tmp, QR)
    elif remove_qr:
        QR.unlink(missing_ok=True)
    d = {k: " ".join(form.get(k, "").split())[:n] for k, n in FIELDS.items()}
    d["version"] = str(int(time.time()))
    _write(d)
    return None


def _write(d):
    FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, FILE)


def sync_from_main(site, apply_settings, every=300):
    """Backup server only: copy the switches and the donation box from the main site (the laptop) every
    `every` seconds. Answers from the backup itself (X-Served-By: render-backup) are ignored."""
    def loop():
        while True:
            try:
                r = requests.get(site + "/api/public-config", timeout=20, headers={"X-Visitor-IP": "backup-sync"})
                if r.ok and r.headers.get("X-Served-By") != "render-backup":
                    cfg = r.json()
                    apply_settings(cfg.get("settings", {}))
                    don = cfg.get("donation", {})
                    if don.get("version") != get()["version"]:
                        if don.get("has_qr"):
                            img = requests.get(site + "/donation-qr.png?v=" + don.get("version", ""), timeout=20)
                            if img.ok and img.headers.get("X-Served-By") != "render-backup":
                                tmp = QR.with_suffix(".tmp")
                                tmp.write_bytes(img.content)
                                os.replace(tmp, QR)
                        else:
                            QR.unlink(missing_ok=True)
                        _write({k: don.get(k, "") for k in (*FIELDS, "version")})
            except (requests.RequestException, ValueError, OSError):
                pass
            time.sleep(every)
    threading.Thread(target=loop, daemon=True).start()
