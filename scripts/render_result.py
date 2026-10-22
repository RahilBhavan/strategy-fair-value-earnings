"""Generate a result table from the actual reported-quarter backtest, without plotting dependencies."""
import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    backtest = json.loads((ROOT / 'results/backtest.json').read_text())['coinbase']
    rows = [r for r in backtest['quarters'] if not r['estimate_only']]
    mae = backtest['mean_abs_ni_error'] / 1e6
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="960" height="650" viewBox="0 0 960 650" role="img" aria-labelledby="title desc">',
        f'<title id="title">Net-income error averages ${mae:,.2f} million</title>',
        '<desc id="desc">Six reported quarters, Q1 2025 to Q2 2026. Coinbase-price model versus reported GAAP net income. Q3 preliminary estimates are excluded.</desc>',
        '<rect width="960" height="650" fill="#F5F5EF"/>',
        '<g font-family="IBM Plex Sans, Liberation Sans, sans-serif" fill="#111214">',
    ]

    def text(x, y, value, size=26, anchor='start', color='#111214', weight='400'):
        parts.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" fill="{color}" font-weight="{weight}">{escape(str(value))}</text>')

    text(40, 48, 'BUILD NOTES / RAHIL BHAVAN', 20, color='#52545A')
    text(40, 104, f'Net-income error averages ${mae:,.2f}m', 40, weight='600')
    text(40, 146, 'Coinbase-price model vs reported GAAP earnings', 26)
    text(40, 184, 'Six quarters · USD millions · model minus reported', 23, color='#52545A')
    headers = [(40, 'Quarter', 'start'), (440, 'Reported', 'end'), (660, 'Model', 'end'), (916, 'Error', 'end')]
    for x, label, anchor in headers:
        text(x, 240, label, 24, anchor, '#52545A')
    parts.append('<path d="M40 258 H920" stroke="#C6C7BF"/>')
    for i, r in enumerate(rows):
        y = 300 + i * 42
        text(40, y, r['quarter_end'])
        for x, key in ((440, 'reported_ni'), (660, 'pred_ni'), (916, 'ni_error')):
            text(x, y, f'{r[key] / 1e6:+,.2f}', anchor='end')
    parts.append('<path d="M40 532 H920" stroke="#C6C7BF"/>')
    text(40, 570, 'Reconciled asset gains do not establish net-income accuracy.', 25, weight='600')
    text(40, 605, 'Source: results/backtest.json · frozen 2026-10-21', 22, color='#52545A')
    text(40, 633, 'Preliminary Q3 2026 is excluded. Research; no selection-probability claim.', 20, color='#52545A')
    parts.append('</g></svg>')
    out = ROOT / 'docs/assets/backtest.svg'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('\n'.join(parts) + '\n')
    print(out.relative_to(ROOT))


if __name__ == '__main__':
    main()
