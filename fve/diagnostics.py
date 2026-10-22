"""Ex-post signed error accounting; comparator histories are quarter-chronological.

These are historical reconstructions, not filing-date-safe forecasts. No model
parameters are fitted here. Net interest is only a bounded financing proxy.
"""
from statistics import median

from . import earnings, xbrl
from .filings import load_curated

TAGS = {
    'operating': 'OperatingIncomeLoss',
    'interest': 'InterestIncomeExpenseNonoperatingNet',
    'pretax': earnings.PRETAX,
    'tax': 'IncomeTaxExpenseBenefit',
    'net_income': 'NetIncomeLoss',
    'impairment': 'ImpairmentOfIntangibleAssetsExcludingGoodwill',
}
COMPONENTS = ('operations_ex_btc', 'net_interest', 'other_nonoperating')


def prior_values(series, before, count=4):
    return [(e, series[e]) for e in sorted(series) if e < before][-count:]


def prior_median(series, before):
    prior = prior_values(series, before)
    return median(v for _, v in prior) if prior else None


def signed_bridge(pred, reported, forecasts):
    """Positive contribution increases model-minus-reported NI error.

    Missing component attribution is left in unexplained_residual, never zero
    filled. Allocation gap reconciles separate diagnostic medians to the
    production model's median of aggregate other income.
    """
    error = pred.net_income - reported['net_income']
    contributions = {
        'btc_valuation': pred.gain - reported['btc_gain'],
        'tax': reported['tax'] - pred.tax,
    }
    complete = all(forecasts.get(k) is not None for k in COMPONENTS)
    contributions['other_allocation_gap'] = (
        pred.other - sum(forecasts[k] for k in COMPONENTS) if complete else None)
    for k in COMPONENTS:
        actual, forecast = reported.get(k), forecasts.get(k)
        contributions[k] = forecast - actual if actual is not None and forecast is not None else None
    contributions['unexplained_residual'] = error - sum(
        v for v in contributions.values() if v is not None)
    return {'ni_error': error, 'contributions': contributions}


def component_history(cf, hist):
    series = {k: xbrl.quarterly(cf, tag) for k, tag in TAGS.items()}
    out = {k: {} for k in COMPONENTS}
    lineage = {}
    for end, (op, _, _) in series['operating'].items():
        if end.year < 2023 or end not in series['pretax']:
            continue
        q = hist.get(end)
        if q and q.btc_gain is not None and end.year >= 2025:
            operations = op - q.btc_gain
        elif end.year < 2025 and end in series['impairment']:
            operations = op + series['impairment'][end][0]
        else:
            continue
        out['operations_ex_btc'][end] = operations
        if end in series['interest']:
            interest = series['interest'][end][0]
            out['net_interest'][end] = interest
            out['other_nonoperating'][end] = series['pretax'][end][0] - op - interest
        lineage[end] = {
            k: {'tag': TAGS[k], 'value_usd': values[end][0],
                'derivation': values[end][1], 'accession': values[end][2],
                'filing_urls': [xbrl.source_url(a) for a in values[end][2].split(' - ')]}
            for k, values in series.items() if end in values
        }
    return out, lineage


def report():
    cf, hist = xbrl.load(), {q.end: q for q in earnings.history()}
    components, lineage = component_history(cf, hist)
    oh = earnings.other_income_history()
    ni = {e: v[0] for e, v in xbrl.quarterly(cf, 'NetIncomeLoss').items()}
    rows = []
    for row in earnings.backtest('coinbase')[1]:
        if row['estimate']:
            continue
        end, pred, q = row['quarter_end'], row['pred'], hist[row['quarter_end']]
        actual = {k: v.get(end) for k, v in components.items()}
        actual.update(btc_gain=q.btc_gain, tax=q.tax, net_income=q.net_income)
        forecasts = {k: prior_median(v, end) for k, v in components.items()}
        prior_other = prior_values(oh, end)
        prior_ni = prior_values(ni, end, 1)
        # Fixed comparators selected before scoring, no full-sample fitting.
        estimates = {
            'production': pred.net_income,
            'zero_net_income': 0.0,
            'previous_net_income': prior_ni[-1][1] if prior_ni else None,
            'bridge_zero_other': pred.gain - pred.tax,
            'bridge_previous_other': pred.gain - pred.tax + prior_other[-1][1] if prior_other else None,
            'bridge_split_medians': pred.gain - pred.tax + sum(forecasts.values())
            if all(v is not None for v in forecasts.values()) else None,
        }
        rows.append({
            'quarter_end': end, 'status': 'reported', 'reported': actual,
            'production_prediction': {'gain': pred.gain, 'tax': pred.tax, 'other': pred.other,
                                      'net_income': pred.net_income},
            'diagnostic_component_forecasts': forecasts,
            'history_quarters': {k: [e for e, _ in prior_values(v, end)] for k, v in components.items()},
            'other_history_quarters': [e for e, _ in prior_other],
            'ni_history_quarters': [e for e, _ in prior_ni],
            **signed_bridge(pred, actual, forecasts),
            'source_facts': lineage.get(end, {}),
            'baseline_predictions': estimates,
        })
    metrics = {}
    for name in rows[0]['baseline_predictions']:
        errors = [r['baseline_predictions'][name] - r['reported']['net_income']
                  for r in rows if r['baseline_predictions'][name] is not None]
        metrics[name] = {'n': len(errors), 'mae_usd': sum(map(abs, errors)) / len(errors),
                         'mean_signed_error_usd': sum(errors) / len(errors),
                         'max_abs_error_usd': max(map(abs, errors))}
    contribution_metrics = {}
    for key in rows[0]['contributions']:
        values = [r['contributions'][key] for r in rows if r['contributions'][key] is not None]
        contribution_metrics[key] = {'n': len(values), 'mean_signed_usd': sum(values) / len(values),
                                     'mean_absolute_usd': sum(map(abs, values)) / len(values)}
    return {
        'units': 'USD', 'error_sign': 'prediction minus reported',
        'scope': 'Ex-post reconstruction; earlier quarter ends, not as-filed information sets',
        'financial_cutoff': '2026-10-21', 'excluded_preliminary_quarters': ['2026-09-30'],
        'limits': [
            'End-quarter holdings and costs are observed inputs, not forecasts.',
            'Latest-comparative XBRL may postdate the scored quarter; filing lags are not modeled.',
            'Net interest is a financing proxy; other nonoperating is not assigned a causal label.',
            'Separate diagnostic medians do not replace the production aggregate other forecast.',
            'Absolute component errors do not add to net-income MAE because signs offset.',
            'Tax is a GAAP expense proxy comparison, not AFSI or actual CAMT liability.',
        ],
        'companyfacts_source': xbrl.companyfacts_provenance(),
        'curated_btc_sources': {k: v for k, v in load_curated().items()
                                if k.startswith(('btc_gain_', 'sale_'))},
        'component_input_lineage': [{'quarter_end': e, 'facts': facts}
                                    for e, facts in sorted(lineage.items())],
        'quarters': rows, 'baseline_metrics': metrics, 'component_metrics': contribution_metrics,
    }
