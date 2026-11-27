"""Offline tests for UCI commit source-first fixture preflight."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('uci_commit_ci', ROOT / 'scripts/issue53-uci-commit-ci.py')
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)

class FixturePreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.fixtures = self.root / 'fixtures'
        shutil.copytree(ROOT / 'ql/test/issue53-uci-commit', self.fixtures)
        self.stage = self.root / 'stage'
        self.stage.mkdir()
        self.patch = patch.object(ci, 'FIX', self.fixtures)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def manifest(self, change):
        path = self.fixtures / 'source-first.json'
        value = json.loads(path.read_text())
        change(value)
        path.write_text(json.dumps(value))

    def test_frozen_sources_and_anchors(self):
        entries = ci.stage_inputs(self.stage)
        self.assertEqual(len(entries), 31)
        self.assertEqual((self.stage / 'usr/share/rpcd/ucode/luci.adblock-fast').stat().st_size, 23660)

    def test_unexpected_model_cohort_fails(self):
        self.manifest(lambda m: m['entries'][0].update(expected='typo'))
        with self.assertRaisesRegex(ValueError, 'classification'):
            ci.stage_inputs(self.stage)

    def test_path_escape_fails_before_staging(self):
        self.manifest(lambda m: m['entries'][0].update(path='../escape.uc'))
        with self.assertRaisesRegex(ValueError, 'fixture path'):
            ci.stage_inputs(self.stage)
        self.assertEqual(list(self.stage.iterdir()), [])

    def test_inconsistent_anchor_coordinate_fails(self):
        def change(m):
            a = m['entries'][0]['anchors']['import']
            a['offset'] += 1
        self.manifest(change)
        with self.assertRaisesRegex(ValueError, 'coordinate offset'):
            ci.stage_inputs(self.stage)

    def test_changed_bytes_fail(self):
        path = self.fixtures / 'controls/positive.uc'
        path.write_bytes(path.read_bytes() + b'\n')
        with self.assertRaisesRegex(ValueError, 'source bytes'):
            ci.stage_inputs(self.stage)

if __name__ == '__main__':
    unittest.main()
