"""Offline five-minute diagnostic: python scripts/diagnose_earnings.py."""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fve.diagnostics import report  # noqa: E402


def main():
    result = report()
    target = Path(__file__).resolve().parents[1] / 'results' / 'earnings_diagnostics.json'
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(result, indent=2, default=lambda v: v.isoformat()
                                if isinstance(v, date) else str(v)) + '\n')
    print('Historical reconstruction; USD millions; prediction minus reported')
    for name, metric in result['baseline_metrics'].items():
        print(f"{name}: n={metric['n']} MAE={metric['mae_usd'] / 1e6:.3f}")
    print('Component mean absolute contributions (do not sum to NI MAE):')
    for name, metric in result['component_metrics'].items():
        print(f"{name}: {metric['mean_absolute_usd'] / 1e6:.3f}")
    print(f'Wrote {target.name}; Q3 preliminary excluded; no production parameters changed.')


if __name__ == '__main__':
    main()
