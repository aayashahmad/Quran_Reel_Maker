"""Cloudflare numbers for the admin dashboard: visitors, requests, page views, data served, threats blocked
and top countries for the last 30 days (Cloudflare's GraphQL Analytics API), and how often the Worker sent
visitors to the backup server.

Needs a Cloudflare API token with read-only analytics access ("Read analytics and logs" template), entered on
the admin page. It is kept only on this computer in data/cloudflare.json (readable by this user only) and
never shown again; answers are cached for 10 minutes."""
import json
import os
import threading
import time

import requests

from config import DATA

FILE = DATA / "cloudflare.json"
API = "https://api.cloudflare.com/client/v4"
ZONE_NAME = "quranreelmaker.xyz"
WORKER = "quranreelmaker-switching"
_cache, _lock = {"at": 0, "data": None}, threading.Lock()


def configured():
    return _creds() is not None


def _creds():
    try:
        d = json.loads(FILE.read_text())
        return d if d.get("token") else None
    except (FileNotFoundError, ValueError):
        return None


def save(token, zone_id=""):
    """Check the token against Cloudflare, find the zone if needed, and store it. Returns an error or None."""
    token, zone_id = token.strip(), zone_id.strip()
    h = {"Authorization": f"Bearer {token}"}
    try:
        v = requests.get(f"{API}/user/tokens/verify", headers=h, timeout=20).json()
        if not v.get("success"):
            return "Cloudflare did not accept this token."
        if not zone_id:
            z = requests.get(f"{API}/zones", params={"name": ZONE_NAME}, headers=h, timeout=20).json()
            if not z.get("success") or not z.get("result"):
                return "Token works, but it can't list zones: please also paste the Zone ID (Cloudflare > your domain > Overview, right side)."
            zone_id = z["result"][0]["id"]
            account_id = z["result"][0]["account"]["id"]
        else:
            account_id = ""
    except requests.RequestException:
        return "Could not reach Cloudflare. Try again."
    FILE.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump({"token": token, "zone_id": zone_id, "account_id": account_id}, f)
    os.chmod(FILE, 0o600)
    with _lock:
        _cache.update(at=0, data=None)
    return None


def forget():
    FILE.unlink(missing_ok=True)
    with _lock:
        _cache.update(at=0, data=None)


ZONE_QUERY = """query($zone: String!, $since: Date!) { viewer { zones(filter: {zoneTag: $zone}) {
  httpRequests1dGroups(limit: 31, filter: {date_geq: $since}, orderBy: [date_ASC]) {
    dimensions { date }
    sum { requests pageViews bytes cachedRequests threats countryMap { clientCountryName requests } }
    uniq { uniques } } } } }"""
WORKER_QUERY = """query($account: String!, $since: Time!) { viewer { accounts(filter: {accountTag: $account}) {
  workersInvocationsAdaptive(limit: 100, filter: {scriptName: "%s", datetime_geq: $since}) {
    sum { requests errors subrequests } } } } }""" % WORKER


def _gql(creds, query, variables):
    r = requests.post(f"{API}/graphql", json={"query": query, "variables": variables},
                      headers={"Authorization": f"Bearer {creds['token']}"}, timeout=30)
    d = r.json()
    if d.get("errors"):
        raise RuntimeError(d["errors"][0].get("message", "Cloudflare error"))
    return d["data"]


def stats():
    """{"days": [...], "totals": {...}, "countries": [...], "worker": {...} | None, "error": str | None}, cached."""
    creds = _creds()
    if not creds:
        return None
    with _lock:
        if _cache["data"] and time.time() - _cache["at"] < 600:
            return _cache["data"]
    out = {"days": [], "totals": {}, "countries": [], "worker": None, "error": None,
           "checked": time.strftime("%H:%M")}
    try:
        since = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 29 * 86400))
        groups = _gql(creds, ZONE_QUERY, {"zone": creds["zone_id"], "since": since})["viewer"]["zones"][0]["httpRequests1dGroups"]
        countries = {}
        for g in groups:
            s = g["sum"]
            out["days"].append({"date": g["dimensions"]["date"], "visitors": g["uniq"]["uniques"],
                                "requests": s["requests"], "views": s["pageViews"]})
            for c in s["countryMap"]:
                countries[c["clientCountryName"]] = countries.get(c["clientCountryName"], 0) + c["requests"]
        tot = lambda k: sum(g["sum"][k] for g in groups)
        out["totals"] = {"visitors": sum(g["uniq"]["uniques"] for g in groups), "requests": tot("requests"),
                         "views": tot("pageViews"), "bytes": tot("bytes"), "cached": tot("cachedRequests"),
                         "threats": tot("threats")}
        out["countries"] = sorted(countries.items(), key=lambda x: -x[1])[:8]
    except (requests.RequestException, RuntimeError, KeyError, IndexError, TypeError) as e:
        out["error"] = f"Cloudflare analytics: {e}"
    if creds.get("account_id"):
        try:
            since = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 29 * 86400))
            rows = _gql(creds, WORKER_QUERY, {"account": creds["account_id"], "since": since})["viewer"]["accounts"][0]["workersInvocationsAdaptive"]
            out["worker"] = {k: sum(r["sum"][k] for r in rows) for k in ("requests", "errors", "subrequests")}
        except (requests.RequestException, RuntimeError, KeyError, IndexError, TypeError):
            pass                                            # optional: the token may not cover Workers
    with _lock:
        _cache.update(at=time.time(), data=out)
    return out
