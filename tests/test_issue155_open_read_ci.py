"""Offline checks for the source-first literal-r fixture gate."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('open_read_ci', ROOT/'scripts/issue155-open-read-ci.py')
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)


class FixtureGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        shutil.copytree(ci.FIXTURES, self.root/'fixtures')
        self.old = ci.FIXTURES
        ci.FIXTURES = self.root/'fixtures'
        self.addCleanup(setattr, ci, 'FIXTURES', self.old)

    def stage(self):
        destination = self.root/'stage'
        destination.mkdir()
        return ci.stage_inputs(destination)

    def test_source_first_stage(self):
        _, entries = self.stage()
        self.assertEqual(len(entries), 27)

    def test_manifest_cannot_drop_or_relabel_control(self):
        path = ci.FIXTURES/'manifest.json'
        data = json.loads(path.read_text())
        data['controls'][0]['expected_count'] = 0
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'cohort'):
            self.stage()

    def test_changed_source_bytes_are_rejected(self):
        path = ci.FIXTURES/'controls/positive-two.uc'
        path.write_bytes(path.read_bytes()+b'\n')
        with self.assertRaisesRegex(ValueError, 'fixture bytes'):
            self.stage()

    def test_wrong_mode_anchor_is_rejected(self):
        path = ci.FIXTURES/'manifest.json'
        data = json.loads(path.read_text())
        entry = next(e for e in data['controls'] if e['path'] == 'controls/positive-two.uc')
        entry['selected']['mode_argument'][1] -= 1
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'source anchor mode_argument'):
            self.stage()


if __name__ == '__main__':
    unittest.main()
