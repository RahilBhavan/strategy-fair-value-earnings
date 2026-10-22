# Publication receipt

Purpose: record the authorized public publication and its verification evidence.

- Repository: [RahilBhavan/strategy-fair-value-earnings](https://github.com/RahilBhavan/strategy-fair-value-earnings), public, default branch `main`.
- Original local v1: `98cec08`. Preserved as an ancestor; no force push or history rewrite.
- Reviewed source and workflow commit: `990eed7c6c390f928392300e2ec95715d5413121`. Remote `refs/heads/main` matched that commit before this receipt-only documentation update.
- [Successful CI run](https://github.com/RahilBhavan/strategy-fair-value-earnings/actions/runs/39718623446): both Python 3.12.12 and 3.14.0 jobs passed. The initial workflow failed to parse an unquoted colon in a pip command; the command now uses a YAML block scalar, and the corrected workflow passed.
- Fresh HTTPS clone under `~/scratch/strategy-fair-value-earnings/published-clone`: source restore, verification, all 31 tests, the demo twice, figure generation and compilation passed with a separately installed NumPy 2.3.4 environment (Python 3.14.7). The six output hashes and generated SVG matched local evidence. After the workflow-only fix, a fast-forward pull retained these results and source hashes.
- Commands: `python scripts/snapshot.py`, `python scripts/validate.py`, `python scripts/render_result.py`, `python -m compileall -q fve scripts tests`. Exact result hashes: [validation.json](validation.json).
- Publication audit inspected current files, all reachable Git blobs and the reconstructed archived sources. No credential or private-artifact matches were found. The inherited v1 commit contact was verified already present in public RahilBhavan GitHub history. New commits use GitHub noreply metadata. Original public issuer contact material remains in attributed filings; no private account/hub material is included. This bounded scan is not a security certification.
- The largest reachable source/archive-part blob before publication was 18,000 bytes. Every staged file remained at or below 20,000 bytes; the hook was enabled and not bypassed. No broad staging, PR, web deployment, schedule or external message was used.
- About text and five topics describe the actual Python accounting/research model. License: **No license file yet**. Third-party material is attributed in [sources](sources.md), with no implied relicensing.

Financial snapshot: October 21, 2026. Fetch timestamps are retained separately in the provenance inventories; simulated returns end October 20. The $326.77 million net-income MAE remains material. Q3 is preliminary plus model estimates, GAAP tax is separate from AFSI/tentative tax, and scenario frequencies are not index-selection probabilities. No actual liability, tax-return, investment or election-compliance functionality is claimed.

This receipt is a documentation descendant of the verified source commit. The final remote HEAD and its CI run are also checked before handoff; GitHub's [workflow history](https://github.com/RahilBhavan/strategy-fair-value-earnings/actions/workflows/ci.yml) provides the commit-specific record. Scratch verification environments/copies are removed after that check.
