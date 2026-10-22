"""Exercise offline restoration, corruption detection and cache retries on disk."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fve import sources
from scripts import snapshot


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        scratch = Path.home() / 'scratch/strategy-fair-value-earnings'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch, prefix='test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_restore_repairs_modified_bytes_and_replays(self):
        with patch.object(snapshot, 'ROOT', self.root), patch('sys.argv', ['snapshot.py']), \
                contextlib.redirect_stdout(io.StringIO()):
            snapshot.main()
            target = self.root / 'data/curated/text_facts.csv'
            expected = target.read_bytes()
            target.write_bytes(b'corrupt')
            snapshot.main()
            self.assertEqual(target.read_bytes(), expected)
            snapshot.main()
            self.assertEqual(target.read_bytes(), expected)

    def test_bad_archive_fails_before_restoration(self):
        snap = self.root / 'snapshot'
        snap.mkdir()
        (snap / 'index.json').write_text('{"parts": 1, "bytes": 3, "sha256": "bad"}')
        (snap / 'part-0000').write_bytes(b'bad')
        with patch.object(snapshot, 'ROOT', self.root), patch.object(snapshot, 'SNAP', snap), \
                patch('sys.argv', ['snapshot.py']):
            with self.assertRaisesRegex(ValueError, 'integrity'):
                snapshot.main()
        self.assertFalse((self.root / 'data').exists())

    def test_failed_refresh_preserves_cache_then_retry_uses_it(self):
        raw = self.root / 'raw'
        raw.mkdir()
        (raw / 'body').write_bytes(b'prior public response')
        manifest = raw / 'manifest.csv'
        manifest.write_text('prior manifest')
        with patch.object(sources, 'RAW', raw), patch.object(sources, 'MANIFEST', manifest), \
                patch.object(sources.urllib.request, 'urlopen', side_effect=TimeoutError):
            with self.assertRaises(TimeoutError):
                sources.fetch('https://example.org/source', 'body', refresh=True)
            self.assertEqual(sources.fetch('https://example.org/source', 'body'), b'prior public response')
        self.assertEqual(manifest.read_text(), 'prior manifest')
