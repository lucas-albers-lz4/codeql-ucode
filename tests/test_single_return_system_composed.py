"""Replay the complete smoke through a strict synthetic CodeQL boundary.

Rows are synthetic wiring fixtures, not fresh extraction or query results. The
real smoke and its real verifier/oracle/control scripts execute in each case.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SMOKE = 'scripts/m4-single-return-system-shape-smoke.sh'
ADAPTER = ROOT / 'tests/single_return_system_fake_codeql.py'


class ComposedSmokeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.temp = Path(self.tmp.name).resolve()
        self.checkout = self.temp / 'checkout'
        self.checkout.mkdir()
        for directory in ('ql/src', 'ql/lib', 'ql/test/single-return-system'):
            shutil.copytree(ROOT / directory, self.checkout / directory)
        for name in ('.codeqlmanifest.json', SMOKE, 'scripts/ql-smoke-pack-install.sh',
                     'scripts/m4-smoke-diagnostics.py', 'scripts/single-return-system-oracle.py',
                     'scripts/single-return-system-controls.py',
                     'ql/test/extractor-smoke/usr/share/rpcd/ucode/luci'):
            target = self.checkout / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        extractor = self.checkout / 'extractor-pack/tools/linux64/extractor'
        extractor.parent.mkdir(parents=True)
        extractor.write_text('fixture: never executed\n')
        extractor.chmod(0o755)
        self.binary = self.temp / 'bin'
        self.binary.mkdir()
        fake = self.binary / 'codeql'
        fake.write_text('#!' + sys.executable + '\n' + ADAPTER.read_text())
        fake.chmod(0o755)
        self.trace = self.temp / 'trace.jsonl'
        self.state = self.temp / 'state.json'
        self.env = os.environ.copy()
        self.env.update(PATH=str(self.binary) + os.pathsep + self.env.get('PATH', ''),
                        TMPDIR=str(self.temp), SHAPE_FAKE_ROOT=str(self.checkout),
                        SHAPE_FAKE_TRACE=str(self.trace), SHAPE_FAKE_STATE=str(self.state),
                        PYTHONDONTWRITEBYTECODE='1')
        self.env.pop('CODEQL_UCODE_SMOKE_PACKS_READY', None)
        self.env.pop('SINGLE_RETURN_KEEP_EVIDENCE', None)
        if sys.flags.optimize:
            self.env['PYTHONOPTIMIZE'] = '1'
        else:
            self.env.pop('PYTHONOPTIMIZE', None)

    def run_smoke(self, mode):
        env = dict(self.env, SHAPE_FAKE_CASE=mode)
        result = subprocess.run(['bash', str(self.checkout / SMOKE)], cwd=self.checkout,
                                env=env, capture_output=True, text=True, timeout=90)
        trace = [json.loads(line) for line in self.trace.read_text().splitlines()]
        self.assertNotIn('fake codeql rejected', result.stderr, result.stderr)
        return result, trace

    def test_pristine_complete_smoke(self):
        result, trace = self.run_smoke('good')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('PASS bounded source-shape smoke', result.stdout)
        semantic = [e for e in trace if e['kind'] == 'semantic']
        self.assertEqual([e['name'] for e in semantic],
                         ['baseline', 'body-veto', 'literal-veto', 'wrong-start-column'])

    def test_rejects_faults_before_any_semantic_query(self):
        for case in ('error', 'omission', 'duplicate', 'substitution'):
            with self.subTest(case=case):
                self.trace.unlink(missing_ok=True)
                self.state.unlink(missing_ok=True)
                result, trace = self.run_smoke(case)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn('M4 extraction rejected:', result.stderr)
                self.assertFalse([e for e in trace if e['kind'] == 'semantic'], trace)
                self.assertEqual([e['name'] for e in trace if e['kind'] == 'diagnostic'],
                                 ['SuccessfullyExtractedFiles', 'ExtractionErrors'])

    def test_adapter_rejects_bad_smoke_command_arguments(self):
        smoke = self.checkout / SMOKE
        original = smoke.read_text()
        mutations = [
            ('extra-query-option', '--threads=1 --ram=2048', '--threads=1 --ram=2048 --invalid-shape-test'),
            ('wrong-diagnostic-decode', '--format=json --entities=url,string', '--format=json'),
            ('wrong-semantic-query-path', '$ROOT/ql/src/m4/SingleReturnFixedSystemSourceShape.ql',
             '$ROOT/ql/src/extractor-smoke/SingleReturnFixedSystemSourceShape.ql'),
        ]
        for name, before, after in mutations:
            with self.subTest(name=name):
                self.trace.unlink(missing_ok=True)
                self.state.unlink(missing_ok=True)
                self.assertIn(before, original)
                smoke.write_text(original.replace(before, after, 1))
                result = subprocess.run(['bash', str(smoke)], cwd=self.checkout,
                                        env=dict(self.env, SHAPE_FAKE_CASE='good'),
                                        capture_output=True, text=True, timeout=90)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn('fake codeql rejected', result.stderr)
        smoke.write_text(original)


if __name__ == '__main__':
    unittest.main()
