"""Exact source-shape table oracle; no authorization conclusions."""
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / 'scripts/single-return-system-oracle.py'
spec = importlib.util.spec_from_file_location('single_return_system_oracle', PATH)
module = importlib.util.module_from_spec(spec)


class OracleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec.loader.exec_module(module)

    def test_exact_positive_multiset(self):
        module.check_rows(module.EXPECTED)

    def test_missing_duplicate_and_same_count_wrong_span(self):
        rows = module.EXPECTED
        wrong = [list(r) for r in rows]
        wrong[0][2] += 1
        for data in (rows[:-1], rows + [rows[0]], wrong, [rows[0], rows[0], rows[2]]):
            with self.subTest(data=data), self.assertRaises(ValueError):
                module.check_rows(data)

    def test_wrong_type_equal_to_integer_is_rejected(self):
        rows = [list(r) for r in module.EXPECTED]
        rows[0][1] = float(rows[0][1])
        with self.assertRaises(ValueError):
            module.check_rows(rows)


if __name__ == '__main__':
    unittest.main()
