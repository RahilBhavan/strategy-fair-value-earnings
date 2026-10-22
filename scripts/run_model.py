"""Rebuild every result in results/ from the cached sources in data/raw/. Deterministic (seeded).

Run: .venv/bin/python scripts/run_model.py
"""
import csv
import json
import pathlib
import sys
from datetime import date

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from fve import btc, camt, earnings, simulate, sp_rule, xbrl  # noqa: E402
from fve.filings import load_curated  # noqa: E402
from fve.sources import provenance  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parents[1] / "results"
PRETAX = earnings.PRETAX


def j(o):
    if isinstance(o, date):
        return o.isoformat()
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    raise TypeError(type(o))


def dump(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, default=j) + "\n")


def quarterly_history():
    cf = xbrl.load()
    ni = xbrl.quarterly(cf, "NetIncomeLoss")
    nic = xbrl.quarterly(cf, "NetIncomeLossAvailableToCommonStockholdersBasic")
    st = simulate.state()
    closes = btc.daily_closes()
    fp = {q.end: q.filing_price for q in earnings.history()}
    series = {e: v[0] for e, v in ni.items() if e >= date(2022, 3, 31)}
    series[date(2026, 9, 30)] = st["known_ni"][date(2026, 9, 30)]
    verdicts = sp_rule.trailing_series(series)
    rows = []
    for e, v in series.items():
        vd = verdicts.get(e)
        rows.append({
            "quarter_end": e, "net_income_usd": round(v), "net_income_common_usd": nic[e][0] if e in nic else "",
            "trailing_four_usd": round(vd.trailing_four) if vd else "", "passes_viability": vd.passes if vd else "",
            "reason": vd.reason if vd else "", "btc_close_coinbase_utc": btc.close_on_or_before(closes, e),
            "btc_price_filing_implied": round(fp[e], 2) if e in fp and fp[e] else "",
            "accounting": "fair value (ASU 2023-08)" if e >= date(2025, 3, 31) else "cost less impairment",
            "status": "8-K preliminary estimate + modelled other income" if e == date(2026, 9, 30) else "reported",
            "source": (xbrl.source_url(ni[e][2]) if e in ni else provenance(
                "edgar/0001193125-26-413164/mstr-20261005.htm")["url"]),
            "derivation": ni[e][1] if e in ni else "gain - deferred tax + median other",
        })
    with (OUT / "quarterly_history.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: (v.isoformat() if isinstance(v, date) else v) for k, v in r.items()})
    return rows


def backtest():
    out = {}
    for src in ("coinbase", "filing"):
        r, rows = earnings.backtest(src)
        recs = []
        for x in rows:
            p = x["pred"]
            rec = {"quarter_end": x["quarter_end"], "price_begin": x["price_begin"], "price_end": x["price_end"],
                   "pred_gain": p.gain, "pred_tax": p.tax, "pred_other": p.other, "pred_ni": p.net_income,
                   "reported_gain": x["reported_gain"], "reported_tax": x["reported_tax"],
                   "reported_ni": x["reported_ni"], "estimate_only": x["estimate"]}
            if x["reported_ni"] is not None:
                rec["ni_error"] = p.net_income - x["reported_ni"]
                rec["ni_error_pct"] = rec["ni_error"] / abs(x["reported_ni"])
            rec["gain_error"] = p.gain - x["reported_gain"]
            rec["tax_error"] = p.tax - x["reported_tax"]
            recs.append(rec)
        errs = [abs(x["ni_error"]) for x in recs if "ni_error" in x]
        out[src] = {"tax_rate_r": r, "quarters": recs, "mean_abs_ni_error": sum(errs) / len(errs),
                    "max_abs_ni_error": max(errs), "n_quarters_scored": len(errs)}
    dump("backtest.json", out)
    return out


def camt_results():
    cf = xbrl.load()
    pre = xbrl.annual(cf, PRETAX)
    c = load_curated()
    cum = c["asu_adoption_digital_assets_effect"]["value"] * 1000
    gain25 = c["btc_gain_2025fy"]["value"] * 1000
    hist = [camt.Year(y, pre[y]) for y in range(2019, 2025)] + [camt.Year(2025, pre[2025], gain25)]
    st = simulate.state()
    h = {q.end: q for q in earnings.history()}
    pre_q = {e: v[0] for e, v in xbrl.quarterly(cf, PRETAX).items()}
    h1_pretax = pre_q[date(2026, 3, 31)] + pre_q[date(2026, 6, 30)]
    h1_gain = h[date(2026, 3, 31)].btc_gain + h[date(2026, 6, 30)].btc_gain
    q3_gain, q3_pretax = h[date(2026, 9, 30)].btc_gain, h[date(2026, 9, 30)].btc_gain + st["q3_2026_other"]

    def years_for(p26, p27, p28):
        g = simulate.quarter_components(st, np.array([[p26, p27, p28]]))["gain"][0]  # Q4 26, then annual hops
        # Treat each later year as one step from the prior year-end (quarterly steps are additive in gain).
        y26 = camt.Year(2026, h1_pretax + q3_pretax + g[0] + st["other"], h1_gain + q3_gain + g[0],
                         (c["sale_proceeds_2026q2"]["value"] - c["sale_cost_removed_2026q2"]["value"]) * 1000)
        y27 = camt.Year(2027, g[1] + 4 * st["other"], g[1])
        y28 = camt.Year(2028, g[2] + 4 * st["other"], g[2])
        return hist + [y26, y27, y28]

    history = {reg: camt.run(hist, reg, cum) for reg in camt.REGIMES}
    grid_prices = [60_000, 80_000, 100_000, 120_000, 150_000, 200_000]
    grid = {}
    for reg in camt.REGIMES:
        g = {}
        for p26 in grid_prices:
            for p27 in grid_prices:
                res = {r["year"]: r for r in camt.run(years_for(p26, p27, p27), reg, cum)}
                g[f"{p26}|{p27}"] = {"applicable_2027": res[2027]["applicable"], "camt_2027": res[2027]["camt"],
                                     "afsi_2026": res[2026]["afsi"], "afsi_2027": res[2027]["afsi"],
                                     "applicable_2028": res[2028]["applicable"]}
        grid[reg] = g
    # Bootstrap: year-end prices Dec 2026, Dec 2027, Dec 2028, base regime
    qs = [date(2026, 12, 31), date(2027, 12, 31), date(2028, 12, 31)]
    sim = {}
    for regime in ("demeaned", "raw"):
        px = simulate.simulate_quarter_prices(regime, qs, n_paths=5000)
        by = {reg: {"camt_2027": [], "camt_2028": [], "applicable_2027": 0, "applicable_2028": 0}
              for reg in camt.REGIMES}
        for row in px:
            ys = years_for(*row)
            for reg in camt.REGIMES:
                res = {r["year"]: r for r in camt.run(ys, reg, cum)}
                b = by[reg]
                b["camt_2027"].append(res[2027]["camt"])
                b["camt_2028"].append(res[2028]["camt"])
                b["applicable_2027"] += res[2027]["applicable"]
                b["applicable_2028"] += res[2028]["applicable"]
        n = len(px)
        sim[regime] = {reg: {"p_applicable_2027": b["applicable_2027"] / n,
                             "p_applicable_2028": b["applicable_2028"] / n,
                             "mean_camt_2027": float(np.mean(b["camt_2027"])),
                             "p90_camt_2027": float(np.percentile(b["camt_2027"], 90)),
                             "mean_camt_2028": float(np.mean(b["camt_2028"])),
                             "p90_camt_2028": float(np.percentile(b["camt_2028"], 90))}
                       for reg, b in by.items()}
    # Interim regime: bitcoin sales needed for realized gains to make Strategy applicable
    avg_cost = c["cost_2026_10_18"]["value"] * 1e9 / c["units_2026_10_18"]["value"]
    other_year = 4 * st["other"]
    sales = {p: (camt.THRESHOLD - other_year) / (1 - avg_cost / p) for p in (90_000, 100_000, 150_000, 200_000)}
    out = {"cumulative_effect_pretax": cum, "history": history, "grid_dec26_dec27": grid,
           "simulation_n_paths": 5000, "simulation": sim, "interim_sales_needed_per_year": sales,
           "avg_cost_per_btc": avg_cost, "other_income_per_year_assumed": other_year}
    dump("camt.json", out)
    return out


def main():
    OUT.mkdir(exist_ok=True)
    hist = quarterly_history()
    bt = backtest()
    probs = {f"{reg}{'_after_pref' if ap else ''}": simulate.pass_probabilities(reg, after_pref=ap)
             for reg in ("demeaned", "raw", "recent") for ap in (False, True)}
    dump("pass_probabilities.json", probs)
    bt_mae = bt["coinbase"]["mean_abs_ni_error"]
    thr = {"net_income": simulate.next_quarter_thresholds(),
           "net_income_after_preferred": simulate.next_quarter_thresholds(after_pref=True)}
    for t in thr.values():
        t["model_mae_btc_price_equivalent"] = bt_mae / t["ni_change_per_usd_of_btc_price"]
    thr["model_error"] = {
        "mean_abs_ni_error_usd": bt_mae, "max_abs_ni_error_usd": bt["coinbase"]["max_abs_ni_error"],
        "quarters_scored": bt["coinbase"]["n_quarters_scored"], "source": "results/backtest.json (coinbase)",
        "note": "Coinbase-price net-income model vs reported GAAP net income; thresholds inherit this error"}
    thr["march_2027_close_needed_for_june_2027_checkpoint"] = {
        "description": ("Key: BTC close on 2026-12-31. Value: BTC close on 2027-03-31 needed for Q1 2027 and "
                        "the four quarters Q2 2026..Q1 2027 to be positive on GAAP net income before "
                        "preferred dividends (June 2027 checkpoint)."),
        "by_december_31_2026_close": simulate.june_2027_grid()}
    dump("thresholds.json", thr)
    cm = camt_results()
    st = simulate.state()
    reported = {e: v[0] for e, v in xbrl.quarterly(xbrl.load(), "NetIncomeLoss").items()
                if e <= date(2026, 6, 30)}
    latest = max(reported)
    observed = sp_rule.trailing_series(reported)[latest]
    summary = {
        "latest_reported_quarter": str(latest),
        "reported_latest_net_income_usd": observed.latest_quarter,
        "reported_trailing_four_net_income_usd": observed.trailing_four,
        "reported_earnings_screen_pass": observed.passes,
        "probability_status": "Conditional scenarios, not index selection probability; Q3 2026 NI is modelled",
        "camt_status": "Simplified tentative minimum tax with assumed zero regular tax, not actual CAMT liability",
        "as_of": simulate.AS_OF, "tax_rate_r": st["r"], "q3_2026_net_income_estimate": st["known_ni"][date(2026, 9, 30)],
        "trailing_four_at_q3_2026": hist[-1]["trailing_four_usd"],
        "backtest_mean_abs_ni_error_coinbase": bt["coinbase"]["mean_abs_ni_error"],
        "backtest_max_abs_ni_error_coinbase": bt["coinbase"]["max_abs_ni_error"],
        "pass_probability_base": {str(r["checkpoint"]): r["p_pass"] for r in probs["demeaned"]["checkpoints"]},
        "pass_probability_base_reason": {str(r["checkpoint"]): r["reason"]
                                         for r in probs["demeaned"]["checkpoints"]},
        "next_quarter_pass_above": thr["net_income"]["pass_above"],
        "camt_history_applicable_any": {k: any(r["applicable"] for r in v) for k, v in cm["history"].items()},
    }
    dump("summary.json", summary)
    print(json.dumps(summary, indent=2, default=j))


if __name__ == "__main__":
    main()
