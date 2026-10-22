"""Plain-text access to cached filings and the curated facts that XBRL does not carry.

Each curated fact stores the exact quote it came from; tests assert the quote is present in the cached filing
and that its magnitude appears in the quote. A frozen-file hash also detects curated edits;
signs and table-column interpretation still require source review."""
import csv
import html
import re
from datetime import date
from functools import lru_cache

from .sources import RAW, ROOT, provenance

CURATED = ROOT / "data" / "curated" / "text_facts.csv"


@lru_cache(maxsize=None)
def text(rel):
    raw = (RAW / rel).read_text(errors="ignore")
    raw = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(raw)).strip()


def load_curated():
    """{key: dict(value=float, period_end=date, unit, source, quote, url, fetched_utc)}"""
    out = {}
    with CURATED.open() as f:
        for r in csv.DictReader(f):
            prov = provenance(r["source"])
            out[r["key"]] = {
                "value": float(r["value"]), "unit": r["unit"],
                "period_end": date.fromisoformat(r["period_end"]) if r["period_end"] else None,
                "source": r["source"], "quote": r["quote"], "url": prov["url"], "fetched_utc": prov["fetched_utc"],
            }
    return out
