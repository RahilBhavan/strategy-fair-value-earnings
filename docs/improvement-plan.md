# Historical earnings diagnostic slice

Scope: preserve the frozen October 21, 2026 sample and production model. Explain
six reported quarters' approximately $326.77m Coinbase net-income MAE with a
signed component bridge, source lineage and simple historical comparators.
No glossary or ADR directory exists in this repository; `docs/spec.md` and
`docs/methodology.md` define the existing domain and scope.

Done conditions:

1. Offline CLI writes deterministic per-quarter JSON: BTC, operations excluding
   BTC, net interest (bounded financing proxy), other nonoperating income, tax,
   allocation gap and unexplained residual. Signed contributions reconstruct
   model-minus-reported NI within $0.01; unavailable attribution stays explicit.
2. Every reported component identifies its XBRL tag, accession and direct/FY-9M
   derivation; frozen source hashes and dates remain unchanged.
3. Compare zero and prior-quarter NI plus zero/prior/median other-income
   alternatives on the same six reported quarters. All history-dependent inputs
   use strictly earlier quarter ends; do not claim point-in-time forecasting
   from latest-comparative XBRL or end-period holdings/costs.
4. Q3 preliminary inputs are excluded from scores. No full-sample fitting,
   production parameter change, CAMT/AFSI change or selection-probability claim.
5. Baseline and new arithmetic, missing-input, chronology, real-source and
   deterministic-replay checks pass. Document a five-minute example, measured
   results and residual limits; commit and push scoped changes and inspect CI.
