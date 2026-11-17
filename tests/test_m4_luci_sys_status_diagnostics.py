"""Exercise every status smoke database through its standalone entry point.

The adapter replays the observed semantic CSV and models diagnostic receipts;
real CodeQL runs remain necessary to establish actual routing and extraction.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class StatusSmokeDiagnostics(unittest.TestCase):
    def run_smoke(self, leg='', fault='', helper_edit=None):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        temp = Path(directory.name)
        root = temp / 'checkout'
        shutil.copytree(ROOT / 'scripts', root / 'scripts')
        shutil.copytree(ROOT / 'ql', root / 'ql')
        if helper_edit is not None:
            helper = root / 'scripts/m4-smoke-diagnostics.sh'
            original = helper.read_text()
            rewritten = helper_edit(original)
            self.assertNotEqual(rewritten, original, 'helper edit did not apply')
            helper.write_text(rewritten)
        extractor = root / 'extractor-pack/tools/linux64/extractor'
        extractor.parent.mkdir(parents=True)
        extractor.touch(mode=0o755)
        binary = temp / 'bin'
        binary.mkdir()
        shutil.copy(ROOT / 'tests/m4_status_fake_codeql.py', binary / 'codeql')
        (binary / 'codeql').chmod(0o755)
        tmp = temp / 'tmp'
        tmp.mkdir()
        env = os.environ.copy()
        env.update(PATH=str(binary) + os.pathsep + env['PATH'], TMPDIR=str(tmp),
                   CODEQL_UCODE_SMOKE_PACKS_READY=str(root), STATUS_TEST_ROOT=str(root),
                   STATUS_TEST_LEG=leg, STATUS_TEST_FAULT=fault,
                   PYTHONDONTWRITEBYTECODE='1', PYTHONOPTIMIZE=str(sys.flags.optimize))
        return subprocess.run(['bash', str(root / 'scripts/m4-luci-sys-status-exec-smoke.sh')],
                              cwd=root, env=env, text=True, capture_output=True)

    def test_pristine_all_three_databases_have_receipts(self):
        result = self.run_smoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count('M4 extraction accepted'), 3, result.stdout)

    def test_malformed_source_rejected_in_each_leg(self):
        for leg in ('main', 'dispatch', 'evidence'):
            with self.subTest(leg=leg):
                result = self.run_smoke(leg, 'malformed')
                self.assertNotIn('fake codeql rejected', result.stderr)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn('expected zero extraction errors', result.stderr)
                self.assertIn('parse error for ' + leg, result.stderr)
                self.assertIn('expected exact successful-file multiset', result.stderr)

    def test_error_guard_independent_of_identity(self):
        for leg in ('main', 'dispatch', 'evidence'):
            with self.subTest(leg=leg):
                result = self.run_smoke(leg, 'error_only')
                self.assertNotIn('fake codeql rejected', result.stderr)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn('expected zero extraction errors', result.stderr)
                self.assertNotIn('expected exact successful-file multiset', result.stderr)

    def test_identity_guard_independent_of_errors(self):
        for leg in ('main', 'dispatch', 'evidence'):
            for fault in ('omit0', 'omit1'):
                with self.subTest(leg=leg, fault=fault):
                    result = self.run_smoke(leg, fault)
                    self.assertNotIn('fake codeql rejected', result.stderr)
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertIn('expected exact successful-file multiset', result.stderr)
                    self.assertNotIn('expected zero extraction errors', result.stderr)

    def test_invalid_helper_option_is_rejected(self):
        def inject(original):
            return original.replace('--output="$DB/$diagnostic.bqrs"',
                                    '--output="$DB/$diagnostic.bqrs" --bogus-pr115')

        result = self.run_smoke(helper_edit=inject)
        self.assertIn('fake codeql rejected: unknown query run option --bogus-pr115', result.stderr)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertNotIn('M4 extraction accepted', result.stdout)

    def test_helper_search_path_must_be_exact(self):
        def narrow(original):
            return original.replace('--search-path="$QLPATH"', '--search-path="$ROOT/ql/src"')

        result = self.run_smoke(helper_edit=narrow)
        self.assertIn('fake codeql rejected: wrong search path', result.stderr)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertNotIn('M4 extraction accepted', result.stdout)


if __name__ == '__main__':
    unittest.main()
