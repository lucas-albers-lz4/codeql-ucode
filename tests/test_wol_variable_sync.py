"""Controls for the full shared-to-scoped binding synchronization guard."""
import importlib.util
import subprocess
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('wol_variable_sync', ROOT / 'scripts/wol_variable_sync.py')
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class VariableSyncTests(unittest.TestCase):
    def setUp(self):
        self.shared = sync.SHARED.read_bytes().decode('utf-8')
        self.scoped = sync.SCOPED.read_bytes().decode('utf-8')
        self.seed = sync.SEED.read_bytes()

    def test_real_and_synchronized_non_import_change(self):
        sync.verify(self.shared, self.scoped, self.seed)
        shared = self.shared.replace(' * A variable defined by a lexical declarator, loop binding, catch parameter,', ' * Reviewed variable definition: lexical declarator, loop binding, catch parameter,', 1)
        sync.verify(shared, sync.scoped_source(shared), self.seed)

    def test_independent_body_and_seed_drift(self):
        for shared, scoped, seed in (
            (self.shared + '\n// changed\n', self.scoped, self.seed),
            (self.shared, self.scoped + '\n// changed\n', self.seed),
            (self.shared, self.scoped, self.seed + b'\n'),
        ):
            with self.subTest(shared=shared == self.shared, scoped=scoped == self.scoped, seed=seed == self.seed):
                with self.assertRaises(ValueError):
                    sync.verify(shared, scoped, seed)

    def test_crlf_drift_is_detected(self):
        with self.assertRaises(ValueError):
            sync.verify(self.shared, self.scoped.replace('\n', '\r\n'), self.seed)

    def test_smoke_guard_loads_under_isolated_python(self):
        command = "import runpy; runpy.run_path(%r)['check_variable_sync']()" % str(ROOT / 'scripts/m4-wol-query-local-smoke.py')
        subprocess.run([sys.executable, '-I', '-B', '-c', command], check=True)

    def test_missing_duplicate_or_changed_boundary_fails(self):
        anchor = 'private predicate access(AstNode node, Variable v, string name) {\n'
        for changed in (self.shared.replace(anchor, '', 1), self.shared + '\n' + anchor,
                        self.shared.replace(anchor, anchor.replace('access(', 'access2('), 1)):
            with self.subTest(changed=changed[-50:]), self.assertRaises(ValueError):
                sync.scoped_source(changed)

    def test_new_or_changed_relative_import_fails(self):
        for changed in (self.shared.replace('private import Cached', 'private import Cached\nprivate import NewLocal'),
                        self.shared.replace('private import internal.AstNodes', 'private import Other'),
                        self.shared + '\n/* prefix */ private import NewLocal\n',
                        self.shared + '\n} private import NewLocal\n'):
            with self.assertRaisesRegex(ValueError, 'import list'):
                sync.scoped_source(changed)


if __name__ == '__main__':
    unittest.main()
