"""Exercise the shared diagnostic gate with identity-preserving JSON cells."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / 'scripts/m4-smoke-diagnostics.py'
CASES = ('comment-positive conditional-expression duplicate-method escaped-literal extra-arg '
         'guard-no-call member-guard member methods-alias nested nonliteral positive '
         'shadow unknown-helper real').split()
SUCCESS_COLS = [{'name': 'f', 'kind': 'Entity'}, {'kind': 'String'}]
ERROR_COLS = [{'name': 'error', 'kind': 'Entity'}, {'kind': 'String'}, {'kind': 'Integer'}]


class DiagnosticsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.paths = [self.root / 'modules' / case / 'root/usr/share/rpcd/ucode/luci' for case in CASES]
        self.rows = [[{'label': str(p), 'url': {'uri': p.as_uri(), 'startLine': 0,
                       'startColumn': 0, 'endLine': 0, 'endColumn': 0}}, ''] for p in self.paths]

    def gate(self, rows, errors):
        for name, cols, tuples in [('files', SUCCESS_COLS, rows), ('errors', ERROR_COLS, errors)]:
            (self.root / f'{name}.json').write_text(json.dumps({'#select': {'columns': cols, 'tuples': tuples}}))
        return subprocess.run([sys.executable, '-B', str(GATE), str(self.root / 'files.json'),
                               str(self.root / 'errors.json'), *map(str, self.paths)],
                              capture_output=True, text=True)

    def test_exact_receipts_pass(self):
        self.assertEqual(self.gate(self.rows, []).returncode, 0)

    def test_every_omission_duplicate_and_substitution_rejected(self):
        for i in range(len(self.paths)):
            with self.subTest(index=i):
                self.assertNotEqual(self.gate(self.rows[:i] + self.rows[i+1:], []).returncode, 0)
                duplicated = deepcopy(self.rows)
                duplicated[i] = deepcopy(self.rows[(i+1) % len(self.rows)])
                self.assertNotEqual(self.gate(duplicated, []).returncode, 0)
                substituted = deepcopy(self.rows)
                wrong = self.root / 'modules' / 'other' / 'root/usr/share/rpcd/ucode/luci'
                wrong.parent.mkdir(parents=True, exist_ok=True)
                wrong.write_text('return {};\n')
                substituted[i][0]['label'] = str(wrong)
                substituted[i][0]['url']['uri'] = wrong.as_uri()
                self.assertNotEqual(self.gate(substituted, []).returncode, 0)

    def test_error_rejected_even_when_files_exact(self):
        self.assertNotEqual(self.gate(self.rows, [[{'label': 'parse error'}, 'error', 1]]).returncode, 0)


if __name__ == '__main__':
    unittest.main()
