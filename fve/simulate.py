"""Seeded block bootstrap of BTC daily log returns -> quarterly earnings -> S&P financial viability by checkpoint.

Assumptions (all labelled in docs/findings.md):
- Holdings stay at the latest 8-K figure (848,517 BTC, cost $64.02B, 2026-10-18); no further buys or sales.
- `other` (non-bitcoin pre-tax income) is the median of the four quarters before each forecast quarter, held fixed.
- Quarter-end price = simulated close on the quarter-end date. Filing prices use 4 p.m. ET Coinbase; the
  back-test measures the error this introduces.
- Return regimes: 'demeaned' (full history, zero mean log drift; base case), 'raw' (full history with its
  drift), 'recent' (last four years, raw).
"""
from datetime import date, timedelta
from statistics import median

import numpy as np

from . import btc, earnings, sp_rule
from .filings import load_curated

AS_OF = date(2026, 10, 20)  # last complete Coinbase daily candle
SEED = 20261021
BLOCK = 20


def log_returns(closes, start=None, end=AS_OF):
    ds = sorted(d for d in closes if (start is None or d >= start) and d <= end)
    px = np.array([closes[d] for d in ds])
    return np.diff(np.log(px))


def regime_returns(name, closes):
    if name == "demeaned":
        r = log_returns(closes)
        return r - r.mean()
    if name == "raw":
        return log_returns(closes)
    if name == "recent":
        return log_returns(closes, start=AS_OF - timedelta(days=4 * 365))
    raise ValueError(name)


def block_bootstrap(returns, n_days, n_paths, rng, block=BLOCK):
    """Paths of cumulative log returns, shape (n_paths, n_days), built from contiguous blocks."""
    returns = np.asarray(returns)
    if block < 1 or n_days < 1 or n_paths < 1 or len(returns) < block or not np.isfinite(returns).all():
        raise ValueError("invalid bootstrap shape or returns")
    n_blocks = -(-n_days // block)
    starts = rng.integers(0, len(returns) - block + 1, size=(n_paths, n_blocks))
    idx = (starts[:, :, None] + np.arange(block)).reshape(n_paths, -1)[:, :n_days]
    return np.cumsum(returns[idx], axis=1)


def state():
    """Known inputs for the forecast: reported/estimated quarters and the opening position."""
    c = load_curated()
    hist = earnings.history()
    known_ni = {q.end: q.net_income for q in hist if q.net_income is not None}
    oh = earnings.other_income_history()
    q3 = hist[-1]
    other_q3 = earnings.other_forecast(oh, q3.end)
    known_ni[q3.end] = q3.btc_gain - q3.tax + other_q3        # Q3 2026 from the 8-K estimate
    pref = {q.end: q.net_income - q.net_income_common for q in hist if q.net_income_common is not None}
    return {
        "r": earnings.calibrate_tax_rate(), "known_ni": dict(sorted(known_ni.items())),
        "q3_2026_other": other_q3, "other": earnings.other_forecast(oh, date(2026, 12, 31)),
        "pref_dividends": pref, "pref_assumed": pref[date(2026, 6, 30)],
        "h0": q3.units, "c0": q3.cost, "p0": q3.filing_price,
        "h1": c["units_2026_10_18"]["value"], "c1": c["cost_2026_10_18"]["value"] * 1e9,
    }


def quarter_ni(st, prices):
    """prices: array (..., n_quarters) of quarter-end prices from Q4 2026 on -> net income per quarter."""
    return quarter_components(st, prices)["ni"]


def quarter_pretax(st, prices):
    c = quarter_components(st, prices)
    return c["gain"] + st["other"]


def quarter_components(st, prices):
    prices = np.asarray(prices, dtype=float)
    r, h, c = st["r"], st["h1"], st["c1"]
    h_prev, c_prev = st["h0"], st["c0"]
    p_prev = np.full(prices.shape[:-1], st["p0"])
    gains, nis = [], []
    for k in range(prices.shape[-1]):
        p = prices[..., k]
        gain = h * p - h_prev * p_prev - (c - c_prev)
        tax = r * (np.maximum(h * p - c, 0) - np.maximum(h_prev * p_prev - c_prev, 0))
        gains.append(gain)
        nis.append(gain - tax + st["other"])
        h_prev, c_prev, p_prev = h, c, p
    return {"gain": np.stack(gains, axis=-1), "ni": np.stack(nis, axis=-1)}


def simulate_quarter_prices(regime, quarters, n_paths=20000, seed=SEED):
    closes = btc.daily_closes()
    rng = np.random.default_rng(seed)
    days = [(q - AS_OF).days for q in quarters]
    paths = block_bootstrap(regime_returns(regime, closes), max(days), n_paths, rng)
    return closes[AS_OF] * np.exp(paths[:, [d - 1 for d in days]])


def future_quarter_ends(n):
    return earnings.xbrl.quarter_ends(date(2026, 12, 31), date(2030, 1, 1))[:n]


def pass_probabilities(regime, n_paths=20000, n_checkpoints=5, after_pref=False, seed=SEED):
    closes = btc.daily_closes()
    st = state()
    cps = sp_rule.checkpoints(date(2026, 10, 21), n_checkpoints)
    needed = [sp_rule.latest_reported_quarter(cp) for cp in cps]
    fut = [q for q in future_quarter_ends(8) if q <= max(needed)]
    p_start = closes[AS_OF]
    qprices = simulate_quarter_prices(regime, fut, n_paths, seed)
    ni = quarter_ni(st, qprices)
    known = dict(st["known_ni"])
    pref = st["pref_assumed"] if after_pref else 0.0
    if after_pref:
        known = {e: v - st["pref_dividends"].get(e, pref) for e, v in known.items()}
    ni = ni - pref
    known_ends = sorted(known)
    rows = []
    for cp, latest in zip(cps, needed):
        window = [e for e in known_ends + fut if e <= latest][-4:]
        cols = []
        for e in window:
            cols.append(np.full(n_paths, known[e]) if e in known else ni[:, fut.index(e)])
        m = np.stack(cols, axis=1)
        ok = (m[:, -1] > 0) & (m.sum(axis=1) > 0)
        rows.append({"checkpoint": cp, "latest_quarter": latest, "window": window,
                     "p_pass": float(ok.mean()), "p_latest_positive": float((m[:, -1] > 0).mean()),
                     "p_trailing_positive": float((m.sum(axis=1) > 0).mean()),
                     "deterministic": all(e in known for e in window)})
    q_summary = {str(q): {"p10": float(np.percentile(qprices[:, i], 10)),
                          "p50": float(np.percentile(qprices[:, i], 50)),
                          "p90": float(np.percentile(qprices[:, i], 90))} for i, q in enumerate(fut)}
    return {"regime": regime, "n_paths": n_paths, "seed": seed, "start_price": p_start, "as_of": AS_OF,
            "after_pref": after_pref, "checkpoints": rows, "quarter_end_price_pctiles": q_summary}


def _bisect(f, lo, hi, tol=1.0):
    """Smallest price in [lo, hi] where f(price) is True, assuming f is monotone increasing in price."""
    if not f(hi):
        return None
    while hi - lo > tol:
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if f(mid) else (mid, hi)
    return hi


def next_quarter_thresholds(after_pref=False):
    """BTC price on 2026-12-31 needed for Q4 2026 to pass each half of the test (Mar 2027 checkpoint)."""
    st = state()
    pref = st["pref_assumed"] if after_pref else 0.0
    known = st["known_ni"]
    if after_pref:
        known = {e: v - st["pref_dividends"].get(e, pref) for e, v in known.items()}
    prior3 = sum(known[e] for e in sorted(known)[-3:])

    def q4(p):
        return float(quarter_ni(st, np.array([p]))[0]) - pref
    latest = _bisect(lambda p: q4(p) > 0, 1_000, 1_000_000)
    trailing = _bisect(lambda p: prior3 + q4(p) > 0, 1_000, 1_000_000)
    return {"latest_quarter_positive_above": latest, "trailing_four_positive_above": trailing,
            "pass_above": max(latest, trailing), "prior_three_quarters_sum": prior3,
            "prior_three_quarters": sorted(known)[-3:], "after_pref": after_pref}


def june_2027_grid(dec_prices=(60_000, 70_000, 80_000, 90_000, 100_000, 120_000)):
    """For a given 2026-12-31 price, the 2027-03-31 price needed to pass at the June 2027 checkpoint."""
    st = state()
    known = st["known_ni"]
    q2, q3 = known[date(2026, 6, 30)], known[date(2026, 9, 30)]
    out = {}
    for d in dec_prices:
        def ok(m):
            n4, n1 = quarter_ni(st, np.array([d, m]))
            return n1 > 0 and q2 + q3 + n4 + n1 > 0
        out[d] = _bisect(ok, 1_000, 2_000_000)
    return out
