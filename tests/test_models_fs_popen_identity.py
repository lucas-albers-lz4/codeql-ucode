"""Identity normalization and exact-oracle regression tests for the Models smoke."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('models_smoke', ROOT / 'scripts/models-fs-popen-smoke.py')
assert spec is not None and spec.loader is not None
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


class EntityIdentityTest(unittest.TestCase):
    def test_unshadowed_expression_arrow_is_pinned(self):
        self.assertIn(['arrow_unshadowed.uc', 2, 15, 2, 33], smoke.EXPECTED_CALLS)

    def test_full_url_and_scalar_are_preserved(self):
        source = Path('/staged/source root')
        entity = {'label': 'CallExpression', 'url': {'uri': 'file:///staged/source%20root/x.uc',
                  'startLine': 2, 'startColumn': 3, 'endLine': 2, 'endColumn': 11}}
        self.assertEqual(smoke.normalize_rows([[entity, 'file:///domain/input']], source),
                         [[{'label': 'CallExpression', 'entity': ['x.uc', 2, 3, 2, 11]}, 'file:///domain/input']])

    def test_outside_root_and_malformed_uri_are_rejected(self):
        for uri in ('file:///staged/root2/x', 'https://host/staged/root/x', 'file://host/staged/root/x',
                    'file:///staged/root/../x', 'file:///staged/root/%2e%2e/x',
                    'file:///staged/root/%ZZ', 'file:///staged/root/%00'):
            entity = {'label': 'CallExpression', 'url': {'uri': uri, 'startLine': 1,
                      'startColumn': 1, 'endLine': 1, 'endColumn': 2}}
            with self.subTest(uri=uri), self.assertRaises(SystemExit):
                smoke.normalize_rows([[entity]], Path('/staged/root'))

    def test_same_type_wrong_end_span_rejected(self):
        expected = {('x.uc', 2, 3, 2, 11)}
        wrong = [[{'label': 'CallExpression', 'entity': ['x.uc', 2, 3, 2, 12]}]]
        with self.assertRaises(SystemExit):
            smoke.named_oracle(wrong, expected)

    def test_count_preserving_wrong_consumer_entity_rejected(self):
        expected = [[{'label': 'MemberExpression', 'entity': ['luci', 1, 2, 1, 3]}, 'message',
                     {'label': 'CallExpression', 'entity': ['luci', 4, 1, 4, 9]}]]
        wrong = [[expected[0][0], 'message', {'label': 'CallExpression', 'entity': ['luci', 4, 1, 4, 8]}]]
        with self.assertRaises(SystemExit):
            smoke.consumer_oracle('probe', wrong, expected)


if __name__ == '__main__':
    unittest.main()
