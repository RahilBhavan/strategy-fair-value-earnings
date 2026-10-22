"""Corporate alternative minimum tax (CAMT) exposure under three regimes. Research model, not tax advice.

Regimes (sources in docs/camt.md):
  A  interim_fvi   Notice 2025-49 section 5 "FVI exclusion option": AFSI disregards fair value measurement
                   adjustments on digital assets not marked to market for regular tax. Unrealized bitcoin gains
                   and losses leave AFSI; realized gains on sale come back in (section 5.05(3)).
  B  proposed_2024 2024 proposed regulations without the FVI option: unrealized gains stay in AFSI, and the
                   ASU 2023-08 cumulative-effect amount is spread ratably over four years (proposed
                   section 1.56A-17(c)(3)(ii)(A)), 2025-2028.
  C  statute_only  Unrealized gains stay in AFSI; the cumulative-effect adjustment (a retained-earnings entry)
                   never enters AFSI.

Simplifications (assumptions): AFSI ~= pre-tax GAAP income (ignores state-tax, depreciation, pension and other
section 56A adjustments); regular federal tax ~= 0, so CAMT ~= tentative minimum tax; no CAMT foreign tax credit;
the applicability test ignores FSNOLs (proposed section 1.59-2(c)(1)(ii)(B) disregards section 1.56A-23).
"""
import math
from dataclasses import dataclass

RATE = 0.15
THRESHOLD = 1_000_000_000
FSNOL_CAP = 0.80
REGIMES = ("interim_fvi", "proposed_2024", "statute_only")


@dataclass(frozen=True)
class Year:
    year: int
    pretax: float               # GAAP pre-tax income
    btc_unrealized: float = 0.0  # fair-value gain (loss) included in pretax (0 before 2025)
    btc_realized: float = 0.0    # gain on bitcoin sold, measured against cost (CAMT basis), not in pretax gain line


def afsi(y, regime, cumulative_effect=0.0):
    """AFSI before FSNOLs for one year under a regime."""
    if regime == "interim_fvi":
        return y.pretax - y.btc_unrealized + y.btc_realized
    if regime == "proposed_2024":
        spread = cumulative_effect / 4 if 2025 <= y.year <= 2028 else 0.0
        return y.pretax + spread
    if regime == "statute_only":
        return y.pretax
    raise ValueError(regime)


def run(years, regime, cumulative_effect=0.0, first_test_end=2022):
    """Walk years in order. Returns per-year dicts: afsi, 3-yr average, applicable, fsnol used, camt.

    A corporation is applicable for year T if the 3-year average AFSI for any period ending in a year before T
    (and after 2021) exceeds $1B; once applicable it stays applicable (termination rules not modelled)."""
    ys = sorted(years, key=lambda y: y.year)
    if len({y.year for y in ys}) != len(ys) or any(not all(math.isfinite(v) for v in
            (y.pretax, y.btc_unrealized, y.btc_realized)) for y in ys):
        raise ValueError("duplicate year or nonfinite CAMT input")
    a = {y.year: afsi(y, regime, cumulative_effect) for y in ys}
    fsnol, applicable, out = 0.0, False, []
    for y in ys:
        t = y.year
        prev3 = [a.get(t - k) for k in (3, 2, 1)]
        if None not in prev3 and t - 1 >= first_test_end and sum(prev3) / 3 > THRESHOLD:
            applicable = True
        avg_prior = sum(prev3) / 3 if None not in prev3 else None
        used, camt = 0.0, 0.0
        if a[t] > 0:
            used = min(fsnol, FSNOL_CAP * a[t]) if t >= 2020 else 0.0
            if applicable:
                camt = RATE * (a[t] - used)
            fsnol -= used
        elif t >= 2020:  # FSNOLs arise for taxable years ending after 2019
            fsnol += -a[t]
        out.append({"year": t, "afsi": a[t], "avg_prior_3": avg_prior, "applicable": applicable,
                    "fsnol_used": used, "fsnol_after": fsnol, "camt": camt})
    return out
