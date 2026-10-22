# Historical net-income error diagnostics

The unchanged production model has $326.768m MAE across Q1 2025–Q2 2026.
This diagnostic accounts for that error; it does not establish prospective
accuracy or causally explain every accounting line. USD throughout; positive
error means prediction minus reported net income. Q3 2026 stays preliminary
and is excluded from every score.

## Five-minute offline example

With the README's pinned environment installed, from the repository:

```bash
.venv/bin/python scripts/snapshot.py
.venv/bin/python scripts/diagnose_earnings.py
.venv/bin/python -m unittest discover -s tests -p test_diagnostics.py -v
```

The CLI prints the comparisons and writes `results/earnings_diagnostics.json`.
That ignored artifact contains every quarter's signed bridge, actuals,
forecasts, input-quarter dates, source tags/accessions/derivations, frozen
companyfacts hash/fetch date, curated BTC references and aggregate scores.
No network or credentials are needed after dependency installation.

## What is attributed

Reported operations excluding BTC = operating income minus reported BTC gain.
For earlier impairment-era comparator history, add impairment back instead.
Net interest is a bounded financing proxy, not total financing cash flow or
preferred dividends. Other nonoperating income = pretax income minus operating
income minus net interest; its underlying economic cause remains unassigned.
Reported tax expense is compared to the existing GAAP tax proxy.

The production model forecasts aggregate other pretax income with a trailing
four-quarter median. Diagnostic operations, interest and other nonoperating
forecasts each use their own prior-four median. Their medians need not add to
the aggregate median: `other_allocation_gap` records that exact difference.
This split is diagnostic bookkeeping, not a replacement model.

Signed NI error equals BTC error + operations error + net-interest error +
other-nonoperating error + allocation gap + (reported tax minus modeled tax)
+ unexplained residual. The residual also captures missing component
attribution; missing inputs are null, never assumed zero. With this frozen
sample all components are available and the arithmetic residual is below one
cent. That accounting closure does not identify economic causes inside the
aggregate tax or other-nonoperating lines.

Mean absolute contributions are $274.674m BTC, $124.657m tax, $4.457m operations,
$7.105m net interest, $23.628m other nonoperating and $2.887m allocation gap.
They **do not sum to NI MAE**: signs offset within each quarter. For example,
Q1 2026's +$824.740m NI error includes +$353.792m BTC and +$491.535m tax;
Q2 2026's -$620.869m includes -$502.964m BTC and -$116.327m other nonoperating.
BTC error reflects the venue/measurement-price reconstruction against reported
gain, not an inferred operational loss. The filing-price bridge already
reconciles gains; this does not establish NI accuracy.

## Fixed comparator results

All six reported quarters are scored identically. MAE in USD millions:
production 326.768; zero NI 8,370.365; prior-quarter NI 7,445.222;
same BTC/tax bridge with zero other 338.260; with prior-quarter other 328.217;
with split component medians 326.371. Production already uses aggregate
prior-four median other. The split alternative's $0.397m MAE reduction on six
quarters is insufficient evidence to change production; no parameters were
fitted or selected using these scores.

All comparator histories use strictly earlier quarter ends, with a maximum
four observations (one for prior-NI). This is chronological validation of
historical reconstructions, **not an as-filed walk-forward forecast**:
companyfacts selects latest comparative disclosures and may include subsequent
revisions; scored holdings/costs and the opening tax calibration come from
filings. A genuine forecasting claim needs timestamped as-filed inputs and a
separate subsequent holdout. No such evidence is claimed here.

## Source evidence and measured limits

On 2026-10-22 the primary [June 2026 10-Q](https://www.sec.gov/Archives/edgar/data/1050446/000105044626000044/mstr-20260630.htm)
was rechecked: its interest note identifies net interest, and its digital-asset
policy locates gains in operating expenses. The net-interest table's Q2 2026
-$1.250m agrees with the cached XBRL. This supports the accounting split, not a
causal claim about financing strategy. Existing [source inventory](sources.md)
retains the original observation/fetch dates and hashes. No upstream data,
schema, snapshot or curated facts changed. Q4 source lineage names both FY
and nine-month accessions; input-component lineage includes prior quarters.

Local verification: 31 baseline tests passed before implementation; 39 tests
pass after adding eight diagnostic/validator cases. Synthetic signed arithmetic,
missing attribution, missing interest, unsorted/strict-prior history,
real-quarter closure, Q4 lineage, same-sample baselines and replay are covered.
The full validator reruns both the original model and diagnostic and compares
all seven output hashes; CI runs it on both pinned Python versions. Original
model hashes and figure bytes stay unchanged.

The six-quarter sample cannot validate stable future accuracy or distinguish
all tax causes. No calibrated probability, index-selection claim, AFSI
estimate or actual CAMT liability follows from these diagnostics. Existing
simplified tentative-CAMT and GAAP/AFSI boundaries remain in [camt.md](camt.md).
