"""Offline controls for the mkdir fixture inventory guard."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('mkdir_ci', ROOT / 'scripts/issue155-mkdir-ci.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class MkdirFixtureGuardTest(unittest.TestCase):
    def setUp(self):
        self.manifest = runner.common.inputs.load(runner.FIXTURES / 'source-first.json')

    def stage(self, manifest):
        with tempfile.TemporaryDirectory() as directory, patch.object(runner.common.inputs, 'load', return_value=manifest):
            return runner.stage_inputs(Path(directory))

    def test_actual_inventory(self):
        _, entries = self.stage(copy.deepcopy(self.manifest))
        self.assertEqual(len(entries), 20)
        self.assertEqual(sum(e['expected'] == 'model' for e in entries), 4)

    def test_hash_mutation_fails_for_fixture_bytes(self):
        changed = copy.deepcopy(self.manifest)
        changed['entries'][0]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'fixture bytes:'):
            self.stage(changed)

    def test_anchor_mutation_fails_for_anchor_bytes(self):
        changed = copy.deepcopy(self.manifest)
        changed['entries'][0]['anchors']['call']['text'] = 'not the source'
        with self.assertRaisesRegex(ValueError, 'anchor bytes:'):
            self.stage(changed)

    def test_duplicate_path_is_rejected(self):
        changed = copy.deepcopy(self.manifest)
        changed['entries'][1]['path'] = changed['entries'][0]['path']
        with self.assertRaisesRegex(ValueError, 'fixture inventory identities'):
            self.stage(changed)


if __name__ == '__main__':
    unittest.main()
