"""Exercise the actual declaration-order runner at failure boundaries."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
PIN = "4ccea382de2ebd7f185617bb6ea0307aa9927dbf57d2d1d57a83f3071ecd3631"
RECEIPT = b'{"fixture":"routing bytes"}\n'


class VariableOrderRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / "scripts").mkdir()
        for name in (
            "m4-variable-order-smoke.sh",
            "m4-variable-order-controls-smoke.sh",
            "ql-smoke-pack-install.sh",
            "variable-order-verify.py",
            "variable-order-controls-verify.py",
        ):
            shutil.copy2(REPO / "scripts" / name, self.root / "scripts" / name)
        src = self.root / "ql/test/variable-order"
        src.mkdir(parents=True)
        shutil.copy2(REPO / "ql/test/variable-order/order.uc", src / "order.uc")
        (self.root / "ql/test/variable-order.json").write_text(
            json.dumps({"files": {"order.uc": PIN}})
        )
        shutil.copytree(
            REPO / "ql/test/variable-order-controls",
            self.root / "ql/test/variable-order-controls",
        )
        shutil.copy2(
            REPO / "ql/test/variable-order-controls.json",
            self.root / "ql/test/variable-order-controls.json",
        )
        for platform in ("linux64", "osx64"):
            extractor = self.root / "extractor-pack/tools" / platform / "extractor"
            extractor.parent.mkdir(parents=True)
            extractor.write_text("#!/bin/sh\nexit 0\n")
            extractor.chmod(0o755)
        bindir = self.root / "bin"
        bindir.mkdir()
        codeql = bindir / "codeql"
        codeql.write_text("""#!/usr/bin/env python3
import os
from pathlib import Path
import sys
args = sys.argv[1:]
with open(os.environ["CALL_LOG"], "a") as log:
    log.write(" ".join(args[:2]) + "\\n")
if args[:2] == ["database", "init"]:
    Path(args[2]).mkdir(parents=True)
elif args[:2] == ["database", "index-files"]:
    if os.environ.get("EMIT_RECEIPT", "1") == "1":
        p = Path(args[2]) / "trap/ucode/routing.json"
        p.parent.mkdir(parents=True)
        p.write_bytes(b'{"fixture":"routing bytes"}\\n')
    status = int(os.environ.get("INDEX_STATUS", "37"))
    if status:
        print(f"index shim: injected failure {status}", file=sys.stderr)
    sys.exit(status)
else:
    print("unexpected codeql call", args, file=sys.stderr)
    sys.exit(93)
""")
        codeql.chmod(0o755)
        self.env = dict(
            os.environ,
            PATH=f"{bindir}:{os.environ['PATH']}",
            CODEQL_UCODE_SMOKE_PACKS_READY=str(self.root),
            CALL_LOG=str(self.root / "calls"),
            CP_LOG=str(self.root / "routing-copy-calls"), REAL_CP=shutil.which("cp"),
        )
        for key in ("INDEX_STATUS", "EMIT_RECEIPT", "CP_MODE"):
            self.env.pop(key, None)
        cp = bindir / "cp"
        cp.write_text("""#!/usr/bin/env python3
import os, subprocess, sys
from pathlib import Path
args = sys.argv[1:]
if args[0].endswith("/trap/ucode/routing.json"):
    with open(os.environ["CP_LOG"], "a") as log:
        log.write(args[0] + "\\n")
    if os.environ.get("CP_MODE") == "fail-route":
        print("cp shim: injected routing-copy failure", file=sys.stderr)
        sys.exit(73)
result = subprocess.run([os.environ["REAL_CP"], *args])
if result.returncode:
    sys.exit(result.returncode)
if os.environ.get("CP_MODE") == "tamper-stage" and args[0] == "ql/test/variable-order/order.uc":
    p = Path(args[1])
    raw = p.read_bytes()
    assert b"'inner'" in raw
    p.write_bytes(raw.replace(b"'inner'", b"'other'", 1))
""")
        cp.chmod(0o755)

    def run_smoke(self, script="m4-variable-order-smoke.sh", **env):
        return subprocess.run(
            ["bash", f"scripts/{script}"],
            cwd=self.root,
            env=dict(self.env, **env),
            capture_output=True,
            text=True,
            timeout=30,
        )

    def calls(self):
        p = self.root / "calls"
        return p.read_text().splitlines() if p.exists() else []

    def test_controls_failed_index_copy_failure_preserves_index_status(self):
        result = self.run_smoke(
            script="m4-variable-order-controls-smoke.sh", CP_MODE="fail-route"
        )
        out = self.root / ".codeql-database/m4-variable-order-controls"
        raw = out / "db/trap/ucode/routing.json"
        self.assertEqual(raw.read_bytes(), RECEIPT)
        self.assertEqual((self.root / "routing-copy-calls").read_text().splitlines(), [str(raw)])
        self.assertEqual(self.calls(), ["database init", "database index-files"])
        self.assertFalse((out / "routing.json").exists())
        self.assertIn("index shim: injected failure 37", result.stderr)
        self.assertIn("cp shim: injected routing-copy failure", result.stderr)
        self.assertEqual(result.returncode, 37, result.stderr)
        self.assertIn("failed to retain routing", result.stderr)

    def test_controls_failed_index_without_receipt_preserves_status(self):
        result = self.run_smoke(
            script="m4-variable-order-controls-smoke.sh",
            CP_MODE="fail-route",
            EMIT_RECEIPT="0",
        )
        out = self.root / ".codeql-database/m4-variable-order-controls"
        self.assertEqual(result.returncode, 37, result.stderr)
        self.assertEqual(self.calls(), ["database init", "database index-files"])
        self.assertFalse((out / "db/trap/ucode/routing.json").exists())
        self.assertFalse((out / "routing.json").exists())
        self.assertFalse((self.root / "routing-copy-calls").exists())
        self.assertIn("index shim: injected failure 37", result.stderr)
        self.assertNotIn("failed to retain routing", result.stderr)
        self.assertNotIn("cp shim: injected routing-copy failure", result.stderr)

    def test_controls_failed_index_retains_exact_receipt(self):
        result = self.run_smoke(script="m4-variable-order-controls-smoke.sh")
        out = self.root / ".codeql-database/m4-variable-order-controls"
        raw = out / "db/trap/ucode/routing.json"
        self.assertEqual(result.returncode, 37, result.stderr)
        self.assertEqual(self.calls(), ["database init", "database index-files"])
        self.assertEqual((self.root / "routing-copy-calls").read_text().splitlines(), [str(raw)])
        self.assertEqual(raw.read_bytes(), RECEIPT)
        self.assertEqual((out / "routing.json").read_bytes(), RECEIPT)
        self.assertNotIn("failed to retain routing", result.stderr)

    def test_controls_successful_index_copy_failure_stops_before_finalize(self):
        result = self.run_smoke(
            script="m4-variable-order-controls-smoke.sh",
            CP_MODE="fail-route",
            INDEX_STATUS="0",
        )
        out = self.root / ".codeql-database/m4-variable-order-controls"
        raw = out / "db/trap/ucode/routing.json"
        self.assertEqual(result.returncode, 73, result.stderr)
        self.assertEqual(self.calls(), ["database init", "database index-files"])
        self.assertEqual((self.root / "routing-copy-calls").read_text().splitlines(), [str(raw)])
        self.assertEqual(raw.read_bytes(), RECEIPT)
        self.assertFalse((out / "routing.json").exists())
        self.assertIn("cp shim: injected routing-copy failure", result.stderr)
        self.assertNotIn("failed to retain routing", result.stderr)

    def test_failed_index_retains_exact_receipt_and_status(self):
        result = self.run_smoke()
        self.assertEqual(result.returncode, 37, result.stderr)
        self.assertEqual(self.calls(), ["database init", "database index-files"])
        self.assertEqual(
            (
                self.root / ".codeql-database/m4-variable-order/routing.json"
            ).read_bytes(),
            RECEIPT,
        )

    def test_failed_index_without_receipt_preserves_status(self):
        result = self.run_smoke(EMIT_RECEIPT="0")
        self.assertEqual(result.returncode, 37, result.stderr)
        self.assertEqual(self.calls(), ["database init", "database index-files"])
        self.assertFalse(
            (self.root / ".codeql-database/m4-variable-order/routing.json").exists()
        )

    def test_receipt_copy_failure_does_not_hide_index_failure(self):
        result = self.run_smoke(CP_MODE="fail-route")
        self.assertEqual(result.returncode, 37, result.stderr)
        self.assertIn("failed to retain routing", result.stderr)
        self.assertEqual(self.calls(), ["database init", "database index-files"])

    def test_receipt_copy_failure_after_success_stops_before_finalize(self):
        result = self.run_smoke(CP_MODE="fail-route", INDEX_STATUS="0")
        self.assertEqual(result.returncode, 73, result.stderr)
        self.assertEqual(self.calls(), ["database init", "database index-files"])

    def test_changed_source_fixture_is_rejected_before_database_init(self):
        fixture = self.root / "ql/test/variable-order/order.uc"
        data = fixture.read_bytes()
        self.assertIn(b"'inner'", data)
        altered = data.replace(b"'inner'", b"'other'", 1)
        self.assertEqual(len(altered), len(data))
        fixture.write_bytes(altered)
        result = self.run_smoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("fixture bytes differ", result.stderr)
        self.assertEqual(self.calls(), [])
        self.assertFalse((self.root / ".codeql-database/m4-variable-order").exists())

    def test_changed_staged_fixture_is_rejected_before_database_init(self):
        result = self.run_smoke(CP_MODE="tamper-stage")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("fixture bytes differ", result.stderr)
        self.assertEqual(self.calls(), [])


if __name__ == "__main__":
    unittest.main()
