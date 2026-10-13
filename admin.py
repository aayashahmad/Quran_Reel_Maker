"""Private admin page (/admin) for the site owner: log in with a password and flip the switches in
site_settings. The password is set on the computer itself with
    .venv/bin/python admin.py set-password
and only its hash is stored, in data/admin.json (not in git).

Safety: the hash uses werkzeug's scrypt; the login cookie is HttpOnly, Secure and SameSite=Strict
and lasts 12 hours; every form carries a per-session CSRF token; 5 wrong passwords from one
address lock it out for 15 minutes; pages are not cached or indexed."""
import getpass
import hmac
import json
import os
import secrets
import sys
import threading
import time
from datetime import timedelta
from urllib.parse import quote

from flask import Blueprint, abort, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

import cloudflare_stats
import dashboard
import donation
import site_settings
from config import DATA

ADMIN_FILE = DATA / "admin.json"
SECRET_FILE = DATA / "secret_key"
MAX_FAILS, LOCK_SECONDS = 5, 15 * 60
bp = Blueprint("admin", __name__)
_fails, _fails_lock = {}, threading.Lock()


def _private_write(path, text):
    """Write a file only this user can read."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(text)
    os.chmod(path, 0o600)


def setup(app):
    """Register the admin page on the Flask app, with a secret key kept in data/secret_key."""
    if not SECRET_FILE.exists():
        _private_write(SECRET_FILE, secrets.token_hex(32))
    app.secret_key = SECRET_FILE.read_text().strip()
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SECURE=True, SESSION_COOKIE_SAMESITE="Strict",
                      SESSION_COOKIE_NAME="qrm_admin", PERMANENT_SESSION_LIFETIME=timedelta(hours=12))
    app.register_blueprint(bp)


def _password_hash():
    try:
        return json.loads(ADMIN_FILE.read_text())["password_hash"]
    except (FileNotFoundError, ValueError, KeyError):
        return None


def _client():
    # Through the tunnel every request comes from 127.0.0.1; Cloudflare names the real visitor
    return request.headers.get("CF-Connecting-IP") or request.remote_addr or "?"


def _locked(ip):
    with _fails_lock:
        n, since = _fails.get(ip, (0, 0))
        if n >= MAX_FAILS and time.time() - since < LOCK_SECONDS:
            return True
        if n >= MAX_FAILS:
            _fails.pop(ip, None)          # lock-out over
        return False


def _failed(ip):
    with _fails_lock:
        n, since = _fails.get(ip, (0, time.time()))
        _fails[ip] = (n + 1, time.time() if n + 1 >= MAX_FAILS else since)


def is_admin():
    return bool(session.get("admin"))


def _csrf():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


def _check_csrf():
    sent = request.form.get("csrf", "")
    if not session.get("csrf") or not hmac.compare_digest(sent, session["csrf"]):
        abort(400)


def _page(**kw):
    resp = render_template("admin.html", csrf=_csrf(), **kw)
    return resp, 200, {"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow",
                       "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer"}


@bp.get("/admin")
def page():
    if not _password_hash():
        return _page(state="not-set")
    if not session.get("admin"):
        return _page(state="login")
    values = site_settings.get()
    switches = [dict(name=k, label=label, help=help_, on=values[k]) for k, (_, label, help_) in site_settings.SWITCHES.items()]
    msg = {"1": "Saved. The change is live now and reaches the backup server within 5 minutes.",
           "donation": "Donation box saved.", "cf": "Cloudflare connected.", "cf-off": "Cloudflare token removed."}
    return _page(state="settings", switches=switches, saved=msg.get(request.args.get("saved", "")),
                 error=request.args.get("error", "")[:200], d=dashboard.collect(), donation=donation.get())


@bp.post("/admin/login")
def login():
    _check_csrf()
    ip = _client()
    if _locked(ip):
        return _page(state="login", error="Too many wrong passwords. Try again in 15 minutes.")
    h = _password_hash()
    if not h or not check_password_hash(h, request.form.get("password", "")):
        _failed(ip)
        time.sleep(1)                     # slow down guessing
        return _page(state="login", error="Wrong password.")
    with _fails_lock:
        _fails.pop(ip, None)
    session.clear()
    session.permanent = True
    session["admin"] = True
    return redirect("/admin", code=303)


@bp.post("/admin/settings")
def save_settings():
    _check_csrf()
    if not session.get("admin"):
        return redirect("/admin", code=303)
    site_settings.save({k: request.form.get(k) == "on" for k in site_settings.SWITCHES})
    return redirect("/admin?saved=1", code=303)


def _admin_post(max_bytes=64 * 1024):
    """Common checks for admin forms: size, CSRF token, logged in."""
    if (request.content_length or 0) > max_bytes:
        abort(413)
    _check_csrf()
    if not session.get("admin"):
        abort(403)


@bp.post("/admin/donation")
def save_donation():
    _admin_post(donation.MAX_UPLOAD + 64 * 1024)
    err = donation.save(request.form, request.files.get("qr"), remove_qr=request.form.get("remove_qr") == "on")
    return redirect(f"/admin?error={quote(err)}#donation" if err else "/admin?saved=donation#donation", code=303)


@bp.post("/admin/cloudflare")
def save_cloudflare():
    _admin_post()
    if request.form.get("forget") == "1":
        cloudflare_stats.forget()
        return redirect("/admin?saved=cf-off#traffic", code=303)
    err = cloudflare_stats.save(request.form.get("token", ""), request.form.get("zone_id", ""))
    return redirect(f"/admin?error={quote(err)}#traffic" if err else "/admin?saved=cf#traffic", code=303)


@bp.post("/admin/logout")
def logout():
    _check_csrf()
    session.clear()
    return redirect("/admin", code=303)


def set_password():
    print("Set the password for quranreelmaker.xyz/admin (at least 12 characters).")
    while True:
        pw = getpass.getpass("New password: ")
        if len(pw) < 12:
            print("Too short, use at least 12 characters.")
            continue
        if getpass.getpass("Type it again: ") != pw:
            print("They don't match, try again.")
            continue
        break
    _private_write(ADMIN_FILE, json.dumps({"password_hash": generate_password_hash(pw)}))
    print(f"Saved (only a hash of it) in {ADMIN_FILE}.")


if __name__ == "__main__":
    if sys.argv[1:] == ["set-password"]:
        set_password()
    else:
        print("usage: python admin.py set-password")
