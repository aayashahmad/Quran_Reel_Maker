"""Protection for the site's data (the Kashmiri recordings, backgrounds, translations) and its server:

- Only this website may use the data addresses: requests that a browser marks as coming from another
  site (Sec-Fetch-Site: cross-site) are refused, so other sites can't embed or pull them.
- Speed limits per visitor, so nobody can bulk-download all recordings or flood the video maker.
- Security headers on every page.

Nothing here can stop someone recording audio while it plays; it makes copying in bulk impractical."""
import hashlib
import hmac
import threading
import time
from collections import defaultdict, deque

from flask import abort, jsonify, request

# path prefix: (requests allowed, per seconds) for one visitor
LIMITS = {
    "/api/generate": (20, 600),
    "/api/finish-video": (20, 600),
    "/api/surah/": (60, 600),
    "/api/meta": (60, 600),
    "/api/guide": (60, 600),
    "/api/ping": (240, 600),        # one open tab pings every 30 s
    "/api/audio/": (600, 600),      # a long reel made on the device needs a few hundred
    "/bg/": (120, 600),
    "/files/": (120, 600),
}
DATA_PATHS = ("/api/", "/bg/", "/files/")
_hits, _lock = defaultdict(deque), threading.Lock()

CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline'",           # the page's own inline script
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    "img-src 'self' data: blob:",
    "media-src 'self' blob: https://verses.quran.com https://cdn.islamic.network",
    "connect-src 'self' https://verses.quran.com https://cdn.islamic.network",
    "frame-ancestors 'none'",
    "form-action 'self'",
    "base-uri 'self'",
    "object-src 'none'",
])
HEADERS = {
    "Content-Security-Policy": CSP,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}


# SHA-256 of the Cloudflare Worker's secret (a Worker secret, also in ~/.quranreel-proxy-secret on the laptop):
# the backup can recognise the Worker without the secret itself being stored here or on the server.
PROXY_SECRET_SHA256 = "e9afbaf226cdb060c7adee1927b60e4600b7afcdabcc6c7005ff11ef33834987"


def _from_worker():
    sent = request.headers.get("X-Proxy-Secret", "")
    return bool(sent) and hmac.compare_digest(hashlib.sha256(sent.encode()).hexdigest(), PROXY_SECRET_SHA256)


def _visitor():
    # through the tunnel every request comes from 127.0.0.1; Cloudflare names the real visitor. On the backup
    # server requests come from the Cloudflare Worker, which passes the visitor on with its secret.
    if _from_worker():
        return request.headers.get("X-Visitor-IP") or "?"
    return request.headers.get("CF-Connecting-IP") or request.remote_addr or "?"


def _too_many(prefix, limit, window):
    key = (_visitor(), prefix)
    now = time.time()
    with _lock:
        q = _hits[key]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            return True
        q.append(now)
        if len(_hits) > 50_000:              # forget idle visitors so memory stays small
            for k in [k for k, v in _hits.items() if not v or now - v[-1] > 3600]:
                del _hits[k]
        return False


def check():
    """Runs before every request."""
    path = request.path
    if path.startswith(DATA_PATHS) and request.headers.get("Sec-Fetch-Site") == "cross-site":
        abort(403)
    for prefix, (limit, window) in LIMITS.items():
        if path.startswith(prefix) and _too_many(prefix, limit, window):
            resp = jsonify(error="Too many requests. Please wait a few minutes and try again.")
            resp.status_code = 429
            resp.headers["Retry-After"] = str(window)
            return resp
    return None


def headers(resp):
    """Runs after every request."""
    for k, v in HEADERS.items():
        resp.headers.setdefault(k, v)
    if request.path.startswith(DATA_PATHS):
        resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    return resp


def setup(app):
    app.before_request(check)
    app.after_request(headers)
