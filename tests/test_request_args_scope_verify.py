"""Offline checks for the scope smoke's frozen input and routing oracle."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('scope', ROOT / 'scripts/request-args-scope-verify.py')
scope = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scope)


class ScopeOracleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.source = self.root / 'source'
        shutil.copytree(ROOT / 'ql/test/request-args-scope', self.source)
        self.receipt = self.root / 'routing.json'
        self.route = {'input_count': 10, 'plain_count': 10, 'markup_count': 0,
                      'markup_inconclusive_count': 0, 'uncertain_count': 0,
                      'excluded_count': 0, 'duplicate_input_count': 0,
                      'decisions': [dict(path=str(self.source / path), installed_path=path,
                                         classification='plain', status='plain_route_selected',
                                         reason='rpcd_raw_mode_full_path' if path.startswith(scope.BASE) else 'ucode_extension')
                                    for path in scope.ALL]}

    def check_route(self, route):
        self.receipt.write_text(json.dumps(route))
        scope.verify_routing(self.source, self.receipt)

    def test_fixture_bytes_are_frozen(self):
        scope.preflight(self.source)
        (self.source / scope.ALL[0]).write_bytes(scope.TEXT.replace('\n', '\r\n').encode())
        with self.assertRaises(SystemExit):
            scope.preflight(self.source)

    def test_exact_route_and_negative_mutations(self):
        self.check_route(self.route)
        for field, value in [('path', '/other'), ('installed_path', 'wrong'),
                             ('classification', 'markup'), ('reason', 'ucode_extension'),
                             ('status', 'excluded')]:
            route = copy.deepcopy(self.route)
            route['decisions'][0][field] = value
            with self.subTest(field=field), self.assertRaises(SystemExit):
                self.check_route(route)
        route = copy.deepcopy(self.route)
        route['decisions'][-1] = route['decisions'][0]
        with self.assertRaises(SystemExit):
            self.check_route(route)
        route = copy.deepcopy(self.route)
        route['duplicate_input_count'] = 1
        with self.assertRaises(SystemExit):
            self.check_route(route)


if __name__ == '__main__':
    unittest.main()
