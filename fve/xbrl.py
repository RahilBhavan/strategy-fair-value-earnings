"""Quarterly series from the SEC companyfacts JSON for Strategy (CIK 1050446).

10-Qs report three-month facts for Q1-Q3; 10-Ks report only the fiscal year, so Q4 = FY - nine-month YTD.
When a period was reported more than once (later filings repeat comparatives), the latest filing wins and the
choice is recorded so a test can confirm values agree across filings."""
import json
from datetime import date

from .sources import RAW, provenance

FACTS_REL = "edgar/companyfacts_CIK0001050446.json"


def load(rel=FACTS_REL):
    return json.loads((RAW / rel).read_text())


def _d(s):
    return date.fromisoformat(s)


PERIODIC_FORMS = {"10-K", "10-Q", "10-K/A", "10-Q/A"}


def facts(cf, tag, unit="USD", ns="us-gaap"):
    """Facts for a tag from periodic reports only (proxy statements repeat figures with rounding)."""
    return [f for f in cf["facts"][ns][tag]["units"][unit] if f["form"] in PERIODIC_FORMS]


def _latest(rows):
    return max(rows, key=lambda f: (f["filed"], f["accn"]))


def durations(cf, tag, unit="USD"):
    """{(start, end): fact} with the latest filing for each period."""
    out = {}
    for f in facts(cf, tag, unit):
        if "start" not in f:
            continue
        k = (_d(f["start"]), _d(f["end"]))
        out.setdefault(k, []).append(f)
    return {k: _latest(v) for k, v in out.items()}


def instants(cf, tag, unit="USD"):
    out = {}
    for f in facts(cf, tag, unit):
        if "start" in f:
            continue
        out.setdefault(_d(f["end"]), []).append(f)
    return {k: _latest(v) for k, v in out.items()}


def quarter_ends(first, last):
    """Calendar quarter-end dates from first to last inclusive."""
    out, y, q = [], first.year, (first.month - 1) // 3 + 1
    while True:
        m = 3 * q
        d = date(y, m, 31 if m in (3, 12) else 30)
        if d > last:
            return out
        if d >= first:
            out.append(d)
        q += 1
        if q == 5:
            y, q = y + 1, 1


def quarter_start(end):
    return date(end.year, end.month - 2, 1)


def quarterly(cf, tag, unit="USD"):
    """{quarter_end: (value, how, accn)} where how is 'reported' or 'FY-9M'."""
    dur = durations(cf, tag, unit)
    out = {}
    for (s, e), f in dur.items():
        if 80 <= (e - s).days <= 100:
            out[e] = (f["val"], "reported", f["accn"])
    for (s, e), f in dur.items():
        if 350 <= (e - s).days <= 380 and e not in out:
            nine = dur.get((s, date(e.year, 9, 30)))
            if nine:
                out[e] = (f["val"] - nine["val"], "FY-9M", f"{f['accn']} - {nine['accn']}")
    return dict(sorted(out.items()))


def annual(cf, tag, unit="USD"):
    """{fiscal_year: value} for calendar-year duration facts."""
    out = {}
    for (s, e), f in durations(cf, tag, unit).items():
        if 350 <= (e - s).days <= 380 and s.month == 1 and s.day == 1:
            out[e.year] = f["val"]
    return dict(sorted(out.items()))


def source_url(accn):
    """EDGAR filing index URL for an accession number."""
    a = accn.split(" ")[0]
    return f"https://www.sec.gov/Archives/edgar/data/1050446/{a.replace('-', '')}/"


def companyfacts_provenance():
    return provenance(FACTS_REL)
