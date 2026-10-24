# Strategy fair-value earnings: bridge BTC accounting to an earnings eligibility screen

Strategy lost money in its latest reported quarters, so it fails the S&P 500's profit test; this model estimates the bitcoin price that would change that.

[![Offline verification](https://github.com/RahilBhavan/strategy-fair-value-earnings/actions/workflows/ci.yml/badge.svg)](https://github.com/RahilBhavan/strategy-fair-value-earnings/actions/workflows/ci.yml)

A local Python model of Strategy's earnings under bitcoin fair-value accounting. It applies the S&P earnings screen to reported quarters, finds the year-end BTC price that would pass it, and runs seeded BTC price scenarios. It measures its own error against six reported quarters. Financial cutoff: October 21, 2026; market candles end October 20.

## Results

### S&P 500 earnings screen

- **What it checks.** The [S&P U.S. Indices Methodology](https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-us-indices.pdf) (July 2026, p. 9; [archived copy](https://web.archive.org/web/20260908073946/https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-us-indices.pdf), read 2026-10-22) requires that "Generally Accepted Accounting Principles (GAAP) net income from continuing operations must be positive for: the most recent quarter, and the sum of the most recent four consecutive quarters". `fve/sp_rule.py` encodes that rule. Zero is not positive.
- **Result.** Strategy fails both halves. Latest reported quarter, June 30, 2026: net loss **$8,219,628,000**. Trailing four quarters: net loss **$30,413,926,000** (`results/summary.json`, from Strategy's [June 2026 10-Q](https://www.sec.gov/Archives/edgar/data/1050446/000105044626000044/mstr-20260630.htm), filed 2026-08-03).
- **Which earnings line.** The 10-Q reports "Net (loss) income" (Q2: -$8,219,628 thousand) before "Dividends on preferred stock" ($400,661 thousand). The methodology does not say which line counts, so the model uses "Net (loss) income" and reports after-preferred figures as a sensitivity. S&P's [Index Mathematics Methodology](https://web.archive.org/web/20261001061252/https://www.spglobal.com/spdji/en/documents/methodologies/methodology-index-math.pdf) (September 2026, p. 72) subtracts "Preferred Dividend and Other Adjustments" for its EPS data, but that is not the eligibility rule.

### Next pass price

<!-- generated:thresholds start -->
- **Next pass price:** a Coinbase BTC-USD daily close (UTC) on 2026-12-31 above **$86,459** makes Q4 2026 (2026-12-31) and the four quarters ending then positive on GAAP net income, so the modelled screen passes at the 2027-03-19 checkpoint. After preferred dividends the price is **$88,826**. Q4 alone turns positive above $83,570; the trailing-four sum binds because Q1–Q3 2026 sum to -$1,747m (Q3 is a preliminary-estimate model) (`results/thresholds.json`).
- **Model error:** the price model missed reported net income by $326.77m on average (max $824.74m) over 6 quarters. Near the threshold, net income moves about $605k per $1 of BTC price, so the mean error equals about $540 and the max about $1,364 of BTC price. Treat closes within that band as undecided.
- **`pass_probability_base`** keys are assumed quarterly rebalance dates (third Friday of March, June, September and December), not announced dates. 2026-12-18 is 0.0 because no simulated price enters its window: Q3 2026 is modelled positive, but the four quarters ending September 30, 2026 sum to -$14.18bn. `pass_probability_base_reason` in `results/summary.json` states this for every date.
<!-- generated:thresholds end -->

### Model error

![Model minus reported net income for six quarters, Q1 2025 to Q2 2026; the mean absolute error is $326.77m.](docs/assets/backtest.svg)

The price model missed reported net income by **$326.77 million** on average over six quarters (`results/backtest.json`). This is a model limit, not a code bug. With the filing's own BTC price, the modelled bitcoin gain matches the reported gain within $1 million in every quarter (`tests/test_model.py`). Q1 and Q2 2026 carry 74% of the total absolute error ($1,445.6m of $1,960.6m). With the filing's own BTC price, the mean error falls to $121.28m (`results/backtest.json`). The two causes are the price time (the model uses the midnight-UTC close, not the filing's 4:00 p.m. ET price) and a Q1 2026 tax valuation allowance the model does not track. The per-quarter bridge and both explanations are in [Earnings diagnostics](docs/earnings-diagnostics.md#why-the-model-missed-by-quarter).

### Scenarios

- Q3 2026 uses Strategy's preliminary 8-K gain and tax estimates plus modelled other income. It is not reported GAAP earnings.
- Price scenarios resample blocks of historical BTC daily returns in three regimes: `demeaned` (zero drift), `raw` (full history) and `recent` (last four years). Simplified corporate alternative minimum tax (CAMT) scenarios separate the fair value item (FVI) exclusion in IRS Notice 2025-49 from no-exclusion cases.

## How it works

`fve/xbrl.py` and `filings.py` load SEC facts; `earnings.py` bridges holdings, fair value, purchases/sales and a simplified tax proxy. `sp_rule.py` applies the positivity screen. `simulate.py` uses historical BTC return blocks. `camt.py` models simplified adjusted financial statement income (AFSI), CAMT applicability and tentative-tax sensitivities separately from GAAP deferred tax.

## Run it

CI installs Python 3.12.12 and 3.14.0 with NumPy 2.3.4 (`.github/workflows/ci.yml`). The last local run used Python 3.14.7. From this repository:

```bash
git clone https://github.com/RahilBhavan/strategy-fair-value-earnings.git
cd strategy-fair-value-earnings
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/snapshot.py
.venv/bin/python scripts/verify_sources.py
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/run_model.py
.venv/bin/python scripts/render_result.py
```

Observed: **43 tests pass**, none skipped (on a fresh clone the README-block test runs `scripts/run_model.py` itself). `render_result.py` rewrites the generated threshold lines in this README from `results/`. Installing packages needs network access. Restoring sources, tests and the demo run offline with no credentials. A second run reproduces the output hashes with the pinned NumPy version and seed. Optional source fetching needs a contact-bearing `SEC_USER_AGENT` for EDGAR.

## Repository layout

- `fve/`: source loading, accounting, screen, bootstrap and CAMT models.
- `scripts/`: restore, verify, optional fetch and deterministic demo.
- `snapshot/`: compressed source/curated-fact archive.
- `provenance/`: source URL/date/hash inventories.
- `tests/`: source, accounting, missing-input and stochastic checks.
- `docs/`: scope, methodology, CAMT research and validation.

## Documentation

- [Public design system](DESIGN.md): Rahil Design 3.3.0, shared tokens and visual review rules.
- [Scope and acceptance](docs/spec.md): local v1 contract.
- [Earnings diagnostics](docs/earnings-diagnostics.md): per-quarter error bridge, baseline comparisons and a five-minute example. Run `python scripts/diagnose_earnings.py`.
- [Methodology](docs/methodology.md): bridges, backtests and conditional scenarios.
- [CAMT research](docs/camt.md): AFSI exclusions, thresholds and omitted tax details.
- [Sources](docs/sources.md): primary-source checks and cache coverage.
- [Validation](docs/validation.md): exact checks and reproducibility.
- [Review](docs/review.md): proven fixes and source interpretation.
- [Publication](docs/publication.md): publication verification receipt.

## Sources

The snapshot contains 65 attributed response bodies: SEC filings/XBRL, Coinbase candles from July 2015 through October 20, 2026, and IRS/regulatory material. The July 2026 S&P methodology was checked in the browser; direct PDF download returned 403, so that PDF is not in the snapshot. Its earnings wording was rechecked on 2026-10-22 against the Internet Archive copy linked in Results. Strategy's 4:00 p.m. ET pricing and the $2.42 billion tax reversal are quoted from the June 2026 10-Q in the snapshot. See [source notes](docs/sources.md) and `provenance/`.

## Scope and limits

- Independent research; no affiliation with Strategy or S&P. No investment or tax-return functionality.
- Only the earnings condition is modelled. Market cap, liquidity, float, sector balance and the Index Committee's discretion are not.
- Scenario pass frequencies are conditional on fixed holdings and cost, no future sales, assumed other income, the tax proxy and the return regime. They are not index-selection probabilities.
- The tax proxy tracks only the bitcoin deferred tax item. It misses valuation-allowance effects on other deferred tax assets (about $491m in Q1 2026, see Model error).
- Six quarters cannot show stable future accuracy. Scored holdings, costs and the tax calibration come from filings, not as-filed forecasts.
- AFSI is not GAAP earnings. Simplified `camt` keys assume zero regular tax and credits and give tentative-tax sensitivity, not actual liability.
- Optional source refresh is a new sample. It does not update curated facts or IRS guidance and will fail the frozen-source checks.
- The October 28 daily-dividend proposal was pending at the snapshot; the model does not assume it passes.

## License

[MIT](LICENSE). The license covers this project's code only. Third-party source documents/data retain their owners' rights.

Part of [Rahil Bhavan's projects](https://github.com/RahilBhavan).
