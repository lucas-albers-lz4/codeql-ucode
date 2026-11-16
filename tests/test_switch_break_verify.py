"""Unit tests of the result verifier; rows here are synthetic, not CodeQL evidence."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "ql/test/switch-break"
spec = importlib.util.spec_from_file_location("switch_break_verify", ROOT / "scripts/switch-break-verify.py")
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load switch-break verifier")
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)


def edge_row(a, b):
    keys = ("sourceFile", "sourceLine", "sourceColumn", "sourceEndLine", "sourceEndColumn",
            "targetFile", "targetLine", "targetColumn", "targetEndLine", "targetEndColumn")
    return dict(zip(keys, a + b))


def flow_row(a, b):
    keys = ("file", "sourceLine", "sourceColumn", "sourceEndLine", "sourceEndColumn",
            "readLine", "readColumn", "readEndLine", "readEndColumn")
    return dict(zip(keys, a + b[1:]))


class SwitchBreakVerifierTests(unittest.TestCase):
    def setUp(self):
        self.edges = [edge_row(a, b) for a, targets in verify.expected_edges(SOURCE).items() for b in targets]
        a = verify.span(SOURCE, "controls.uc", 3, "source()")
        b = verify.span(SOURCE, "controls.uc", 4, "x")
        self.flow = [flow_row(a, b)]

    def test_accepts_expected_synthetic_rows(self):
        verify.verify_edges(SOURCE, self.edges)
        verify.verify_flow(SOURCE, self.flow)

    def test_rejects_bypass_despite_safe_edge(self):
        a = verify.span(SOURCE, "break.uc", 5, "break;")
        b = verify.span(SOURCE, "break.uc", 9, "print")
        with self.assertRaisesRegex(ValueError, "CFG successors"):
            verify.verify_edges(SOURCE, self.edges + [edge_row(a, b)])

    def test_rejects_count_preserving_wrong_target(self):
        a = verify.span(SOURCE, "break_control.uc", 5, "break;")
        b = verify.span(SOURCE, "break_control.uc", 9, "print")
        rows = [r for r in self.edges if (r["sourceFile"], r["sourceLine"], r["sourceColumn"]) != a[:3]]
        with self.assertRaisesRegex(ValueError, "CFG successors"):
            verify.verify_edges(SOURCE, rows + [edge_row(a, b)])

    def test_rejects_source_flow_and_missing_positive(self):
        a = verify.span(SOURCE, "break.uc", 3, "source()")
        b = verify.span(SOURCE, "break.uc", 9, "x")
        with self.assertRaisesRegex(ValueError, "overwritten source"):
            verify.verify_flow(SOURCE, self.flow + [flow_row(a, b)])
        with self.assertRaisesRegex(ValueError, "missing positive"):
            verify.verify_flow(SOURCE, [])


if __name__ == "__main__":
    unittest.main()
