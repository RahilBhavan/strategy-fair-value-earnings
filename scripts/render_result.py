"""Generate the backtest figure and the README threshold block from results/, without plotting dependencies."""
import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START, END = '<!-- generated:thresholds start -->', '<!-- generated:thresholds end -->'


def usd(v, digits=0):
    return f"{'-' if v < 0 else ''}${abs(v):,.{digits}f}"


def threshold_block():
    """README lines built only from results/thresholds.json and results/summary.json."""
    thr = json.loads((ROOT / 'results/thresholds.json').read_text())
    summary = json.loads((ROOT / 'results/summary.json').read_text())
    pre, post, err = thr['net_income'], thr['net_income_after_preferred'], thr['model_error']
    per_usd = pre['ni_change_per_usd_of_btc_price']
    lines = [
        f"- **Next pass price:** a {pre['price_basis']} above **{usd(pre['pass_above'])}** makes "
        f"Q4 2026 ({pre['quarter']}) and the four quarters ending then positive on GAAP net income, "
        f"so the modelled screen passes at the {pre['checkpoint']} checkpoint. After preferred dividends "
        f"the price is **{usd(post['pass_above'])}**. Q4 alone turns positive above {usd(pre['latest_quarter_positive_above'])}; "
        f"the trailing-four sum binds because Q1–Q3 2026 sum to {usd(pre['prior_three_quarters_sum'] / 1e6)}m "
        f"(Q3 is a preliminary-estimate model) (`results/thresholds.json`).",
        f"- **Model error:** the price model missed reported net income by {usd(err['mean_abs_ni_error_usd'] / 1e6, 2)}m on average "
        f"(max {usd(err['max_abs_ni_error_usd'] / 1e6, 2)}m) over {err['quarters_scored']} quarters. Near the threshold, "
        f"net income moves about {usd(per_usd / 1e3)}k per $1 of BTC price, so the mean error equals about "
        f"{usd(pre['model_mae_btc_price_equivalent'])} and the max about "
        f"{usd(err['max_abs_ni_error_usd'] / per_usd)} of BTC price. Treat closes within that band as undecided.",
    ]
    probs = summary['pass_probability_base']
    first = next(iter(probs))
    lines.append(
        f"- **`pass_probability_base`** keys are assumed quarterly rebalance dates (third Friday of March, June, "
        f"September and December), not announced dates. {first} is {probs[first]} because no simulated price "
        f"enters its window: Q3 2026 is modelled positive, but the four quarters ending September 30, 2026 sum to "
        f"{usd(summary['trailing_four_at_q3_2026'] / 1e9, 2)}bn. `pass_probability_base_reason` in "
        f"`results/summary.json` states this for every date.")
    return '\n'.join([START, *lines, END])


def update_readme():
    path = ROOT / 'README.md'
    text = path.read_text()
    head, rest = text.split(START, 1)
    tail = rest.split(END, 1)[1]
    path.write_text(head + threshold_block() + tail)


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
    update_readme()
    print('README.md threshold block')


if __name__ == '__main__':
    main()
