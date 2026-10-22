import math
import re
import unittest
from datetime import date

import numpy as np

from fve import btc, camt, earnings, simulate, sp_rule, xbrl
from fve.filings import load_curated, text


class ModelTests(unittest.TestCase):
    def test_curated_source_quotes(self):
        facts = load_curated()
        self.assertGreater(len(facts), 20)
        for key, row in facts.items():
            with self.subTest(key=key):
                quote = re.sub(r'\s+', ' ', row['quote'])
                self.assertIn(quote, text(row['source']))
                self.assertTrue(row['url'].startswith('https://www.sec.gov/'))

    def test_reported_screen(self):
        ni = {e: v[0] for e, v in xbrl.quarterly(xbrl.load(), 'NetIncomeLoss').items()
              if e <= date(2026, 6, 30)}
        vd = sp_rule.trailing_series(ni)[date(2026, 6, 30)]
        self.assertFalse(vd.passes)
        self.assertEqual(vd.latest_quarter, -8219628000)
        self.assertEqual(vd.trailing_four, -30413926000)

    def test_zero_is_not_positive(self):
        self.assertFalse(sp_rule.financial_viability([1, 1, 1, 0]).passes)
        self.assertFalse(sp_rule.financial_viability([-3, 1, 1, 1]).passes)
        self.assertTrue(sp_rule.financial_viability([-1, 1, 1, 1]).passes)

    def test_missing_and_nonfinite_quarters(self):
        for values in ([1, 2, 3], [1, 2, 3, None], [1, 2, 3, math.nan], [1, 2, 3, math.inf]):
            with self.assertRaises(ValueError):
                sp_rule.financial_viability(values)

    def test_gapped_series(self):
        ni = {date(2025, 3, 31): 1, date(2025, 6, 30): 1,
              date(2025, 12, 31): 1, date(2026, 3, 31): 1}
        self.assertEqual(sp_rule.trailing_series(ni), {})

    def test_purchase_at_market_no_instant_profit(self):
        p = earnings.predict(10, 100, 1000, 12, 100, 1200, 0, .3)
        self.assertEqual(p.gain, 0)
        self.assertEqual(p.net_income, 0)

    def test_bridge_additivity(self):
        a = earnings.predict(10, 100, 1000, 12, 120, 1200, 0, .3)
        b = earnings.predict(12, 120, 1200, 15, 90, 1500, 0, .3)
        both = earnings.predict(10, 100, 1000, 15, 90, 1500, 0, .3)
        self.assertAlmostEqual(a.gain + b.gain, both.gain)
        self.assertAlmostEqual(a.tax + b.tax, both.tax)

    def test_below_cost_no_assumed_benefit(self):
        p = earnings.predict(10, 80, 1000, 10, 60, 1000, 0, .3)
        self.assertEqual(p.tax, 0)
        self.assertEqual(p.net_income, -200)

    def test_filing_price_bridge(self):
        _, rows = earnings.backtest('filing')
        self.assertEqual(sum(not r['estimate'] for r in rows), 6)
        # Holdings/cost bridge agrees within source rounding, distinct from tax/NI accuracy.
        self.assertLess(max(abs(r['pred'].gain - r['reported_gain']) for r in rows if not r['estimate']), 1_000_000)

    def test_btc_data_order_and_cutoff(self):
        closes = btc.daily_closes()
        self.assertIn(date(2026, 10, 20), closes)
        r = simulate.log_returns(closes)
        shuffled = dict(reversed(list(closes.items())))
        np.testing.assert_array_equal(r, simulate.log_returns(shuffled))
        self.assertTrue(np.isfinite(r).all())

    def test_bootstrap_reproducible(self):
        a = simulate.block_bootstrap(np.arange(25) / 1000, 40, 10, np.random.default_rng(1))
        b = simulate.block_bootstrap(np.arange(25) / 1000, 40, 10, np.random.default_rng(1))
        np.testing.assert_array_equal(a, b)
        self.assertEqual(a.shape, (10, 40))

    def test_bootstrap_single_valid_block(self):
        p = simulate.block_bootstrap(np.ones(20), 20, 2, np.random.default_rng(1))
        np.testing.assert_array_equal(p[0], np.arange(1, 21))

    def test_invalid_bootstrap(self):
        for r, n, paths in (([], 20, 2), ([0] * 20, 0, 2), ([math.nan] * 20, 20, 2), ([0] * 20, 20, 0)):
            with self.assertRaises(ValueError):
                simulate.block_bootstrap(r, n, paths, np.random.default_rng(1))

    def test_conditional_probabilities(self):
        out = simulate.pass_probabilities('demeaned', n_paths=200, n_checkpoints=2)
        again = simulate.pass_probabilities('demeaned', n_paths=200, n_checkpoints=2)
        self.assertEqual(out, again)
        self.assertTrue(all(0 <= r['p_pass'] <= 1 for r in out['checkpoints']))
        self.assertTrue(out['checkpoints'][0]['deterministic'])

    def test_camt_fvi_exclusion(self):
        y = camt.Year(2025, 10e9, 12e9, 1e9)
        self.assertEqual(camt.afsi(y, 'interim_fvi'), -1e9)
        self.assertEqual(camt.afsi(y, 'statute_only'), 10e9)

    def test_camt_threshold_and_prior_year(self):
        ys = [camt.Year(y, 1e9) for y in range(2020, 2025)]
        self.assertFalse(any(r['applicable'] for r in camt.run(ys, 'statute_only')))
        ys = [camt.Year(y, 2e9) for y in range(2020, 2025)]
        rows = camt.run(ys, 'statute_only')
        self.assertFalse(rows[2]['applicable'])  # 2022 cannot use a period ending in 2021
        self.assertTrue(rows[3]['applicable'])
        self.assertEqual(rows[3]['camt'], .15 * 2e9)

    def test_camt_fsnol_cap(self):
        ys = [camt.Year(2020, -10e9), camt.Year(2021, 0), camt.Year(2022, 0), camt.Year(2023, 1e9)]
        row = camt.run(ys, 'statute_only')[-1]
        self.assertEqual(row['fsnol_used'], .8e9)
        self.assertGreaterEqual(row['fsnol_after'], 0)

    def test_camt_invalid_inputs(self):
        for ys in ([camt.Year(2025, 1), camt.Year(2025, 2)], [camt.Year(2025, math.nan)]):
            with self.assertRaises(ValueError):
                camt.run(ys, 'interim_fvi')

    def test_preliminary_is_separate(self):
        hist = earnings.history()
        self.assertIsNone(hist[-1].net_income)
        self.assertIsNotNone(hist[-2].net_income)
        self.assertIn('preliminary', hist[-1].sources['note'])
