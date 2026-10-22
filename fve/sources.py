"""Fetch and cache primary-source documents. Each cached file gets a row in data/raw/manifest.csv
(path, url, fetched_utc, sha256, bytes) so every number can be traced to a URL and fetch date."""
import csv
import hashlib
import os
import pathlib
import time
import urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
MANIFEST = RAW / "manifest.csv"

# SEC returned HTTP 403 ("Undeclared Automated Tool") on 2026-10-21 for the requested
# "RahilBhavan-research (github.com/RahilBhavan)" string. data.sec.gov accepted a name-only string, but
# www.sec.gov/Archives required a contact email. Set SEC_USER_AGENT="<name> <email>" to fetch filings;
# the email is never stored in this repository.
SEC_UA = os.environ.get("SEC_USER_AGENT", "Rahil Bhavan research")
_last = [0.0]


def _manifest():
    if not MANIFEST.exists():
        return {}
    with MANIFEST.open() as f:
        return {r["path"]: r for r in csv.DictReader(f)}


def _write_manifest(rows):
    with MANIFEST.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["path", "url", "fetched_utc", "sha256", "bytes"])
        w.writeheader()
        for k in sorted(rows):
            w.writerow(rows[k])


def provenance(rel):
    """Return the manifest row (url, fetched_utc) for a cached file."""
    return _manifest()[rel]


def fetch(url, rel, refresh=False, ua=None):
    """Return bytes for url, cached at data/raw/<rel>. Rate-limited to <= 5 req/s."""
    path = RAW / rel
    if path.exists() and not refresh:
        return path.read_bytes()
    wait = 0.2 - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={"User-Agent": ua or SEC_UA, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read()
    _last[0] = time.time()
    if b"Undeclared Automated Tool" in body[:2000]:
        raise RuntimeError(f"SEC rejected the User-Agent for {url}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    rows = _manifest()
    rows[rel] = {"path": rel, "url": url,
                 "fetched_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                 "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}
    _write_manifest(rows)
    return body
