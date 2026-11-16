"""Independent multiset oracle must reject equal-count wrong identities."""
import csv
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('construction_verify', ROOT / 'scripts/setlocaltime-construction-verify.py')
if spec is None or spec.loader is None:
    raise RuntimeError('cannot load construction verifier')
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)
ORACLE = ROOT / 'ql/test/setlocaltime-construction-real-oracle.csv'


class ExactTableOracle(unittest.TestCase):
    def setUp(self):
        with ORACLE.open(newline='', encoding='utf-8') as f:
            self.rows = list(csv.reader(f, strict=True))
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.actual = Path(self.temp.name) / 'actual.csv'

    def check(self, rows, accepted):
        with self.actual.open('w', encoding='utf-8', newline='') as f:
            csv.writer(f, lineterminator='\n').writerows(rows)
        if accepted:
            verify.verify(self.actual, ORACLE)
        else:
            with self.assertRaises(ValueError):
                verify.verify(self.actual, ORACLE)

    def test_reordering_is_allowed(self):
        self.check([self.rows[0], *reversed(self.rows[1:])], True)

    def test_same_count_wrong_sink_identity_is_rejected(self):
        rows = [r[:] for r in self.rows]
        idx = rows[0].index('sink_start_line')
        for row in rows[1:]:
            row[idx] = '112'
        self.check(rows, False)

    def test_same_count_swapped_fields_are_rejected(self):
        rows = [r[:] for r in self.rows]
        idx = rows[0].index('field_name')
        rows[1][idx], rows[2][idx] = rows[2][idx], rows[1][idx]
        self.check(rows, False)

    def test_duplicate_replacing_other_slot_is_rejected(self):
        rows = [r[:] for r in self.rows]
        rows[-1] = rows[-2][:]
        self.check(rows, False)

    def test_off_by_one_endpoint_is_rejected(self):
        rows = [r[:] for r in self.rows]
        rows[1][rows[0].index('field_end_column')] = '80'
        self.check(rows, False)

    def test_missing_row_is_rejected(self):
        self.check(self.rows[:-1], False)

    def test_wrong_header_is_rejected(self):
        rows = [r[:] for r in self.rows]
        rows[0][0] = 'authority'
        self.check(rows, False)


if __name__ == '__main__':
    unittest.main()
