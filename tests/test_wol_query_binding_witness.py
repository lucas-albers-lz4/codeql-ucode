"""Offline controls for the WOL binding witness verifier."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('wol_smoke', ROOT / 'scripts/m4-wol-query-local-smoke.py')
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)

class BindingWitnessTests(unittest.TestCase):
    @staticmethod
    def fixture():
        witness = {'path': 'fixture.uc', 'occurrence': {'line': 2, 'start_column': 5, 'end_column': 11},
                   'declaration': {'line': 1, 'start_column': 1, 'end_column': 7},
                   'declaration_kind': 'Identifier', 'variable_group': 'outer'}
        row = ['fixture.uc', 'read', {'id': 10}, 2, 5, 2, 11, {'id': 20}, {'id': 30},
               'Identifier', 1, 1, 1, 7]
        return witness, row

    def test_exact_single_binding_and_ambiguity(self):
        witness, row = self.fixture()
        smoke.verify_binding_witnesses([row], [witness])
        wrong = list(row); wrong[8] = {'id': 31}
        with self.assertRaisesRegex(RuntimeError, 'missing or ambiguous'):
            smoke.verify_binding_witnesses([row, wrong], [witness])
        wrong = list(row); wrong[1] = 'write'
        with self.assertRaisesRegex(RuntimeError, 'missing or ambiguous'):
            smoke.verify_binding_witnesses([wrong], [witness])

    def test_distinct_groups_cannot_share_variable_or_declaration(self):
        first, row = self.fixture()
        second = dict(first, occurrence={'line': 3, 'start_column': 5, 'end_column': 11},
                      variable_group='inner')
        other = list(row); other[2] = {'id': 11}; other[3:7] = [3, 5, 3, 11]
        for variable, declaration in ((20, 31), (21, 30)):
            other[7], other[8] = {'id': variable}, {'id': declaration}
            with self.subTest(variable=variable, declaration=declaration), self.assertRaisesRegex(
                RuntimeError, 'distinct binding groups collapsed'
            ):
                smoke.verify_binding_witnesses([row, other], [first, second])

if __name__ == '__main__':
    unittest.main()
