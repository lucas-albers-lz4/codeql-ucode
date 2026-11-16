"""The local-helper verifier compares full entity identities, not counts."""
import hashlib
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

    def test_review_controls_pin_spans_and_generic_consumers(self):
        o = smoke.ORACLE
        self.assertIn([['within_declaration.uc', 5, 5, 5, 37]], o['raw'])
        self.assertIn([['argument_escape.uc', 5, 3, 5, 35]], o['raw'])
        self.assertIn([['generic_positive.uc', 3, 1, 3, 20], ['generic_positive.uc', 2, 10, 2, 20]], o['generic_bindings'])
        self.assertTrue(any(row[0][0] == 'generic_taint_positive.uc' for row in o['generic_effects']))
        self.assertEqual(sum(row[0][0] == 'generic_taint_positive.uc' for row in o['generic_taints']), 2)
        self.assertFalse(any(row[0][0] == 'generic_taint_shadow.uc' for k in ('generic_bindings', 'generic_effects', 'generic_taints') for row in o[k]))

    def test_exact_delta_rejects_collateral_and_wrong_span(self):
        base = [[['a.uc', 1, 1, 1, 2], ['a.uc', 2, 1, 2, 3]]]
        extra = [['b.uc', 1, 1, 1, 2], ['b.uc', 2, 1, 2, 3]]
        smoke.assert_delta('addition', base + [extra], base, [extra], [])
        for wrong in ([], base, base + [[extra[0], ['b.uc', 2, 1, 2, 4]]]):
            with self.subTest(wrong=wrong), self.assertRaises(SystemExit):
                smoke.assert_delta('addition', wrong, base, [extra], [])

    def test_new_input_hashes_and_source_slices(self):
        expected = {
            ('within_declaration.uc', 5, 5, 37): "callPackageVersionCheck('netifd')",
            ('within_declaration.uc', 2, 10, 32): 'callPackageVersionCheck',
            ('within_declaration.uc', 3, 3, 15): "popen('true')",
            ('argument_escape.uc', 5, 3, 35): "callPackageVersionCheck('netifd')",
            ('argument_escape.uc', 4, 11, 33): 'callPackageVersionCheck',
            ('generic_positive.uc', 3, 1, 20): "localHelper('value')",
            ('generic_positive.uc', 2, 10, 20): 'localHelper',
            ('generic_taint_positive.uc', 4, 3, 22): "localHelper('value')",
            ('generic_taint_positive.uc', 2, 29, 51): 'popen(request.args.cmd)',
            ('generic_taint_positive.uc', 2, 35, 46): 'request.args',
            ('generic_taint_positive.uc', 2, 35, 50): 'request.args.cmd',
            ('generic_taint_shadow.uc', 4, 3, 22): "localHelper('value')",
        }
        for (name, line, start, end), literal in expected.items():
            with self.subTest(name=name, line=line, start=start):
                data = (smoke.CORPUS / name).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), smoke.ORACLE['inputs'][name])
                self.assertEqual(data.decode().splitlines()[line - 1][start - 1:end], literal)
        self.assertEqual(len(smoke.ORACLE['wrapped_raw']), 5)

    def test_identity_mutation_queries_keep_original_anchor_and_select(self):
        for case in smoke.IDENTITY_CASES:
            label, group, _, _, _, _, old, new = case
            path = {
                'bindings': ROOT / 'ql/src/extractor-smoke/ModelsLocalHelperBindings.ql',
                'effects': ROOT / 'ql/src/m3/GetFeaturesPopen.ql',
                'taints': ROOT / 'ql/src/m3/GetFeaturesHelperTaint.ql',
            }[group]
            source = path.read_text()
            with self.subTest(label=label):
                mutant = smoke.identity_mutant_text(source, case)
                self.assertEqual(source.count(old), 1)
                self.assertIn(new, mutant)
                self.assertEqual(mutant.count('reportIdentity('), 2)
                self.assertEqual(mutant.count('sameFileCall('), source.count('sameFileCall('))

    def test_entity_uri_and_full_span(self):
        cell = {'label': 'CallExpression', 'url': {'uri': 'file:///staged/root/a.uc',
                'startLine': 4, 'startColumn': 3, 'endLine': 4, 'endColumn': 35}}
        self.assertEqual(smoke.entity(cell, Path('/staged/root')), ['a.uc', 4, 3, 4, 35])
        for uri in ('file:///staged/root/../a.uc', 'file:///staged/root/%ZZ', 'file://evil/a.uc'):
            with self.subTest(uri=uri), self.assertRaises(SystemExit):
                smoke.entity({'label': 'CallExpression', 'url': dict(cell['url'], uri=uri)}, Path('/staged/root'))


if __name__ == '__main__':
    unittest.main()
