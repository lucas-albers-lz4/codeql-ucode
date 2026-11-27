"""Offline tests for UCI commit source-first fixture preflight."""

import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "uci_commit_ci", ROOT / "scripts/issue53-uci-commit-ci.py"
)
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)


class FixturePreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.fixtures = self.root / "fixtures"
        shutil.copytree(ROOT / "ql/test/issue53-uci-commit", self.fixtures)
        self.stage = self.root / "stage"
        self.stage.mkdir()
        self.patch = patch.object(ci, "FIX", self.fixtures)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def manifest(self, change):
        path = self.fixtures / "source-first.json"
        value = json.loads(path.read_text())
        change(value)
        path.write_text(json.dumps(value))

    def test_frozen_sources_and_anchors(self):
        entries = ci.stage_inputs(self.stage)
        self.assertEqual(len(entries), 31)
        self.assertEqual(
            (self.stage / "usr/share/rpcd/ucode/luci.adblock-fast").stat().st_size,
            23660,
        )

    def test_unexpected_model_cohort_fails(self):
        self.manifest(lambda m: m["entries"][0].update(expected="typo"))
        with self.assertRaisesRegex(ValueError, "classification"):
            ci.stage_inputs(self.stage)

    def test_path_escape_fails_before_staging(self):
        self.manifest(lambda m: m["entries"][0].update(path="../escape.uc"))
        with self.assertRaisesRegex(ValueError, "fixture path"):
            ci.stage_inputs(self.stage)
        self.assertEqual(list(self.stage.iterdir()), [])

    def test_inconsistent_anchor_coordinate_fails(self):
        def change(m):
            a = m["entries"][0]["anchors"]["import"]
            a["offset"] += 1

        self.manifest(change)
        with self.assertRaisesRegex(ValueError, "coordinate offset"):
            ci.stage_inputs(self.stage)

    def test_changed_bytes_fail(self):
        path = self.fixtures / "controls/positive.uc"
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "source bytes"):
            ci.stage_inputs(self.stage)


class ReceiverWriteIdentityTests(unittest.TestCase):
    @staticmethod
    def row(kind, node, variable, declaration):
        row = [None] * 11
        row[0], row[1], row[3] = "controls/receiver-write.uc", kind, {"id": node}
        row[9], row[10] = {"id": variable}, {"id": declaration}
        return row

    def test_requires_one_write_and_read_to_same_selected_declaration(self):
        path = "controls/receiver-write.uc"
        write = self.row("write", 11, 32, 60)
        read = self.row("read", 12, 32, 60)
        ci.verify_receiver_write_binding(path, 11, 12, 60, [write, read])
        cases = [
            [read],
            [write, write, read],
            [write, self.row("read", 12, 33, 60)],
            [write, self.row("read", 12, 32, 61)],
        ]
        for rows in cases:
            with (
                self.subTest(rows=rows),
                self.assertRaisesRegex(
                    ValueError, "write targets selected receiver binding"
                ),
            ):
                ci.verify_receiver_write_binding(path, 11, 12, 60, rows)


class RawEdgeIdentityTests(unittest.TestCase):
    def test_statement_edges_must_match_both_calls(self):
        edges = {1: [(-1, 10)], 2: [(-1, 20)]}

        def targets(_path, source, _field):
            return edges[source]

        ci.verify_statement_expression_edges("fixture", 1, 10, 2, 20, targets)
        edges[2] = [(-1, 10)]
        with self.assertRaisesRegex(ValueError, "statement expression edges"):
            ci.verify_statement_expression_edges("fixture", 1, 10, 2, 20, targets)

    def test_declaration_owners_must_be_distinct(self):
        parents = {1: 11, 2: 12, 11: 21, 12: 22}

        def parent(_path, node):
            return parents[node]

        ci.verify_distinct_declaration_owners("fixture", 1, 2, parent)
        parents[12] = 21
        with self.assertRaisesRegex(ValueError, "distinct declaration owners"):
            ci.verify_distinct_declaration_owners("fixture", 1, 2, parent)


if __name__ == "__main__":
    unittest.main()
