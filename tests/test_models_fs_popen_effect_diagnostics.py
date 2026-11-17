"""Test effect-database diagnostic wiring independently of semantic queries."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('effect_smoke', ROOT / 'scripts/models-fs-popen-smoke.py')
if spec is None or spec.loader is None:
    raise RuntimeError('cannot load Models smoke')
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)

CASES = ('real', 'positive', 'negative-method', 'negative-command', 'negative-member',
         'negative-import', 'negative-formal-shadow', 'negative-local-shadow',
         'negative-escaped-module')


class SemanticReached(Exception):
    pass


class EffectExtractionTest(unittest.TestCase):
    def run_effect(self, variant, mutant=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'checkout'
            staged = Path(tmp) / 'stage'
            fixture = Path('ql/test/extractor-smoke/usr/share/rpcd/ucode/luci')
            (root / fixture).parent.mkdir(parents=True)
            shutil.copyfile(ROOT / fixture, root / fixture)
            (root / 'scripts').mkdir()
            helper = root / 'scripts/m4-smoke-diagnostics.py'
            shutil.copyfile(ROOT / 'scripts/m4-smoke-diagnostics.py', helper)
            if mutant:
                text = helper.read_text()
                token = ('if errors:' if mutant == 'errors' else
                         'if Counter(map(encode, success)) != Counter(map(encode, wanted)):')
                self.assertEqual(text.count(token), 1)
                helper.write_text(text.replace(token, token.replace('if ', 'if False and ', 1)))
            source = staged / 'effect-source'
            files = [source / 'modules' / case / 'root/usr/share/rpcd/ucode/luci' for case in CASES]
            def receipt(path):
                return [{'label': str(path), 'url': {'uri': path.as_uri(), 'startLine': 0,
                        'startColumn': 0, 'endLine': 0, 'endColumn': 0}}, '']
            successes = [receipt(p) for p in files]
            errors = []
            if variant == 'error':
                errors = [[{'label': 'parse error'}, 'parse error', 2]]
            elif variant.startswith('omit'):
                successes.pop(int(variant[4:]))
            elif variant.startswith('duplicate'):
                successes.append(successes[int(variant[9:])])
            elif variant.startswith('substitute'):
                successes[int(variant[10:])] = receipt(source / 'elsewhere/luci')
            diagnostics = {
                'SuccessfullyExtractedFiles': {'#select': {'columns': [{'name': 'f', 'kind': 'Entity'}, {'kind': 'String'}], 'tuples': successes}},
                'ExtractionErrors': {'#select': {'columns': [{'name': 'error', 'kind': 'Entity'}, {'kind': 'String'}, {'kind': 'Integer'}], 'tuples': errors}},
            }
            db = root / '.codeql-database/m4-models-fs-popen-effect-controls'
            def command(args, **kwargs):
                if args[1:3] == ['database', 'index-files']:
                    routing = db / 'trap/ucode/routing.json'
                    routing.parent.mkdir(parents=True)
                    routing.write_text(json.dumps({'input_count': 9, 'plain_count': 9,
                                                   'excluded_count': 0, 'duplicate_input_count': 0}))
                return None
            seen = []
            def run_query(query, database, output_dir, name, **kwargs):
                if name not in diagnostics:
                    raise SemanticReached()
                self.assertEqual(query, root / 'ql/src/diagnostics' / (name + '.ql'))
                self.assertEqual(database, db)
                seen.append(name)
                return diagnostics[name]
            with mock.patch.dict(os.environ, {'PYTHONOPTIMIZE': str(sys.flags.optimize)}), \
                 mock.patch.object(smoke, 'ROOT', root), mock.patch.object(smoke, 'EFFECTS', ROOT / 'ql/test/effect-controls/getblock'), \
                 mock.patch.object(smoke, 'CODEQL', 'codeql'), mock.patch.object(smoke, 'command', side_effect=command), \
                 mock.patch.object(smoke, 'run_query', side_effect=run_query):
                try:
                    smoke.run_effect_database(staged)
                except SemanticReached:
                    return 'accepted', '', seen
                except SystemExit as exc:
                    return 'rejected', str(exc), seen
                self.fail('effect runner neither rejected nor reached the semantic queries')

    def test_valid_inventory_reaches_semantics(self):
        status, message, seen = self.run_effect('valid')
        self.assertEqual((status, seen), ('accepted', ['SuccessfullyExtractedFiles', 'ExtractionErrors']))

    def test_error_only_is_rejected(self):
        status, message, _ = self.run_effect('error')
        self.assertEqual(status, 'rejected')
        self.assertIn('expected zero extraction errors', message)
        self.assertNotIn('expected exact successful-file multiset', message)

    def test_identity_only_is_rejected(self):
        for i in range(len(CASES)):
            for kind in ('omit', 'duplicate', 'substitute'):
                with self.subTest(case=CASES[i], kind=kind):
                    status, message, _ = self.run_effect(f'{kind}{i}')
                    self.assertEqual(status, 'rejected')
                    self.assertIn('expected exact successful-file multiset', message)
                    self.assertNotIn('expected zero extraction errors', message)

    def test_each_guard_is_necessary(self):
        for variant, mutant in (('error', 'errors'), ('omit0', 'identity')):
            with self.subTest(mutant=mutant):
                status, message, seen = self.run_effect(variant, mutant)
                self.assertEqual((status, seen), ('accepted', ['SuccessfullyExtractedFiles', 'ExtractionErrors']), message)


if __name__ == '__main__':
    unittest.main()
