"""Offline contract for source-declared fs guard query generation."""
import ast
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

stat = load('stat_guard_inputs', 'ql/test/issue155-stat-observation/run-smoke.py')
rename = load('rename_guard_ci', 'scripts/issue155-rename-ci.py')
open_wx = load('open_guard_ci', 'scripts/issue155-open-wx-ci.py')
SOURCE = (ROOT / 'ql/lib/codeql/ucode/internal/SourceDeclaredFs.qll').read_text()

class GuardQueryTests(unittest.TestCase):
    def test_seven_distinct_named_variants_and_guard_removal(self):
        families = ((stat.model_mutations(SOURCE), 'stat', 'issue155-model-'),
                    (rename.guard_mutations(), 'rename', 'issue155-rename-guard-'),
                    (open_wx.guard_mutations(), 'open wx', 'issue155-open-wx-guard-'))
        guards = self.guard_anchors()
        for variants, family, prefix in families:
            self.assertEqual(set(variants), set(guards))
            self.assertEqual(len(set(variants.values())), 7)
            for name, query in variants.items():
                self.assertIn(f'@name Testing-only {family} {name} guard mutation', query)
                ids = [line.strip().removeprefix('* ').removeprefix('@id ') for line in query.splitlines() if line.strip().startswith('* @id ')]
                self.assertEqual(ids, [f'ucode/testing/{prefix}{name}-mutant'])
                self.assertNotIn(guards[name], query)
                for other, guard in guards.items():
                    if other != name:
                        self.assertEqual(query.count(guard), 1, (name, other))

    @staticmethod
    def guard_anchors():
        tree = ast.parse((ROOT / 'ql/test/issue155-stat-observation/run-smoke.py').read_text())
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'source_declared_fs_guard_queries')
        assignment = next(n for n in fn.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'guards' for t in n.targets))
        return ast.literal_eval(assignment.value)

    def test_siblings_ignore_stat_wrapper_format_and_projection(self):
        for module in (rename, open_wx):
            before = module.guard_mutations()
            with patch.object(module.common.inputs, 'model_mutations', return_value={'changed': 'from wrapped\nselect changed'}):
                self.assertEqual(module.guard_mutations(), before)

    def test_every_missing_and_duplicate_guard_is_rejected(self):
        guards = self.guard_anchors()
        self.assertEqual(len(guards), 7)
        marker = "/** A selected dot member or any bracket member of the namespace identifier. */"
        named, namespace = SOURCE.split(marker, 1)
        for name, guard in guards.items():
            self.assertEqual(named.count(guard), 1)
            for changed in (named.replace(guard, ''), named.replace(guard, guard + guard)):
                altered = changed + marker + namespace
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, f'model mutation target changed: {name}'):
                    stat.source_declared_fs_guard_queries(altered, family='test', id_prefix='test-', selection='')
            self.assertEqual(stat.model_mutations(SOURCE), stat.model_mutations(SOURCE + guard))

if __name__ == '__main__':
    unittest.main()
