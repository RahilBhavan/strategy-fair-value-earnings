"""Run source checks, tests and two identical offline demos; record output hashes."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMOS = [['scripts/run_model.py'], ['scripts/diagnose_earnings.py']]


def run(args):
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)


OUTPUTS = ('backtest.json', 'camt.json', 'earnings_diagnostics.json',
           'pass_probabilities.json', 'quarterly_history.csv', 'summary.json', 'thresholds.json')


def hashes():
    # Required artifacts only: missing files must fail; unrelated local files are not evidence.
    return {f'results/{name}': hashlib.sha256((ROOT / 'results' / name).read_bytes()).hexdigest()
            for name in OUTPUTS}


def main():
    run(["scripts/verify_sources.py"])
    run(["-m", "unittest", "discover", "-s", "tests", "-v"])
    for demo in DEMOS:
        run(demo)
    first = hashes()
    for demo in DEMOS:
        run(demo)
    if first != hashes():
        raise RuntimeError("demo output hashes changed between identical runs")
    evidence = {"financial_as_of": "2026-10-21", "python": sys.version.split()[0],
                "demo_commands": [["python", *d] for d in DEMOS],
                "reproducible_output_files": first}
    (ROOT / "docs/validation.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"Reproduced {len(first)} output file hashes")


if __name__ == "__main__":
    main()
