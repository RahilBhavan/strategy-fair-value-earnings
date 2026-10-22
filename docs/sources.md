# Source coverage and reproduction

The frozen inventory contains 65 response bodies, including SEC filing/index/XBRL responses, Coinbase daily candle batches, regulatory material and IRS guidance. `provenance/sources-*.csv` records each URL, fetch time, bytes and SHA-256. `snapshot/index.json` hashes their compressed archive (with curated facts and original metadata), split into <=18,000-byte files. Restore and hash-verify before running. Derived results are ignored by Git and rebuild offline.

Primary-source website checks during continuation:

- [June 2026 10-Q](https://www.sec.gov/Archives/edgar/data/1050446/000105044626000044/mstr-20260630.htm): financial statements, BTC movement and sale cost/proceeds, tax disclosure.
- [October 5 8-K](https://www.sec.gov/Archives/edgar/data/1050446/000119312526413164/mstr-20261005.htm): Q3 preliminary digital-asset and deferred-tax estimates, not complete earnings.
- [October 19 8-K](https://www.sec.gov/Archives/edgar/data/1050446/000119312526424688/mstr-20261019.htm): latest frozen BTC holdings/cost input.
- [S&P methodology](https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-us-indices.pdf): July 2026 edition checked in the browser. Direct download returned HTTP 403, so the PDF is not in the archive; the rule is documented by URL and date. The program uses the encoded rule rather than parsing that inaccessible PDF.
- [Coinbase API specification](https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles): daily candle schema. Frozen batches cover July 2015 through October 20, 2026; venue closes are not universal BTC closing prices. Sparse intervals and exchange-specific artifacts can affect bootstrap returns.
- [IRS Notice 2025-49](https://www.irs.gov/pub/irs-drop/n-25-49.pdf), [2026-7](https://www.irs.gov/irb/2026-11_IRB), and [2025-27](https://www.irs.gov/irb/2025-26_IRB) were checked and saved. [2024 proposed regulations](https://www.federalregister.gov/documents/2024/09/13/2024-20089/corporate-alternative-minimum-tax) are cached for the counterfactual only.

Curated facts retain exact filing excerpts; tests confirm each excerpt remains in the cached filing. The two Q2 sale-flow facts were added during continuation. Source-hash tests cover all 65 response bodies. This does not mean all historical filings were independently reread in this continuation. The source fetch helpers are optional and require a contact-bearing `SEC_USER_AGENT` for EDGAR; deterministic reproduction uses the archived cache instead. Updated XBRL can contain restatements and change outputs, so refresh is a new sample rather than reproduction of this cutoff.
