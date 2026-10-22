# Strategy fair-value earnings: bridge BTC accounting to an earnings eligibility screen

A local Python model that rebuilds Strategy's BTC fair-value earnings bridge and tests the latest-quarter/trailing-four-quarter earnings condition used by S&P. Seeded scenarios estimate conditional frequencies of passing that screen. They do not estimate index selection probability. Financial cutoff: October 21, 2026; market candles end October 20.

## Results

- Latest reported quarter, June 30, 2026: net loss **$8,219,628,000**; trailing-four net loss **$30,413,926,000**. Both fail the earnings screen (`results/summary.json`).
- Filing-price asset-gain bridges reconcile six reported fair-value quarters after including sourced Q2 sale proceeds/cost removed. The broader Coinbase-price net-income model has **$326.77 million mean absolute error**; this remains material (`results/backtest.json`).
- The September 2026 quarter uses preliminary company asset-gain/tax estimates plus modeled other income. It is not reported GAAP earnings.
- Three bootstrap regimes, preferred-burden sensitivities, price thresholds and simplified CAMT scenarios rebuild locally. CAMT outputs distinguish the current FVI-option scenario from counterfactual no-exclusion cases.

## How it works

`fve/xbrl.py` and `filings.py` load SEC facts; `earnings.py` bridges holdings, fair value, purchases/sales and a simplified tax proxy. `sp_rule.py` applies the positivity screen. `simulate.py` uses historical BTC return blocks. `camt.py` models simplified AFSI/applicability and tentative-tax sensitivities separately from GAAP deferred tax.

## Run it

Python 3.12+ and NumPy 2.3.4; tested with Python 3.14.7. From this repository:

```bash
python3 -m venv ~/scratch/strategy-fair-value-earnings/venv
~/scratch/strategy-fair-value-earnings/venv/bin/pip install -r requirements.txt
~/scratch/strategy-fair-value-earnings/venv/bin/python scripts/snapshot.py
~/scratch/strategy-fair-value-earnings/venv/bin/python scripts/verify_sources.py
~/scratch/strategy-fair-value-earnings/venv/bin/python -m unittest discover -s tests -v
~/scratch/strategy-fair-value-earnings/venv/bin/python scripts/run_model.py
```

Observed: **20 tests passed**. Package installation needs network access; source restoration/tests/demo are offline and need no credentials. Generated CSV/JSON stay local. A second run reproduces their hashes with the pinned NumPy version and seed. Optional source fetching needs contact-bearing `SEC_USER_AGENT` for EDGAR.

## Repository layout

- `fve/`: source loading, accounting, screen, bootstrap and CAMT models.
- `scripts/`: restore, verify, optional fetch and deterministic demo.
- `snapshot/`: compressed source/curated-fact archive.
- `provenance/`: source URL/date/hash inventories.
- `tests/`: source, accounting, missing-input and stochastic checks.
- `docs/`: scope, methodology, CAMT research and validation.

## Documentation

- [Scope and acceptance](docs/spec.md): local v1 contract.
- [Methodology](docs/methodology.md): bridges, backtests and conditional scenarios.
- [CAMT research](docs/camt.md): AFSI exclusions, thresholds and omitted tax details.
- [Sources](docs/sources.md): primary-source checks and cache coverage.
- [Validation](docs/validation.md): exact checks and reproducibility.

## Sources

The snapshot contains 65 attributed response bodies: SEC filings/XBRL, Coinbase candles from July 2015 through October 20, 2026, and IRS/regulatory material. The July 2026 S&P methodology was checked in the browser; direct PDF download returned 403, so that PDF is not archived. See [source notes](docs/sources.md) and `provenance/`.

## Scope and limits

- Independent research; no affiliation with Strategy or S&P. No investment or tax-return functionality.
- Only an earnings condition is modeled; other eligibility criteria and committee selection are excluded.
- Scenario frequencies depend on fixed holdings/cost, no future sales, assumed other income, tax proxy and return regime. No calibrated future-probability claim.
- AFSI is not GAAP earnings. Current guidance permits qualifying FVI exclusions subject to requirements. Simplified `camt` keys assume zero regular tax/credits and mean tentative-tax sensitivity, not actual liability or tax on every unrealized gain.
- Existing figures are excluded from this CLI deliverable.

## License

No license file yet. Third-party source documents/data retain their owners' rights.

Part of [Rahil Bhavan's projects](https://github.com/RahilBhavan).
