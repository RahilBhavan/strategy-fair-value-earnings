import unittest
from pathlib import Path
from datetime import date
from unittest.mock import patch
from scripts import fetch_sources
from fve import btc
from scripts.verify_sources import verify


class SourceTests(unittest.TestCase):
    def test_all_frozen_source_hashes(self):
        self.assertGreater(verify(), 0)

    def test_refresh_reaches_filings_exhibits_and_candles(self):
        calls = []

        def cached(url, rel, refresh=False, **kwargs):
            calls.append((rel, refresh))
            return (Path('data/raw') / rel).read_bytes()

        with patch.object(fetch_sources, 'fetch', cached), \
                patch.object(fetch_sources.btc, 'fetch_all') as candles, patch('builtins.print'):
            fetch_sources.main(refresh=True)
        self.assertGreater(len(calls), 20)
        self.assertTrue(all(refresh for _, refresh in calls))
        candles.assert_called_once_with(date(2026, 10, 20), refresh=True)

    def test_candle_refresh_reaches_each_chunk(self):
        with patch.object(btc, 'fetch') as fetch:
            btc.fetch_all(btc.FIRST, refresh=True)
        self.assertTrue(fetch.call_args.kwargs['refresh'])
