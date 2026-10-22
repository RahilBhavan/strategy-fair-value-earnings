"""S&P Composite 1500 financial viability rule, as written in the S&P U.S. Indices Methodology (July 2026).

Quoted rule (methodology p. 9, "Financial Viability", S&P Composite 1500 bullet):
    "Generally Accepted Accounting Principles (GAAP) net income from continuing operations must be
     positive for: the most recent quarter, and the sum of the most recent four consecutive quarters"

This module encodes only that screen. It does not model market capitalization (US$22.7B+), float-adjusted
market cap, IWF >= 0.1, liquidity (FALR >= 0.75, 250,000 shares/month), sector balance, domicile, or the
Index Committee's discretion ("Constituent selection is at the discretion of the Index Committee").
"""
import math
from dataclasses import dataclass
from datetime import date, timedelta

METHODOLOGY_REL = "spdji/methodology-sp-us-indices.pdf"
RULE_QUOTE = ("Generally Accepted Accounting Principles (GAAP) net income from continuing operations must be "
              "positive for: o the most recent quarter, and o the sum of the most recent four consecutive quarters")


@dataclass(frozen=True)
class Verdict:
    passes: bool
    latest_quarter: float
    trailing_four: float
    reason: str


def financial_viability(quarters):
    """quarters: chronological net income from continuing operations, most recent last.

    Needs four *consecutive* quarters; a gap or fewer than four raises, because the rule is undefined there.
    Zero is not positive, so a quarter or sum of exactly 0 fails."""
    q = list(quarters)
    if len(q) < 4:
        raise ValueError("the rule needs the most recent four consecutive quarters")
    if any(v is None or not math.isfinite(v) for v in q[-4:]):
        raise ValueError("missing quarter inside the four-quarter window")
    last, t4 = q[-1], sum(q[-4:])
    if last <= 0 and t4 <= 0:
        reason = "latest quarter and trailing four quarters not positive"
    elif last <= 0:
        reason = "latest quarter not positive"
    elif t4 <= 0:
        reason = "trailing four quarters not positive"
    else:
        reason = "passes"
    return Verdict(last > 0 and t4 > 0, last, t4, reason)


def trailing_series(by_quarter):
    """{quarter_end: Verdict} for every quarter with four consecutive quarters of history."""
    ends = sorted(by_quarter)
    out = {}
    for i in range(3, len(ends)):
        window = ends[i - 3:i + 1]
        ordinals = [e.year * 4 + (e.month - 1) // 3 for e in window]
        if any(b - a != 1 for a, b in zip(ordinals, ordinals[1:])):
            continue
        out[ends[i]] = financial_viability([by_quarter[e] for e in window])
    return out


def third_friday(year, month):
    d = date(year, month, 1)
    first_friday = d + timedelta(days=(4 - d.weekday()) % 7)
    return first_friday + timedelta(days=14)


def checkpoints(after, n):
    """The next n quarterly rebalance dates (third Friday of Mar/Jun/Sep/Dec) after `after`.

    S&P 500 additions can happen at any time ("changes ... can be made at any time"); the quarterly dates are
    used here only as regular checkpoints."""
    out, y, m = [], after.year, after.month
    while len(out) < n:
        if m in (3, 6, 9, 12):
            d = third_friday(y, m)
            if d > after:
                out.append(d)
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def latest_reported_quarter(checkpoint, filing_lag_days=45):
    """Most recent quarter-end whose 10-Q/10-K would be public before the announcement (about two weeks before
    the checkpoint). Assumption: filings arrive within `filing_lag_days` (Strategy filed in 33-50 days in
    2025-2026); the 10-K deadline is later, so Q4 uses 60 days."""
    announce = checkpoint - timedelta(days=14)
    y, m = announce.year, announce.month
    candidates = []
    for yy in (y - 1, y):
        for mm, dd in ((3, 31), (6, 30), (9, 30), (12, 31)):
            qe = date(yy, mm, dd)
            lag = 60 if mm == 12 else filing_lag_days
            if qe + timedelta(days=lag) <= announce:
                candidates.append(qe)
    return max(candidates)
