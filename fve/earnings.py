"""Quarterly GAAP earnings model for Strategy under fair-value accounting (ASU 2023-08, adopted 2025-01-01).

    gain  = H_end * P_end - H_begin * P_begin - (C_end - C_begin)      bitcoin fair-value gain
    tax   = r * (max(U_end, 0) - max(U_begin, 0)),  U = H * P - C      deferred tax on the unrealized position
    other = median of the previous four quarters' (pre-tax income - bitcoin gain)
    NI    = gain - tax + other

H is bitcoin held, P the BTC-USD price, C the cost basis. The tax line encodes a mechanism Strategy describes in
its filings: a deferred tax liability on unrealized gains when fair value exceeds cost, and a full valuation
allowance on the deferred tax asset when it is below cost (Q1 2026 onward), so losses below cost get no tax
benefit. r is calibrated once, from the adoption-date balance sheet (2025-01-01), and is then held fixed.
These are model assumptions, not Strategy's tax computation.
"""
from dataclasses import dataclass, field
from datetime import date
from statistics import median

from . import btc, xbrl
from .filings import load_curated

PRETAX = "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"
K = 1000.0  # XBRL USD -> curated "USD_thousands"


@dataclass
class Quarter:
    end: date
    units: float                  # BTC held at quarter end
    cost: float                   # cost basis, USD
    fair_value: float | None      # reported carrying value, USD
    btc_gain: float | None        # reported gain (loss) on digital assets, USD
    pretax: float | None
    tax: float | None
    net_income: float | None
    net_income_common: float | None
    sources: dict = field(default_factory=dict)
    sale_adjustment: float = 0.0  # sale proceeds minus original cost removed

    @property
    def filing_price(self):
        return self.fair_value / self.units if self.fair_value else None


def _cur(c, key):
    v = c[key]
    scale = {"USD_thousands": K, "USD_billions": 1e9, "BTC": 1.0}[v["unit"]]
    return v["value"] * scale


def history():
    """Fair-value-era quarters (2024-12-31 opening position through 2026-06-30) plus the Q3 2026 8-K estimate."""
    cf, c = xbrl.load(), load_curated()
    units = {e: f["val"] for e, f in xbrl.instants(cf, "CryptoAssetNumberOfUnits", "Bitcoin").items()}
    for k in ("units_2025q1", "units_2025q2", "units_2025q3"):
        units[c[k]["period_end"]] = _cur(c, k)
    fv = {e: f["val"] for e, f in xbrl.instants(cf, "CryptoAssetFairValue").items()}
    for e, f in xbrl.instants(cf, "IndefiniteLivedIntangibleAssetsExcludingGoodwill").items():
        if date(2025, 3, 31) <= e <= date(2025, 9, 30):
            fv[e] = f["val"]
    fv[date(2024, 12, 31)] = fv.pop(date(2025, 1, 1))  # opening fair value on adoption
    cost = {e: f["val"] for e, f in xbrl.instants(cf, "CryptoAssetCost").items()}
    purch = {e: v[0] for e, v in xbrl.quarterly(cf, "CryptoAssetPurchase").items()}
    purch[date(2025, 9, 30)] = _cur(c, "purchases_2025q3")
    fy25 = xbrl.annual(cf, "CryptoAssetPurchase")[2025]
    purch[date(2025, 12, 31)] = fy25 - _cur(c, "purchases_2025_9m")
    for e in (date(2025, 3, 31), date(2025, 6, 30), date(2025, 9, 30)):
        prev = max(d for d in cost if d < e)
        cost[e] = cost[prev] + purch[e]
    gain = {c[k]["period_end"]: _cur(c, k) for k in
            ("btc_gain_2025q1", "btc_gain_2025q2", "btc_gain_2025q3", "btc_gain_2026q1", "btc_gain_2026q2")}
    gain[date(2025, 12, 31)] = _cur(c, "btc_gain_2025fy") - sum(gain[date(2025, m, d)] for m, d in
                                                                ((3, 31), (6, 30), (9, 30)))
    pre = {e: v[0] for e, v in xbrl.quarterly(cf, PRETAX).items()}
    tax = {e: v[0] for e, v in xbrl.quarterly(cf, "IncomeTaxExpenseBenefit").items()}
    ni = {e: v[0] for e, v in xbrl.quarterly(cf, "NetIncomeLoss").items()}
    nic = {e: v[0] for e, v in xbrl.quarterly(cf, "NetIncomeLossAvailableToCommonStockholdersBasic").items()}
    out = []
    for e in xbrl.quarter_ends(date(2024, 12, 31), date(2026, 6, 30)):
        out.append(Quarter(e, units[e], cost[e], fv[e], gain.get(e), pre.get(e), tax.get(e), ni.get(e), nic.get(e)))
    out[-1].sale_adjustment = _cur(c, "sale_proceeds_2026q2") - _cur(c, "sale_cost_removed_2026q2")
    q3 = date(2026, 9, 30)
    out.append(Quarter(q3, _cur(c, "q3_2026_units"), _cur(c, "q3_2026_cost"), _cur(c, "q3_2026_est_carrying_value"),
                       _cur(c, "q3_2026_est_gain"), None, _cur(c, "q3_2026_est_deferred_tax"), None, None,
                       {"note": "Strategy 8-K preliminary estimate, unaudited (filed 2026-10-05)"}))
    return out


def other_income_history():
    """{quarter_end: pre-tax income excluding bitcoin gains/impairments}, 2023 onward (impairment era included)."""
    cf, hist = xbrl.load(), {q.end: q for q in history()}
    pre = {e: v[0] for e, v in xbrl.quarterly(cf, PRETAX).items()}
    imp = {e: v[0] for e, v in xbrl.quarterly(cf, "ImpairmentOfIntangibleAssetsExcludingGoodwill").items()}
    out = {}
    for e, p in pre.items():
        if e < date(2023, 1, 1):
            continue
        if e in hist and hist[e].btc_gain is not None and e >= date(2025, 3, 31):
            out[e] = p - hist[e].btc_gain
        elif e in imp:
            out[e] = p + imp[e]
    return dict(sorted(out.items()))


def calibrate_tax_rate():
    """r = deferred tax liability (net) / unrealized gain at adoption, 2025-01-01. Assumption: one blended rate."""
    cf = xbrl.load()
    dtl = xbrl.instants(cf, "DeferredIncomeTaxLiabilitiesNet")[date(2025, 1, 1)]["val"]
    fv = xbrl.instants(cf, "CryptoAssetFairValue")[date(2025, 1, 1)]["val"]
    cost = xbrl.instants(cf, "CryptoAssetCost")[date(2024, 12, 31)]["val"]
    return dtl / (fv - cost)


@dataclass(frozen=True)
class Prediction:
    gain: float
    tax: float
    other: float

    @property
    def net_income(self):
        return self.gain - self.tax + self.other


def predict(h_b, p_b, c_b, h_e, p_e, c_e, other, r, sale_adjustment=0.0):
    gain = h_e * p_e - h_b * p_b - (c_e - c_b) + sale_adjustment
    tax = r * (max(h_e * p_e - c_e, 0.0) - max(h_b * p_b - c_b, 0.0))
    return Prediction(gain, tax, other)


def other_forecast(other_hist, before):
    prior = [v for e, v in other_hist.items() if e < before][-4:]
    return median(prior) if prior else 0.0


def backtest(price_source="coinbase"):
    """Back-predict each fair-value quarter from public inputs only: holdings and cost basis from the filing,
    BTC price from Coinbase daily closes (or the filing-implied price), `other` from earlier quarters."""
    r, hist, oh = calibrate_tax_rate(), history(), other_income_history()
    closes = btc.daily_closes() if price_source == "coinbase" else None
    rows = []
    for b, e in zip(hist, hist[1:]):
        if price_source == "coinbase":
            p_b, p_e = btc.close_on_or_before(closes, b.end), btc.close_on_or_before(closes, e.end)
        else:
            p_b, p_e = b.filing_price, e.filing_price
        pr = predict(b.units, p_b, b.cost, e.units, p_e, e.cost, other_forecast(oh, e.end), r, e.sale_adjustment)
        rows.append({"quarter_end": e.end, "price_begin": p_b, "price_end": p_e, "pred": pr,
                     "reported_gain": e.btc_gain, "reported_tax": e.tax, "reported_ni": e.net_income,
                     "reported_ni_common": e.net_income_common, "estimate": e.net_income is None})
    return r, rows
