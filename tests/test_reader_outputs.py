import json
import subprocess
import sys
import unittest
from pathlib import Path

from fve import simulate

ROOT = Path(__file__).resolve().parents[1]


class ReaderOutputTests(unittest.TestCase):
    def test_checkpoint_reasons(self):
        rows = simulate.pass_probabilities('demeaned', n_paths=50, n_checkpoints=2)['checkpoints']
        fixed, simulated = rows
        self.assertTrue(fixed['deterministic'])
        self.assertEqual(fixed['p_pass'], 0)
        self.assertIn('trailing four quarters not positive', fixed['reason'])
        self.assertIn('-$14.18bn', fixed['reason'])
        self.assertIn('assumed quarterly S&P rebalance date', simulated['reason'])
        self.assertIn('50 simulated BTC paths', simulated['reason'])
        after = simulate.pass_probabilities('demeaned', n_paths=2, n_checkpoints=1, after_pref=True)
        self.assertIn('after preferred dividends', after['checkpoints'][0]['reason'])

    def test_threshold_metadata(self):
        pre = simulate.next_quarter_thresholds()
        post = simulate.next_quarter_thresholds(after_pref=True)
        self.assertEqual((str(pre['quarter']), str(pre['checkpoint'])), ('2026-12-31', '2027-03-19'))
        self.assertIn('before preferred', pre['earnings_basis'])
        self.assertGreater(post['pass_above'], pre['pass_above'])
        self.assertGreater(pre['ni_change_per_usd_of_btc_price'], 0)

    def test_readme_block_matches_results(self):
        if not (ROOT / 'results/thresholds.json').exists():
            subprocess.run([sys.executable, 'scripts/run_model.py'], cwd=ROOT, check=True, capture_output=True)
        thr = json.loads((ROOT / 'results/thresholds.json').read_text())
        self.assertNotIn('june_2027_march_price_needed_given_december', thr)
        self.assertIn('by_december_31_2026_close', thr['march_2027_close_needed_for_june_2027_checkpoint'])
        sys.path.insert(0, str(ROOT / 'scripts'))
        import render_result
        block = render_result.threshold_block()
        self.assertIn(f"${thr['net_income']['pass_above']:,.0f}", block)
        self.assertIn(f"${thr['net_income_after_preferred']['pass_above']:,.0f}", block)
        self.assertIn(block, (ROOT / 'README.md').read_text())


if __name__ == '__main__':
    unittest.main()
