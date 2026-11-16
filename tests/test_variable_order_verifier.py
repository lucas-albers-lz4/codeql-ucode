"""Direct CLI checks against portable, real declaration-order results."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import quote


REPO = Path(__file__).resolve().parents[1]
VERIFIER = REPO / "scripts/variable-order-verify.py"
DATA = REPO / "tests/fixtures/variable-order-results"
MARKER = b"@SOURCE_ROOT@"


class VariableOrderVerifierTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        # Exercise URI encoding separately from the routing path.
        self.source = self.root / "source with space"
        self.source.mkdir()
        shutil.copy2(REPO / "ql/test/variable-order/order.uc", self.source / "order.uc")
        self.link = self.root / "source-link"
        self.link.symlink_to(self.source, target_is_directory=True)
        self.out = self.root / "results"
        self.out.mkdir()
        provenance = json.loads((DATA / "provenance.json").read_text())
        self.assertEqual(
            hashlib.sha256((self.source / "order.uc").read_bytes()).hexdigest(),
            provenance["source_sha256"],
        )
        for name, item in provenance["results"].items():
            data = (DATA / name).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), item["portable_sha256"])
            self.assertEqual(data.count(MARKER), item["root_occurrences"])
            replacement = (
                quote(str(self.source), safe="/").encode()
                if name == "extracted.json"
                else str(self.source).encode()
            )
            # The File label is a plain path while the URI must be percent encoded.
            if name == "extracted.json":
                data = data.replace(MARKER, str(self.source).encode(), 1)
            data = data.replace(MARKER, replacement)
            (self.out / name).write_bytes(data)

    def run_cli(self, mode, source, optimized=False):
        args = [sys.executable]
        if optimized:
            args.append("-O")
        args.extend([str(VERIFIER), "inputs" if mode == "inputs" else str(self.out), str(source)])
        return subprocess.run(args, cwd=REPO, capture_output=True, text=True, timeout=30)

    def test_real_baseline_accepts_source_in_both_modes(self):
        for optimized in (False, True):
            for mode in ("inputs", "results"):
                with self.subTest(optimized=optimized, mode=mode):
                    result = self.run_cli(mode, self.source, optimized)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("PASS fixture identities and hashes: 1", result.stdout)
                    if mode == "results":
                        self.assertIn("PASS exact bindings identities: 17", result.stdout)
                        self.assertIn("PASS exact flow identities: 2", result.stdout)

    def test_relative_and_symlink_parent_paths_keep_canonical_semantics(self):
        parent_link = self.root / "parent-link"
        parent_link.symlink_to(self.root, target_is_directory=True)
        paths = (os.path.relpath(self.source, REPO), parent_link / self.source.name)
        for path in paths:
            for mode in ("inputs", "results"):
                with self.subTest(path=path, mode=mode):
                    result = self.run_cli(mode, path)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    if mode == "results":
                        self.assertIn("PASS exact bindings identities: 17", result.stdout)
                        self.assertIn("PASS exact flow identities: 2", result.stdout)

    def test_symlink_root_is_rejected_in_both_modes(self):
        for optimized in (False, True):
            for mode in ("inputs", "results"):
                with self.subTest(optimized=optimized, mode=mode):
                    result = self.run_cli(mode, self.link, optimized)
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertIn("invalid fixture source root", result.stderr)

    def test_missing_and_regular_file_roots_are_rejected(self):
        for root in (self.root / "missing", self.source / "order.uc"):
            for mode in ("inputs", "results"):
                with self.subTest(root=root, mode=mode):
                    result = self.run_cli(mode, root)
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertIn("invalid fixture source root", result.stderr)

    def test_fixture_symlink_is_rejected_in_both_modes(self):
        fixture = self.source / "order.uc"
        other = self.root / "order.uc"
        fixture.rename(other)
        fixture.symlink_to(other)
        for mode in ("inputs", "results"):
            with self.subTest(mode=mode):
                result = self.run_cli(mode, self.source)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn("fixture is not a regular file", result.stderr)

    def test_corrupt_real_binding_row_fails_results_oracle(self):
        path = self.out / "bindings.json"
        data = json.loads(path.read_text())
        self.assertEqual(data["#select"]["tuples"][0], [6, 13, 4, 7])
        data["#select"]["tuples"][0][0] = 7
        path.write_text(json.dumps(data))
        result = self.run_cli("results", self.source)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("bindings differs", result.stderr)


if __name__ == "__main__":
    unittest.main()
