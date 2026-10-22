# Validation evidence

Purpose: document reproducible checks for the October 21, 2026 financial snapshot. Publication review ran locally with Python 3.14.7 and NumPy 2.3.4.

From a clean checkout, install `requirements.txt`, then run:

```bash
python scripts/snapshot.py
python scripts/validate.py
python scripts/render_result.py
python -m compileall -q fve scripts tests
```

Original publication: 31 tests passed, all 65 response bodies matched their committed inventory hashes, and all six generated result files reproduced identical hashes on consecutive runs. Exact hashes are in [validation.json](validation.json). The new result-table SVG is generated directly from `results/backtest.json`; its bytes reproduce as well. The six default model hashes remain unchanged from the starting v1. Floating-point byte identity across every Python/NumPy/platform combination is not promised.

A fresh scratch copy under `~/scratch/strategy-fair-value-earnings/` contained only tracked/intended source files, with no raw cache, results or repository environment. A separately created venv installed the pinned dependency. Offline restoration, the complete test/demo sequence, compile checks and figure generation passed there. Result hashes and the SVG matched the working tree. Scratch test/build folders are removed after publication verification.

Persistence and negative cases include corruption rejection before archive extraction, three real restore attempts repairing a modified curated file, a network timeout preserving an existing cached response followed by a cache retry, propagation of refresh to every SEC/candle request, missing and nonfinite earnings, exact-zero positivity boundaries, CAMT duplicate/nonfinite years, invalid bootstrap requests, deterministic checkpoints and longer forecast horizons. These are concrete tested cases, not a general crash-atomicity guarantee for the optional fetcher's multiple file writes.

The GitHub workflow pins action commits, Python versions (3.12.12 and 3.14.0), pip and NumPy, grants only `contents: read`, and runs restoration, compilation, source verification, tests, repeated demos and figure-drift checks. Dependency setup requires network; financial source tests/demos run offline with no credentials or paid services. This plain Python project has no configured static typechecker; compilation is a syntax check, not a typecheck.

The pre-commit hook rejects staged files above 20,000 bytes (5,000 estimated tokens). It remains enabled and was not bypassed. No code license was selected. See [review](review.md) for financial limitations and [publication](publication.md) for remote verification.

The earnings-diagnostics slice adds eight behavioral/validator tests (39 total) and a seventh deterministic output. See [diagnostic evidence](earnings-diagnostics.md); `scripts/validate.py` now repeats both CLIs and requires exactly the seven outputs, rejecting missing artifacts while ignoring unrelated local files. Existing six output hashes and the SVG are preserved.

## Reader-test fixes (2026-10-22)

Three added tests (42 total) check checkpoint `reason` text for fixed and simulated
rebalance dates, threshold metadata (quarter, checkpoint, earnings basis, net-income
sensitivity per dollar of BTC) and that the README threshold lines equal those
rendered from `results/`. CI now also fails if `render_result.py` changes README.md.
Output hashes in [validation.json](validation.json) changed deliberately:
`pass_probabilities.json` gained `reason`, `summary.json` gained
`pass_probability_base_reason`, and `thresholds.json` gained basis/error fields and
renamed `june_2027_march_price_needed_given_december` to
`march_2027_close_needed_for_june_2027_checkpoint` (no consumer used the old key, so
no alias). All numeric values and the SVG are unchanged.

## Error explanation (2026-10-22)

One added test (43 total) pins the README's account of the $326.77m mean error:
Q1 and Q2 2026 carry over 73% of absolute error, the filing-price backtest error is
$121.28m, and the Q1 2026 tax error equals the modelled bitcoin tax reversal less the
reported December 31, 2025 net deferred tax liability within $5m. No model code,
source, output hash or SVG changed.
