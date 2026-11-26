#!/usr/bin/env python3
"""Focused preflight and identity controls for the release runner."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


spec = importlib.util.spec_from_file_location(
    "installed_stage", Path(__file__).resolve().parents[1] / "runner/run-installed-stage.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class InstalledStageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stage = self.root / "stage"
        self.stage.mkdir()
        self.rel = "usr/share/rpcd/ucode/example"
        source = self.stage / self.rel
        source.parent.mkdir(parents=True)
        source.write_text("return 1;\n")
        self.entry = {"path": self.rel, "sha256": runner.sha256(source),
                      "expect_success": True,
                      "route": {"classification": "plain", "reason": "rpcd_raw_mode_full_path",
                                "status": "plain_route_selected", "inconclusive_reason": None}}
        self.oracle = self.root / "oracle.json"
        self.write_oracle()

    def write_oracle(self):
        self.oracle.write_text(json.dumps({"schema": "ucode-installed-stage-v1", "files": [self.entry]}))

    def test_accepts_exact_source_and_route(self):
        oracle = runner.load_oracle(self.oracle, self.stage)
        receipt = self.root / "routing.json"
        receipt.write_text(json.dumps({"input_count": 1, "duplicate_input_count": 0,
            "decisions": [{"path": str(self.stage / self.rel), "installed_path": self.rel,
                           **self.entry["route"]}]}))
        runner.check_route(receipt, self.stage, oracle)

    def test_changed_source_and_extra_file_fail_before_run(self):
        (self.stage / self.rel).write_text("return 2;\n")
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            runner.load_oracle(self.oracle, self.stage)
        (self.stage / self.rel).write_text("return 1;\n")
        (self.stage / "extra.uc").write_text("return 3;\n")
        with self.assertRaisesRegex(ValueError, "inventory mismatch"):
            runner.load_oracle(self.oracle, self.stage)

    def test_duplicate_and_traversal_fail(self):
        self.entry["path"] = "../outside.uc"
        self.write_oracle()
        with self.assertRaisesRegex(ValueError, "invalid stage path"):
            runner.load_oracle(self.oracle, self.stage)
        self.entry["path"] = self.rel
        self.oracle.write_text(json.dumps({"schema": "ucode-installed-stage-v1",
                                            "files": [self.entry, self.entry]}))
        with self.assertRaisesRegex(ValueError, "duplicate stage path"):
            runner.load_oracle(self.oracle, self.stage)

    def test_wrong_route_or_duplicate_fails(self):
        oracle = runner.load_oracle(self.oracle, self.stage)
        receipt = self.root / "routing.json"
        decision = {"path": str(self.stage / self.rel), "installed_path": self.rel,
                    **self.entry["route"]}
        decision["reason"] = "ucode_extension"
        receipt.write_text(json.dumps({"input_count": 1, "duplicate_input_count": 0,
                                       "decisions": [decision]}))
        with self.assertRaisesRegex(ValueError, "route reason mismatch"):
            runner.check_route(receipt, self.stage, oracle)

    def test_excluded_regular_file_is_part_of_route_oracle(self):
        excluded_path = self.stage / "etc/config/example"
        excluded_path.parent.mkdir(parents=True)
        excluded_path.write_text("config example\n")
        excluded = {"path": "etc/config/example", "sha256": runner.sha256(excluded_path),
                    "expect_success": False,
                    "route": {"classification": "excluded", "reason": "no_ucode_route",
                              "status": "excluded", "inconclusive_reason": None}}
        self.oracle.write_text(json.dumps({"schema": "ucode-installed-stage-v1",
                                           "files": [self.entry, excluded]}))
        oracle = runner.load_oracle(self.oracle, self.stage)
        receipt = self.root / "routing.json"
        receipt.write_text(json.dumps({"input_count": 2, "duplicate_input_count": 0,
            "decisions": [
                {"path": str(self.stage / self.rel), "installed_path": self.rel,
                 **self.entry["route"]},
                {"path": str(excluded_path), "installed_path": excluded["path"],
                 **excluded["route"]}]}))
        runner.check_route(receipt, self.stage, oracle)


if __name__ == "__main__":
    unittest.main()
