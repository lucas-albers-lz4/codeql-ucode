"""The local-helper verifier compares full entity identities, not counts."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('local_helper_smoke', ROOT / 'scripts/models-local-helper-smoke.py')
assert spec is not None and spec.loader is not None
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


class IdentityTests(unittest.TestCase):
    def test_exact_identity_and_multiplicity(self):
        expected = [[['positive.uc', 4, 3, 4, 35], ['positive.uc', 2, 10, 2, 32]]]
        smoke.assert_rows('binding', expected, expected)
        for wrong in ([], expected + expected,
                      [[['positive.uc', 4, 3, 4, 34], expected[0][1]]],
                      [[expected[0][0], ['negative.uc', 2, 10, 2, 32]]]):
            with self.subTest(wrong=wrong), self.assertRaises(SystemExit):
                smoke.assert_rows('binding', wrong, expected)

    def test_oracle_pins_both_consumers_and_issue_twins(self):
        corpus = smoke.CORPUS
        positive = (corpus / 'issue_positive.uc').read_text()
        shadow = (corpus / 'issue_shadow.uc').read_text()
        self.assertEqual(shadow.replace('call: function(callPackageVersionCheck)', 'call: function()'), positive)
        taint_positive = (corpus / 'taint_positive.uc').read_text()
        taint_shadow = (corpus / 'taint_shadow.uc').read_text()
        self.assertEqual(taint_shadow.replace('call: function(callPackageVersionCheck)', 'call: function()'), taint_positive)
        self.assertIn('popen(request.args.cmd)', taint_positive)
        self.assertIn([['issue_positive.uc', 4, 3, 4, 35], ['issue_positive.uc', 2, 41, 2, 53]], smoke.ORACLE['effects'])
        self.assertEqual(len([row for row in smoke.ORACLE['taints'] if row[0][0] == 'taint_positive.uc']), 2)
        for group in ('bindings', 'effects', 'taints'):
            self.assertFalse(any(row[0][0] in ('issue_shadow.uc', 'taint_shadow.uc') for row in smoke.ORACLE[group]))

    def test_entity_uri_and_full_span(self):
        cell = {'label': 'CallExpression', 'url': {'uri': 'file:///staged/root/a.uc',
                'startLine': 4, 'startColumn': 3, 'endLine': 4, 'endColumn': 35}}
        self.assertEqual(smoke.entity(cell, Path('/staged/root')), ['a.uc', 4, 3, 4, 35])
        for uri in ('file:///staged/root/../a.uc', 'file:///staged/root/%ZZ', 'file://evil/a.uc'):
            with self.subTest(uri=uri), self.assertRaises(SystemExit):
                smoke.entity({'label': 'CallExpression', 'url': dict(cell['url'], uri=uri)}, Path('/staged/root'))


if __name__ == '__main__':
    unittest.main()
