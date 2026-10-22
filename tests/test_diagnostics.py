import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from scripts import validate
from datetime import date

from fve import diagnostics, earnings, xbrl


class DiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = diagnostics.report()

    def test_signed_synthetic_bridge(self):
        pred = earnings.Prediction(120, 20, 12)
        actual = dict(btc_gain=100, tax=15, net_income=95,
                      operations_ex_btc=5, net_interest=-2, other_nonoperating=7)
        result = diagnostics.signed_bridge(pred, actual, dict(
            operations_ex_btc=8, net_interest=-1, other_nonoperating=4))
        self.assertEqual(result['ni_error'], 17)
        self.assertEqual(result['contributions'], dict(
            btc_valuation=20, tax=-5, other_allocation_gap=1,
            operations_ex_btc=3, net_interest=1, other_nonoperating=-3,
            unexplained_residual=0))

    def test_missing_attribution_stays_unexplained(self):
        pred = earnings.Prediction(100, 0, 10)
        result = diagnostics.signed_bridge(pred, dict(
            btc_gain=100, tax=0, net_income=105), {})
        self.assertIsNone(result['contributions']['net_interest'])
        self.assertIsNone(result['contributions']['other_allocation_gap'])
        self.assertEqual(result['contributions']['unexplained_residual'], 5)

    def test_real_reconciliation_and_preliminary_exclusion(self):
        rows = self.report['quarters']
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows[-1]['quarter_end'], date(2026, 6, 30))
        for r in rows:
            self.assertAlmostEqual(sum(r['contributions'].values()), r['ni_error'], places=2)
            self.assertLess(abs(r['contributions']['unexplained_residual']), .01)
            a = r['reported']
            self.assertEqual(a['btc_gain'] + sum(a[k] for k in diagnostics.COMPONENTS)
                             - a['tax'], a['net_income'])
        self.assertAlmostEqual(self.report['baseline_metrics']['production']['mae_usd'],
                               326767589.53013366, places=2)

    def test_chronology_and_unsorted_input(self):
        d1, d2, d3 = date(2025, 3, 31), date(2025, 6, 30), date(2025, 9, 30)
        self.assertEqual(diagnostics.prior_median({d3: 999, d2: 20, d1: 10}, d3), 15)
        self.assertIsNone(diagnostics.prior_median({d1: 999}, d1))
        for r in self.report['quarters']:
            for dates in [*r['history_quarters'].values(), r['other_history_quarters'],
                          r['ni_history_quarters']]:
                self.assertTrue(all(d < r['quarter_end'] for d in dates))
                self.assertLessEqual(len(dates), 4)

    def test_source_lineage_and_q4_derivation(self):
        for r in self.report['quarters']:
            for name in ('operating', 'interest', 'pretax', 'tax', 'net_income'):
                fact = r['source_facts'][name]
                self.assertEqual(fact['tag'], diagnostics.TAGS[name])
                self.assertTrue(fact['accession'])
                self.assertTrue(all(u.startswith('https://www.sec.gov/') for u in fact['filing_urls']))
        q4 = self.report['quarters'][3]
        self.assertEqual(q4['source_facts']['operating']['derivation'], 'FY-9M')
        self.assertEqual(len(q4['source_facts']['operating']['filing_urls']), 2)
        # Independently checked against June 2026 filing's net-interest table (USD thousands).
        self.assertEqual(self.report['quarters'][-1]['reported']['net_interest'], -1_250_000)

    def test_missing_interest_not_fabricated(self):
        cf = xbrl.load()
        cf['facts']['us-gaap'][diagnostics.TAGS['interest']]['units']['USD'] = []
        components, _ = diagnostics.component_history(cf, {q.end: q for q in earnings.history()})
        self.assertEqual(components['net_interest'], {})
        self.assertEqual(components['other_nonoperating'], {})
        self.assertTrue(components['operations_ex_btc'])

    def test_validator_requires_exact_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'results').mkdir()
            for name in validate.OUTPUTS:
                (root / 'results' / name).write_text('fixture')
            (root / 'results' / 'unrelated.txt').write_text('ignored')
            with patch.object(validate, 'ROOT', root):
                self.assertEqual(len(validate.hashes()), 7)
                (root / 'results' / 'earnings_diagnostics.json').unlink()
                with self.assertRaises(FileNotFoundError):
                    validate.hashes()

    def test_baselines_same_sample_and_arithmetic(self):
        for metric in self.report['baseline_metrics'].values():
            self.assertEqual(metric['n'], 6)
        for r in self.report['quarters']:
            p = r['production_prediction']
            self.assertEqual(r['baseline_predictions']['bridge_zero_other'], p['gain'] - p['tax'])
        # The diagnostic is repeatable and never modifies production calibration.
        self.assertEqual(self.report, diagnostics.report())


if __name__ == '__main__':
    unittest.main()
