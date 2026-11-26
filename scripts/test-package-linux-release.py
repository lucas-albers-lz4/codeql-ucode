#!/usr/bin/env python3
"""Static tests for the release archiver; no CodeQL or Rust execution."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import copy
import ast
from pathlib import Path
import subprocess
import sys
import tempfile
import tarfile
import io
import unittest


MODULE_PATH = Path(__file__).with_name("package-linux-release.py")
SPEC = importlib.util.spec_from_file_location("package_linux_release", MODULE_PATH)
assert SPEC and SPEC.loader
package = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(package)
VERIFY_SPEC = importlib.util.spec_from_file_location(
    "verify_linux_release_bundle", MODULE_PATH.with_name("verify-linux-release-bundle.py"))
assert VERIFY_SPEC and VERIFY_SPEC.loader
verify_bundle = importlib.util.module_from_spec(VERIFY_SPEC)
VERIFY_SPEC.loader.exec_module(verify_bundle)
GATE_PATH = MODULE_PATH.with_name("direct-rpc-release-gate.py")
GATE_SPEC = importlib.util.spec_from_file_location("direct_rpc_release_gate", GATE_PATH)
assert GATE_SPEC and GATE_SPEC.loader
release_gate = importlib.util.module_from_spec(GATE_SPEC)
GATE_SPEC.loader.exec_module(release_gate)


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "source"
        (self.root / "Cargo.lock").parent.mkdir(parents=True, exist_ok=True)
        (self.root / "Cargo.lock").write_text("version = 4\n")
        (self.root / ".codeqlmanifest.json").write_text(
            json.dumps({"provide": ["ql/*/qlpack.yml"]}) + "\n")
        for rel in package.PAYLOADS:
            (self.root / rel).mkdir(parents=True)
        (self.root / "extractor-pack/tools/linux64").mkdir(parents=True)
        extractor = self.root / "extractor-pack/tools/linux64/extractor"
        extractor.write_bytes(b"linux extractor bytes")
        extractor.chmod(0o755)
        (self.root / "extractor-pack/codeql-extractor.yml").write_text("name: ucode\n")
        (self.root / "ql/lib/qlpack.yml").write_text(
            "name: org/ucode-all\nversion: 1.2.3\n", encoding="utf-8")
        (self.root / "ql/src/qlpack.yml").write_text(
            "name: org/ucode-queries\nversion: 1.2.3\ndefaultSuiteFile: codeql-suites/code-scanning.qls\n",
            encoding="utf-8")
        for pack in ("ql/lib", "ql/src"):
            (self.root / pack / "codeql-pack.lock.yml").write_text("lockVersion: 1.0.0\n")
        (self.root / "ql/src/codeql-suites").mkdir()
        (self.root / "ql/src/codeql-suites/code-scanning.qls").write_text("- description: test\n")
        (self.root / "ql/src/Sample.ql").write_text("select 1\n")
        (self.root / "runner/run-installed-stage.py").write_text("#!/usr/bin/env python3\n")
        self.kwargs = dict(producer_commit="1" * 40, codeql_version="2.27.4",
                           rustc="rustc 1.100.0", cargo="cargo 1.100.0",
                           grammar_revision="2" * 40,
                           grammar_patch_sha256="4" * 64,
                           grammar_generated_files_sha256="5" * 64,
                           codeql_archive_sha256="3" * 64, source_clean=True)

    def build(self, name):
        path = Path(self.temp.name) / name
        result = package.create_bundle(self.root, path, **self.kwargs)
        return path, result

    def test_archive_is_deterministic_and_manifest_covers_payload(self):
        first, result = self.build("first.tar.gz")
        second, _ = self.build("second.tar.gz")
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertEqual(result["archive_sha256"], hashlib.sha256(first.read_bytes()).hexdigest())
        with tarfile.open(first, "r:gz") as archive:
            manifest = json.load(archive.extractfile("codeql-ucode-linux/bundle-manifest.json"))
            listed = {entry["path"]: entry for entry in manifest["files"]}
            self.assertEqual(set(listed), {".codeqlmanifest.json", "extractor-pack/codeql-extractor.yml",
                                           "extractor-pack/tools/linux64/extractor",
                                           "ql/lib/qlpack.yml", "ql/lib/codeql-pack.lock.yml",
                                           "ql/src/qlpack.yml", "ql/src/codeql-pack.lock.yml",
                                           "ql/src/codeql-suites/code-scanning.qls", "ql/src/Sample.ql",
                                           "runner/run-installed-stage.py"})
            for name, entry in listed.items():
                data = archive.extractfile("codeql-ucode-linux/" + name).read()
                self.assertEqual(len(data), entry["bytes"])
                self.assertEqual(hashlib.sha256(data).hexdigest(), entry["sha256"])
                self.assertEqual(archive.getmember("codeql-ucode-linux/" + name).mode & 0o777,
                                 entry["mode"])
            self.assertTrue(all(member.mode & 0o777 == 0o755
                                for member in archive.getmembers() if member.isdir()))
            self.assertEqual(archive.getmember("codeql-ucode-linux/bundle-manifest.json").mode & 0o777,
                             manifest["manifest_file_mode"])
            self.assertFalse(manifest["codeql_cli_included"])
            self.assertEqual(manifest["artifact_kind"], "ci-candidate")
            self.assertEqual(manifest["source_checkout_clean"], True)
            self.assertEqual(manifest["build"]["built_extractor_sha256"],
                             listed["extractor-pack/tools/linux64/extractor"]["sha256"])
            self.assertEqual(manifest["build"]["grammar_patch_sha256"], "4" * 64)
            self.assertEqual(manifest["build"]["grammar_generated_files_sha256"], "5" * 64)
            self.assertEqual(manifest["packs"]["queries"]["default_suite_sha256"],
                             hashlib.sha256(b"- description: test\n").hexdigest())
            self.assertEqual(manifest["packs"]["queries"]["query_files"]["Sample.ql"],
                             hashlib.sha256(b"select 1\n").hexdigest())
        extra_archive = Path(self.temp.name) / "extra-root-member.tar.gz"
        with tarfile.open(first, "r:gz") as original, tarfile.open(extra_archive, "w:gz") as altered:
            for member in original.getmembers():
                data = original.extractfile(member) if member.isreg() else None
                altered.addfile(copy.copy(member), data)
            rogue = tarfile.TarInfo("codeql-ucode-linux/rogue-executable")
            rogue.mode = 0o755
            rogue.size = 5
            altered.addfile(rogue, io.BytesIO(b"rogue"))
        extra_output = Path(self.temp.name) / "extra-output"
        extra_digest = hashlib.sha256(extra_archive.read_bytes()).hexdigest()
        extra_proc = subprocess.run([sys.executable, str(MODULE_PATH.with_name("verify-linux-release-bundle.py")),
                                     "--archive", str(extra_archive), "--expected-sha256", extra_digest,
                                     "--output-dir", str(extra_output)], capture_output=True, text=True)
        self.assertNotEqual(extra_proc.returncode, 0)
        self.assertIn("archive member set mismatch", extra_proc.stderr)
        self.assertFalse(extra_output.exists())
        extracted = Path(self.temp.name) / "extracted"
        proc = subprocess.run([sys.executable, str(MODULE_PATH.with_name("verify-linux-release-bundle.py")),
                               "--archive", str(first), "--expected-sha256", result["archive_sha256"],
                               "--output-dir", str(extracted)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = extracted / "codeql-ucode-linux"
        self.assertEqual(verify_bundle.verify(payload)["status"], "verified")
        (payload / "rogue-executable").write_bytes(b"unmanifested")
        (payload / "rogue-executable").chmod(0o755)
        with self.assertRaisesRegex(ValueError, "unexpected bundle-root members"):
            verify_bundle.verify(payload)
        (payload / "rogue-executable").unlink()
        (payload / "ql/src/Sample.ql").write_text("changed\n")
        with self.assertRaisesRegex(ValueError, "digest/size mismatch"):
            verify_bundle.verify(payload)

    def test_archive_traversal_fails_before_extraction(self):
        bad = Path(self.temp.name) / "bad.tar.gz"
        with tarfile.open(bad, "w:gz") as archive:
            data = b"escape"
            info = tarfile.TarInfo("codeql-ucode-linux/../../escape")
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
        output = Path(self.temp.name) / "unsafe-out"
        proc = subprocess.run([sys.executable, str(MODULE_PATH.with_name("verify-linux-release-bundle.py")),
                               "--archive", str(bad), "--expected-sha256",
                               hashlib.sha256(bad.read_bytes()).hexdigest(), "--output-dir", str(output)],
                              capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("unsafe archive member path", proc.stderr)
        self.assertFalse((Path(self.temp.name) / "escape").exists())

    def test_release_tag_is_bound_to_manifest_and_verifier_pin(self):
        tag = "v0.1.0-mvp.1"
        archive = Path(self.temp.name) / "versioned.tar.gz"
        result = package.create_bundle(self.root, archive, **self.kwargs, release_tag=tag)
        with tarfile.open(archive, "r:gz") as contents:
            manifest = json.load(contents.extractfile("codeql-ucode-linux/bundle-manifest.json"))
        self.assertEqual(manifest["artifact_kind"], "versioned-release")
        self.assertEqual(manifest["release_tag"], tag)
        output = Path(self.temp.name) / "release-extracted"
        proc = subprocess.run([sys.executable, str(MODULE_PATH.with_name("verify-linux-release-bundle.py")),
                               "--archive", str(archive), "--expected-sha256", result["archive_sha256"],
                               "--output-dir", str(output), "--expected-release-tag", tag],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        verified = verify_bundle.verify(output / "codeql-ucode-linux", tag, self.kwargs["producer_commit"])
        self.assertEqual(verified["artifact_kind"], "versioned-release")
        self.assertEqual(verified["release_tag"], tag)
        self.assertEqual(verified["manifest_sha256"], hashlib.sha256(
            (output / "codeql-ucode-linux/bundle-manifest.json").read_bytes()).hexdigest())
        with self.assertRaisesRegex(ValueError, "release tag differs"):
            verify_bundle.verify(output / "codeql-ucode-linux", "v0.1.0-mvp.2")
        with self.assertRaisesRegex(ValueError, "producer commit differs"):
            verify_bundle.verify(output / "codeql-ucode-linux", tag, "0" * 40)
        with self.assertRaisesRegex(ValueError, "manifest digest differs"):
            verify_bundle.verify(output / "codeql-ucode-linux", tag, self.kwargs["producer_commit"], "0" * 64)
        with self.assertRaisesRegex(ValueError, "release tag must be"):
            package.create_bundle(self.root, Path(self.temp.name) / "bad-tag.tar.gz",
                                  **self.kwargs, release_tag="latest")

    def test_rejects_empty_fake_manifest(self):
        root = Path(self.temp.name) / "fake"
        (root / "extractor-pack").mkdir(parents=True)
        (root / "ql/lib").mkdir(parents=True)
        (root / "ql/src").mkdir(parents=True)
        manifest = {"schema_version": 1, "platform": "linux-x64", "artifact_kind": "ci-candidate",
                    "source_checkout_clean": True, "producer_commit": "fake"}
        (root / "bundle-manifest.json").write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "full Git SHA"):
            verify_bundle.verify(root)

    def test_tailscale_file_lookup_uses_manifest_files_map(self):
        manifest = {"files": {"parent/usr/share/rpcd/ucode/tailscale.uc": {"sha256": "abc"}}}
        self.assertEqual(release_gate.tailscale_file_expectation(
            manifest, "parent", "usr/share/rpcd/ucode/tailscale.uc"), {"sha256": "abc"})
        with self.assertRaisesRegex(RuntimeError, "file expectation is missing"):
            release_gate.tailscale_file_expectation(manifest, "fixed", "missing.uc")

    def test_r2_main_round_trip_uses_bound_runner(self):
        tree = ast.parse(GATE_PATH.read_text(encoding="utf-8"))
        main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")
        calls = [node for node in ast.walk(main) if isinstance(node, ast.Call) and
                 isinstance(node.func, ast.Attribute) and node.func.attr in {"call", "codeql_call"}]
        unbound = [node for node in calls if isinstance(node.func.value, ast.Name) and node.func.value.id == "r"]
        self.assertEqual(unbound, [], "R2 main must use its local Runner instance")
        labels = {arg.value for node in calls for arg in node.args[:1]
                  if isinstance(arg, ast.Constant) and isinstance(arg.value, str)}
        self.assertTrue({"verify-and-extract-linux-release-candidate",
                         "install-candidate-lib-dependencies",
                         "install-candidate-query-dependencies",
                         "resolve-candidate-default-suite"}.issubset(labels))

    def test_refuses_non_linux_extractor(self):
        extractor = self.root / "extractor-pack/tools/linux64/extractor"
        extractor.chmod(0o644)
        with self.assertRaisesRegex(ValueError, "missing executable Linux extractor"):
            self.build("bad.tar.gz")


if __name__ == "__main__":
    unittest.main()
