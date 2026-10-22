# Correctness and source review

Purpose: record the prove-then-fix review of the existing v1 before public publication. Financial snapshot: October 21, 2026; last simulated-return candle: October 20 UTC. This is research software, with no tax-return or trading functionality.

## Fixed and proven

Baseline: commit `98cec08`, clean working tree, 20 passing unittest tests. Scope: this repository only. One independent, read-only T3 review checked earnings, CAMT and source persistence. The parent reproduced findings before changing code.

- `fve/simulate.py`, `pass_probabilities`: `n_paths=2, n_checkpoints=1` raised `ValueError` on an empty future-price horizon. The first checkpoint uses the preliminary Q3 estimate already in state. It now produces a deterministic conditional screen without simulating prices. Regression failed before and passes after.
- `fve/simulate.py`, `pass_probabilities`: `n_paths=2, n_checkpoints=10` labeled December 2028 as latest but evaluated a window ending September 2028 because of an eight-quarter cap. The simulated horizon now reaches the actual requested latest quarter. Regression checks every window ends at its labeled quarter.
- `scripts/fetch_sources.py` and `fve/btc.py`: `main(refresh=True)` only refreshed companyfacts/submissions, leaving cached filings, exhibits and candles in place. Refresh now propagates to each fetched source. Offline mocks reproduce the previous mismatch and verify each request receives the flag. Refresh does not revise curated interpretations or automatically fetch IRS updates.
- `fve/simulate.py`, `pass_probabilities`: zero paths at the deterministic checkpoint produced NaN frequencies. Positive paths/checkpoints are now required; the regression failed before the guard and passes after.

## Source interpretation and evidence

The [June 2026 filing](https://www.sec.gov/Archives/edgar/data/1050446/000105044626000044/mstr-20260630.htm), digital-asset rollforward, identifies $168.126 million original cost removed and $83.205 million sale carrying value/proceeds. Thus the gain bridge adds proceeds minus original cost removed, a negative $84.921 million. This matches the six filed fair-value quarters within rounding. A synthetic unchanged-price sale verifies that it does not create an artificial GAAP gain. The simplified GAAP deferred-tax proxy releases a liability on disposition; it does not model current tax on the sale.

All 24 curated fact magnitudes were checked against the quoted text and their context, including units, gain/loss signs and the Q2 sale columns. Tests now check both quote presence and magnitude, plus a frozen SHA-256 for the curated CSV. Numeric presence alone does not establish the correct table column or sign. The archive itself also has an overall hash; 65 response bodies have separate inventory hashes.

The [July 2026 S&P methodology](https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-us-indices.pdf), Financial Viability, requires positive continuing-operations GAAP net income in the most recent quarter and the sum of four consecutive quarters. June 2026 reported earnings are separate from Q3 preliminary company estimates plus modeled other income. Tests check the latest reported loss, trailing-four loss, zero boundary, missing quarters and the preliminary separation. The methodology PDF was readable through the browser during this review; the earlier direct-download 403 remains documented, and the PDF is not archived. Passing this earnings condition is not selection.

[IRS Notice 2025-49](https://www.irs.gov/pub/irs-drop/n-25-49.pdf), sections 5.03–5.05, supports the conditional FVI exclusion and later adjustment/basis requirements. [Notice 2026-7](https://www.irs.gov/irb/2026-11_IRB) modifies other adjustments and does not revoke that option. The [IRS Form 4626 instructions](https://www.irs.gov/instructions/i4626), FSNOL section, confirm carryforwards are reduced by positive-year use even before a corporation is applicable. A regression now checks that case. The instructions supplement this browser review and are not part of the frozen archive. These checks do not certify company elections, actual AFSI, CAMT basis or tax liability. See [CAMT boundaries](camt.md).

Coinbase batches contain 4,111 daily closes, July 21, 2015 through October 21, 2026, without date gaps. An API boundary overlap includes October 21; `simulate.log_returns` explicitly excludes it. The simulated-return endpoint remains October 20. The net-income MAE remains $326.77 million across six reported quarters. No calibration improvement is claimed.

## Sweep and checks

Correctness, error handling, security, performance, dead-code and repository-convention passes covered `fve/`, `scripts/`, tests and documentation. Accessibility was limited to CLI readability and the generated figure; no app UI exists. No additional demonstrated security issue or measured performance regression survived review. The existing unused `future_quarter_ends` helper is retained because removing a library surface is outside this correctness fix.

After: 31 tests pass. New persistence cases exercise repeated real archive restoration, corruption rejection before extraction, and a failed network refresh followed by a cache retry. Compile checks pass. The six default result-file hashes match the baseline and repeat identically in the pinned local environment. See [validation](validation.md) for clean-clone evidence. This is a bounded review, not security certification.

## Remaining limits

No human-blocked code defect remains from this review. The material net-income model error, assumed valuation allowance, omitted current taxes, frozen holdings/cost, simplified CAMT basis and AFSI, filing-lag assumptions and conditional bootstrap frequencies remain explicit model limits. Q3 remains preliminary. The October 28 daily-dividend proposal was pending at the snapshot and is not treated as enacted.

Next: use fresh source review and a separately versioned sample before interpreting any later financial period.
