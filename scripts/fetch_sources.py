"""Fetch and cache every primary source the model reads. Re-running is idempotent (cached files are reused).

Run: python3 scripts/fetch_sources.py [--refresh]
"""
import json
import pathlib
import sys
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from fve import btc  # noqa: E402
from fve.sources import RAW, fetch  # noqa: E402

CIK = "1050446"
COMPANYFACTS = "https://data.sec.gov/api/xbrl/companyfacts/CIK0001050446.json"
SUBMISSIONS = "https://data.sec.gov/submissions/CIK0001050446.json"
# 10-Q/10-K under fair value (ASU 2023-08 adopted 2025-01-01) plus the 8-Ks that discuss CAMT or
# quarter-end bitcoin gains; chosen by reading the filing index (items 2.02/8.01 near quarter ends).
FILINGS = [
    "0001050446-26-000044",  # 10-Q Q2 2026
    "0001050446-26-000031",  # 10-Q Q1 2026
    "0001050446-26-000020",  # 10-K FY2025
    "0001193125-25-262568",  # 10-Q Q3 2025
    "0000950170-25-102209",  # 10-Q Q2 2025
    "0000950170-25-063536",  # 10-Q Q1 2025
    "0001193125-25-225904",  # 8-K 2025-10-01 (8.01)
    "0001193125-25-230977",  # 8-K 2025-10-06 (2.02 Q3 2025 update)
    "0001050446-26-000012",  # 8-K 2026-02-05 (2.02 Q4 2025 results)
    "0001050446-26-000024",  # 8-K 2026-05-05 (2.02 Q1 2026 results)
    "0001628280-26-051027",  # 8-K 2026-07-30 (2.02 Q2 2026 results)
    "0001193125-26-409863",  # 8-K 2026-10-01 weekly update
    "0001193125-26-413164",  # 8-K 2026-10-05 weekly update / Q3 2026 update
    "0001193125-26-419726",  # 8-K 2026-10-13 weekly update
    "0001193125-26-424688",  # 8-K 2026-10-19 weekly update
]


def filing_docs(sub):
    r = sub["filings"]["recent"]
    idx = {a: i for i, a in enumerate(r["accessionNumber"])}
    for accn in FILINGS:
        i = idx[accn]
        yield accn, r["form"][i], r["filingDate"][i], r["primaryDocument"][i]


def main(refresh=False):
    fetch(COMPANYFACTS, "edgar/companyfacts_CIK0001050446.json", refresh)
    sub = json.loads(fetch(SUBMISSIONS, "edgar/submissions_CIK0001050446.json", refresh))
    for accn, form, filed, doc in filing_docs(sub):
        base = f"https://www.sec.gov/Archives/edgar/data/{CIK}/{accn.replace('-', '')}"
        fetch(f"{base}/{doc}", f"edgar/{accn}/{doc}", refresh)
        idx = json.loads(fetch(f"{base}/index.json", f"edgar/{accn}/index.json", refresh))
        for item in idx["directory"]["item"]:
            n = item["name"]
            if "ex99" in n.lower() and n.endswith(".htm"):
                fetch(f"{base}/{n}", f"edgar/{accn}/{n}", refresh)
        print(filed, form, accn, doc)
    btc.fetch_all(date(2026, 10, 20), refresh=refresh)


if __name__ == "__main__":
    main("--refresh" in sys.argv)
