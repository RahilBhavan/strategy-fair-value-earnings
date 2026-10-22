# Validation evidence

Purpose: document reproducible checks for the October 21, 2026 financial snapshot. Publication review ran locally with Python 3.14.7 and NumPy 2.3.4.

From a clean checkout, install `requirements.txt`, then run:

```bash
python scripts/snapshot.py
python scripts/validate.py
python scripts/render_result.py
python -m compileall -q fve scripts tests
```

Observed: 31 tests passed, all 65 response bodies matched their committed inventory hashes, and all six generated result files reproduced identical hashes on consecutive runs. Exact hashes are in [validation.json](validation.json). The new result-table SVG is generated directly from `results/backtest.json`; its bytes reproduce as well. The six default model hashes remain unchanged from the starting v1. Floating-point byte identity across every Python/NumPy/platform combination is not promised.

A fresh scratch copy under `~/scratch/strategy-fair-value-earnings/` contained only tracked/intended source files, with no raw cache, results or repository environment. A separately created venv installed the pinned dependency. Offline restoration, the complete test/demo sequence, compile checks and figure generation passed there. Result hashes and the SVG matched the working tree. Scratch test/build folders are removed after publication verification.

Persistence and negative cases include corruption rejection before archive extraction, three real restore attempts repairing a modified curated file, a network timeout preserving an existing cached response followed by a cache retry, propagation of refresh to every SEC/candle request, missing and nonfinite earnings, exact-zero positivity boundaries, CAMT duplicate/nonfinite years, invalid bootstrap requests, deterministic checkpoints and longer forecast horizons. These are concrete tested cases, not a general crash-atomicity guarantee for the optional fetcher's multiple file writes.

The GitHub workflow pins action commits, Python versions (3.12.12 and 3.14.0), pip and NumPy, grants only `contents: read`, and runs restoration, compilation, source verification, tests, repeated demos and figure-drift checks. Dependency setup requires network; financial source tests/demos run offline with no credentials or paid services. This plain Python project has no configured static typechecker; compilation is a syntax check, not a typecheck.

The pre-commit hook rejects staged files above 20,000 bytes (5,000 estimated tokens). It remains enabled and was not bypassed. No code license was selected. See [review](review.md) for financial limitations and [publication](publication.md) for remote verification.
